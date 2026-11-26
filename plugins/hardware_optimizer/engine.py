"""Hardware-aware runtime planning for VISUAL; standard-library-first."""
import importlib.util, os, platform, shutil
from pathlib import Path

def _memory():
    out = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            if k in ("MemTotal", "MemAvailable"):
                out[k] = int(v.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return {"total_bytes": out.get("MemTotal"), "available_bytes": out.get("MemAvailable")}

def _android():
    if not (os.environ.get("ANDROID_ROOT") or shutil.which("getprop")): return {}
    result = {"android": True}
    if shutil.which("getprop"):
        import subprocess
        for key, prop in (("soc","ro.soc.model"),("manufacturer","ro.product.manufacturer"),
                          ("device","ro.product.device"),("sdk","ro.build.version.sdk")):
            try:
                value = subprocess.run(["getprop",prop],capture_output=True,text=True,timeout=2).stdout.strip()
                if value: result[key] = value[:120]
            except (OSError, subprocess.SubprocessError): pass
    return result

def _read_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None

def _cpu_telemetry():
    cpus = []
    for base in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")):
        if not base.name[3:].isdigit():
            continue
        freq = _read_text(base / "cpufreq/scaling_cur_freq")
        max_freq = _read_text(base / "cpufreq/cpuinfo_max_freq")
        cpus.append({"cpu": base.name, "current_khz": int(freq) if freq and freq.isdigit() else None,
                     "max_khz": int(max_freq) if max_freq and max_freq.isdigit() else None})
    flags = []
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith(("features", "flags")):
                flags = sorted(set(line.split(":", 1)[1].strip().split()))
                break
    except OSError:
        pass
    return {"cores": cpus, "instruction_features": flags}

def _thermal_telemetry():
    zones = []
    for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        raw = _read_text(zone / "temp")
        kind = _read_text(zone / "type")
        try:
            value = int(raw) if raw is not None else None
            # Linux thermal sysfs convention is millidegrees Celsius.
            celsius = value / 1000.0 if value is not None and abs(value) > 1000 else value
        except ValueError:
            celsius = None
        if kind or celsius is not None:
            zones.append({"zone": zone.name, "type": kind, "temperature_c": celsius})
    return zones

def _accelerator_telemetry():
    devices = []
    for node in sorted(Path("/sys/class/devfreq").glob("*")):
        name = _read_text(node / "name") or node.name
        current = _read_text(node / "cur_freq")
        maximum = _read_text(node / "max_freq")
        if current or maximum:
            devices.append({"name": name, "current_hz": int(current) if current and current.isdigit() else None,
                            "max_hz": int(maximum) if maximum and maximum.isdigit() else None})
    for path in ("/sys/class/kgsl/kgsl-3d0/gpu_model", "/sys/class/misc/mali0/device/gpuinfo"):
        value = _read_text(path)
        if value:
            devices.append({"name": "gpu_model", "model": value[:160]})
    return devices

def hardware_profile():
    ort = None; providers = []
    if importlib.util.find_spec("onnxruntime"):
        try:
            import onnxruntime as ort
            providers = list(ort.get_available_providers())
        except Exception: pass
    tools = {n: shutil.which(n) for n in ("llama-cli","llama-server","ollama")}
    tools = {k:v for k,v in tools.items() if v}
    nodes = [p for p in ("/dev/kgsl-3d0","/dev/mali0","/dev/dri/renderD128","/dev/nvidia0","/dev/accel/accel0") if os.path.exists(p)]
    return {"platform":platform.platform(),"machine":platform.machine(),"processor":platform.processor() or "unknown",
            "logical_cpu_count":os.cpu_count() or 1,"memory":_memory(),"cpu_telemetry":_cpu_telemetry(),
            "thermal_zones":_thermal_telemetry(),"accelerator_telemetry":_accelerator_telemetry(),"android":_android(),
            "onnxruntime_installed":ort is not None,"onnxruntime_version":getattr(ort,"__version__",None),
            "onnx_execution_providers":providers,"gpu_device_nodes":nodes,"local_inference_tools":tools,
            "note":"Device-node presence is not proof that a driver/runtime can execute a model."}

def optimization_plan(workload="llm", ram_budget_mb=0):
    p=hardware_profile(); providers=p["onnx_execution_providers"]; mem=p["memory"]
    avail=mem.get("available_bytes") or mem.get("total_bytes") or 0
    detected=avail//(1024*1024)
    budget=max(128,min(int(ram_budget_mb or max(256,int(detected*.55))),detected or int(ram_budget_mb or 256)))
    order=[x for x in ("TensorrtExecutionProvider","CUDAExecutionProvider","QNNExecutionProvider",
          "CoreMLExecutionProvider","NNAPIExecutionProvider","XNNPACKExecutionProvider",
          "OpenVINOExecutionProvider","DmlExecutionProvider","CPUExecutionProvider") if x in providers]
    steps=["Measure baseline latency, peak RAM, CPU utilization, energy and temperature.",
           "Keep model weights plus KV cache/intermediate tensors inside the RAM budget.",
           "Test INT8/INT4 only against a representative quality-validation set.",
           "Fuse compatible operators and reuse buffers to reduce memory traffic.",
           "Tune thread count empirically; excess threads can increase heat and contention.",
           "Keep a CPU fallback and compare numerical outputs after backend changes."]
    w=str(workload).lower()
    if w in ("llm","language","chat"):
        steps += ["Benchmark GGUF llama.cpp with the device's ARM NEON/SIMD support.",
                  "Compare Q4/Q5 memory, tokens per second and Hindi output quality.",
                  "Bound context length and KV-cache; avoid loading multiple large models concurrently."]
    elif w in ("vision","image","audio","speech","robotics"):
        steps.append("Use practical fixed input shapes and benchmark the complete pipeline end-to-end.")
    limits=[]
    if not providers: limits.append("ONNX Runtime is absent or exposes no execution providers.")
    if not p["local_inference_tools"] and not p["onnxruntime_installed"]:
        limits.append("No local inference runtime detected; this is discovery/planning only.")
    if p["android"].get("android") and not any(x in providers for x in ("QNNExecutionProvider","NNAPIExecutionProvider","XNNPACKExecutionProvider")):
        limits.append("Android accelerator delegation is not exposed by the installed ONNX Runtime.")
    return {"workload":w,"ram_budget_mb":budget,"device":p,"recommended_backend_order":order,"steps":steps,"limitations":limits}

def create_onnx_session(model_path, home=None, intra_threads=0):
    root=Path(home or Path.home()/".visual").resolve()
    allowed=[root/"models",Path("/storage/emulated/0/Download"),Path("/storage/emulated/0/Documents")]
    path=Path(model_path).expanduser().resolve()
    if not any(path==b.resolve() or b.resolve() in path.parents for b in allowed):
        raise ValueError("Model must be inside ~/.visual/models, Android Download, or Documents.")
    if not path.is_file() or path.suffix.lower()!=".onnx": raise ValueError("A local .onnx file is required.")
    try: import onnxruntime as ort
    except ImportError as exc: raise RuntimeError("onnxruntime is not installed; nothing was installed automatically.") from exc
    opts=ort.SessionOptions(); opts.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.enable_mem_pattern=True; opts.enable_cpu_mem_arena=True
    opts.intra_op_num_threads=max(0,min(int(intra_threads),os.cpu_count() or 1)); opts.inter_op_num_threads=1
    avail=set(ort.get_available_providers())
    order=[x for x in ("TensorrtExecutionProvider","CUDAExecutionProvider","QNNExecutionProvider",
          "CoreMLExecutionProvider","NNAPIExecutionProvider","XNNPACKExecutionProvider",
          "OpenVINOExecutionProvider","DmlExecutionProvider","CPUExecutionProvider") if x in avail]
    if not order: raise RuntimeError("No usable ONNX Runtime execution provider.")
    session=ort.InferenceSession(str(path),sess_options=opts,providers=order)
    return session,{"model":str(path),"model_bytes":path.stat().st_size,"available_providers":list(ort.get_available_providers()),
       "active_providers":session.get_providers(),"input_names":[x.name for x in session.get_inputs()],
       "output_names":[x.name for x in session.get_outputs()],"thread_count":opts.intra_op_num_threads or "runtime default",
       "graph_optimization":"ORT_ENABLE_ALL","inference_executed":False}
