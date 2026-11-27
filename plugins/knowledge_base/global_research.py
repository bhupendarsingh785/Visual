"""Rotating, resumable multi-domain public metadata collection for VISUAL."""
import json
import os
import time
from pathlib import Path
from api_harvest import harvest_public_metadata

DOMAIN_QUERIES = {
  "medicine": ["clinical medicine systematic review", "public health epidemiology", "medical imaging open dataset"],
  "biology": ["molecular biology genomics", "proteomics biodiversity"],
  "veterinary": ["veterinary medicine animal disease livestock health", "animal welfare veterinary epidemiology open research"],
  "animals_wildlife": ["wildlife species animal behaviour ecology open dataset", "mammals birds reptiles amphibians biodiversity occurrence"],
  "history": ["ancient history archaeology historical archive", "manuscripts epigraphy cultural heritage"],
  "education": ["teacher education pedagogy open educational resources", "mathematics education curriculum"],
  "coding": ["software engineering programming languages", "open source software code dataset"],
  "ai": ["machine learning deep learning foundation models", "natural language processing computer vision"],
  "agents": ["AI agents tool use benchmark", "multi agent systems planning reasoning"],
  "tools": ["developer tools compilers databases operating systems", "robotics automation engineering"],
  "physics": ["physics astronomy materials science", "particle physics open data"],
  "chemistry": ["chemistry chemical materials research", "drug discovery molecular datasets"],
  "mathematics": ["pure mathematics applied mathematics statistics", "theorem proving mathematical datasets"],
  "agriculture": ["agriculture crop science soil food security", "livestock plant pathology"],
  "climate": ["climate change meteorology weather", "oceanography hydrology earth observation"],
  "space": ["astronomy astrophysics planetary science NASA", "satellite earth observation"],
  "engineering": ["civil mechanical electrical engineering", "electronics semiconductor manufacturing"],
  "energy": ["renewable energy power grids batteries", "nuclear energy energy systems"],
  "economics": ["economics finance development statistics", "labor markets trade public policy"],
  "law": ["law legal scholarship human rights legislation", "comparative law public legal information"],
  "languages": ["linguistics language documentation multilingual corpora", "Hindi language NLP speech"],
  "culture": ["music art anthropology folklore cultural heritage", "literature archives oral history"],
  "geography": ["geography geospatial maps population", "urban planning transportation infrastructure"],
  "environment": ["ecology conservation pollution environmental science", "biodiversity species occurrence"],
  "oceans": ["marine biology fisheries ocean data", "coral reefs ocean circulation"],
  "disasters": ["earthquake flood wildfire disaster risk", "emergency management resilience"],
  "security": ["cybersecurity cryptography vulnerability research", "software security threat intelligence"],
  "business": ["management entrepreneurship industry supply chains", "operations research logistics"],
  "sports": ["sports science biomechanics exercise physiology", "sports analytics open data"],
  "human_behavior": ["human behavior everyday activities social interaction behavioral science open dataset", "human action recognition walking running sitting standing hand movements gestures"],
  "speech_voice": ["multilingual speech corpus spontaneous conversation speech recognition open dataset", "prosody laughter crying emotion speech voice activity dataset"],
  "facial_expression": ["facial expression action units gaze head pose emotion recognition dataset", "face gesture non-identifying landmark movement research dataset"],
  "memory_cognition": ["human memory cognition attention learning decision making psychology dataset", "episodic memory autobiographical memory cognitive task open research data"],
  "social_science": ["sociology social networks demographics migration public survey dataset", "anthropology ethnography oral history community behavior open data"],
  "social_platforms": ["public social media trends platform governance content moderation research dataset", "public online communities discussion network misinformation research dataset"],
  "robotics_motion": ["robotics human robot interaction motion capture manipulation dataset", "human pose estimation gait locomotion biomechanics open dataset"],
  "manufacturing": ["manufacturing industrial engineering predictive maintenance machine sensor dataset", "factory process quality control CNC robotics semiconductor production research data"],
  "mechanical": [ "mechanical engineering fluid dynamics thermodynamics vibration materials dataset", "machine components CAD finite element simulation engineering open data", "mechanism design kinematics dynamics vibration modal analysis finite element", "fluid mechanics turbulence CFD heat transfer thermodynamics open datasets", "machine design bearings gears shafts fatigue lubrication tribology", "mechatronics actuators sensors servo motors control systems"],
  "electrical_electronics": ["electrical engineering power electronics circuits semiconductor devices dataset", "microelectronics chip fabrication testing reliability open research data"],
  "transport": ["transportation traffic pedestrian mobility public transit open data", "vehicle dynamics autonomous driving road safety dataset"],
  "construction": ["construction engineering building materials structural health monitoring dataset", "architecture infrastructure bridge civil engineering open data"],
  "geology": ["geology tectonics minerals volcanology geophysics open research", "earth history rocks soil groundwater geoscience datasets"],
  "paleontology": ["paleontology fossils prehistoric life evolution open research", "dinosaur fossil vertebrate invertebrate paleobiology collections"],
  "archaeology_technology": ["archaeological technology ancient engineering tools metallurgy", "history of inventions ancient machines materials construction"],
  "neuroscience": ["neuroscience brain behavior neural systems open datasets", "cognitive neuroscience motor control perception attention"],
  "psychology": ["psychology emotion behavior personality development open research", "clinical psychology social psychology experimental datasets"],
  "biomechanics": ["human biomechanics gait posture locomotion motion capture open data", "muscle skeletal movement ergonomics sports biomechanics"],
  "sign_language": ["sign language gestures handshape facial grammar open corpus", "gesture recognition sign language linguistics datasets"],
  "performing_arts": ["dance theatre acting facial expression body language movement", "music performance voice prosody rhythm gesture research"],
  "food_nutrition": ["food science nutrition public health food composition open data", "agri food processing fermentation food safety research"],
  "water_resources": ["hydrology water quality groundwater river basin open datasets", "water treatment desalination sanitation engineering research"],
  "quantum_technology": ["quantum computing quantum information devices open research", "quantum sensors materials communication technology"],
  "patents_inventions": ["patent inventions technology trends public patent metadata", "historical patents engineering inventions innovation research"],
  "standards": ["engineering technical standards interoperability public standards", "medical safety manufacturing quality measurement standards"],
  "open_hardware": [ "open source hardware electronics robotics designs", "microcontroller embedded systems circuit schematics open projects", "open source silicon PDK EDA flow RTL FPGA RISC V hardware repositories", "microcontroller SBC embedded board schematics PCB BOM manufacturing files", "robotics open hardware actuators sensors motor drivers mechanical CAD", "hardware reproducibility license verification bill of materials supply chain"],
  "public_policy": ["public policy governance institutions development open data", "government services public administration regulatory research"],
  "discovery_frontier": ["recent scientific discoveries emerging technologies research frontiers", "interdisciplinary unexplored research questions open science"],
  "deep_learning": [ "deep learning neural network architectures optimization training benchmarks", "self supervised learning representation learning foundation models research", "transformer attention architectures encoder decoder mixture of experts state space models neural scaling laws", "self supervised contrastive masked prediction representation learning multimodal pretraining", "supervised fine tuning instruction tuning preference optimization RLHF DPO reward models", "LoRA QLoRA adapters quantization pruning distillation sparsity efficient inference", "continual learning catastrophic forgetting transfer learning domain adaptation few shot learning", "retrieval augmented generation vector databases hybrid search reranking knowledge graphs evaluation", "neural network optimization AdamW SGD schedulers warmup regularization gradient clipping loss scaling", "distributed training data parallel tensor parallel pipeline parallel FSDP ZeRO checkpointing", "benchmark contamination data leakage reproducibility uncertainty calibration robustness interpretability", "edge AI on device inference CPU only mobile NPU memory bandwidth energy latency benchmarks", "tokenization multilingual Hindi Indic languages speech text multimodal dataset quality licensing", "training data deduplication near duplicate detection provenance filtering synthetic data evaluation"],
  "computer_vision": [ "computer vision image video understanding object detection segmentation open datasets", "human pose estimation action recognition facial action units gaze tracking", "image classification object detection instance segmentation panoptic segmentation open benchmark", "video understanding temporal action localization tracking multi object tracking datasets", "3D vision stereo depth estimation SLAM NeRF Gaussian splatting point clouds", "medical imaging segmentation radiology pathology ultrasound MRI CT validation datasets", "optical flow pose estimation hand tracking facial landmarks gaze estimation non-identifying", "vision language grounding image captioning visual question answering multimodal alignment", "low light infrared thermal hyperspectral remote sensing image restoration", "dataset bias domain shift robustness calibration explainability adversarial evaluation"],
  "multimodal_ai": [ "multimodal AI vision language audio video models benchmarks", "cross modal representation learning grounding perception research", "audio visual speech recognition lip reading audiovisual synchronization datasets", "video audio text joint embedding cross modal retrieval grounding temporal alignment", "multimodal fusion early late cross attention token alignment missing modality robustness", "embodied multimodal models visual navigation scene understanding action planning", "multimodal benchmark contamination evaluation safety uncertainty calibration"],
  "medical_imaging": ["medical imaging radiology MRI CT ultrasound pathology open research datasets", "medical image segmentation detection clinical validation explainable AI"],
  "clinical_trials": ["clinical trials interventions outcomes trial registries open research", "randomized controlled trials systematic reviews treatment evidence"],
  "genomics_proteomics": ["genomics transcriptomics proteomics single cell biology open datasets", "protein structure function molecular biology bioinformatics research"],
  "human_motion": ["human activity recognition gait pose estimation body movement datasets", "hand gestures sign language facial expression body posture motion capture"],
  "audio_speech": ["speech emotion recognition speaker diarization acoustic phonetics open corpora", "environmental sound classification animal vocalization audio datasets"],
  "semiconductor_research": [ "semiconductor device physics chip fabrication lithography packaging reliability", "integrated circuits transistor process nodes materials yield testing research", "CMOS transistor FinFET gate all around nanosheet forksheet device physics", "semiconductor process integration lithography EUV etch deposition ion implantation diffusion", "wafer fabrication cleanroom contamination control metrology yield defect inspection", "chip architecture CPU GPU NPU DSP accelerator systolic arrays memory hierarchy", "chiplet advanced packaging 2.5D 3D integration TSV hybrid bonding interposer", "SRAM DRAM HBM NAND flash MRAM ReRAM memory reliability endurance retention", "power performance area PPA timing closure floorplanning placement routing clock tree", "RTL design Verilog SystemVerilog UVM formal verification synthesis static timing analysis", "analog mixed signal ADC DAC PLL RF power management circuit design verification", "semiconductor reliability electromigration BTI TDDB thermal cycling ESD failure analysis", "open source silicon PDK standard cells RISC V tapeout chip design education", "semiconductor materials silicon carbide gallium nitride gallium arsenide silicon photonics", "chip security hardware trojans side channel fault injection secure boot root of trust", "advanced packaging thermal management power integrity signal integrity co design", "process node scaling yield economics supply chain equipment workforce research"],
  "materials_science": [ "materials science alloys polymers ceramics nanomaterials characterization datasets", "battery materials catalysts superconductors crystal structures research", "materials informatics crystal graph neural networks property prediction datasets", "materials characterization XRD SEM TEM AFM Raman spectroscopy microscopy", "alloys ceramics polymers composites fracture fatigue creep corrosion datasets", "battery electrode electrolyte degradation solid state ion transport materials", "semiconductor materials band structure defects interfaces thin films deposition", "materials synthesis process structure property performance data provenance"],
  "robotics_agents": [ "robot learning manipulation navigation embodied AI agent benchmarks", "autonomous agents planning tool use reinforcement learning robotics", "robot kinematics forward inverse dynamics Jacobian trajectory planning motion planning", "robot manipulation grasp planning tactile sensing dexterous hands force control", "mobile robot localization mapping SLAM visual inertial odometry navigation planning", "legged robotics locomotion gait generation balance whole body control contact dynamics", "robot learning imitation learning reinforcement learning sim to real domain randomization", "human robot interaction intent prediction proxemics shared autonomy safety", "robot operating system ROS2 middleware DDS simulation Gazebo Isaac Lab interoperability", "robot perception RGB D lidar radar event cameras sensor fusion calibration", "industrial robotics safety PLC machine vision collaborative robots inspection automation", "robot benchmarks reproducibility real world evaluation failure recovery"],
  "ancient_civilizations": ["ancient civilizations archaeology epigraphy artifacts trade technology", "historical engineering architecture metallurgy inventions manuscripts"],

  "physics": [
    "physics fundamentals mechanics kinematics dynamics Newton laws work energy momentum gravitation waves optics thermodynamics electromagnetism modern physics open education",
    "physics research frontier theoretical experimental computational physics mathematical methods measurement uncertainty laboratory experiments",
    "classical mechanics analytical mechanics Lagrangian Hamiltonian rigid body rotation oscillations nonlinear dynamics",
    "fluid mechanics hydrostatics hydrodynamics viscosity turbulence boundary layers Navier Stokes CFD experiments",
    "thermodynamics statistical mechanics kinetic theory entropy ensembles phase transitions heat engines",
    "electromagnetism electrostatics magnetostatics Maxwell equations electromagnetic waves antennas transmission lines",
    "optics geometrical optics wave optics interference diffraction polarization lasers fiber optics photonics",
    "acoustics sound waves resonance musical acoustics ultrasonics noise vibration experimental data",
    "special relativity general relativity spacetime tensors gravitational waves black holes cosmology",
    "quantum mechanics wave functions operators Schrödinger equation angular momentum spin perturbation theory",
    "atomic molecular nuclear physics spectroscopy atomic structure molecular spectra nuclear reactions radioactivity",
    "particle physics standard model quantum field theory collider experiments neutrinos antimatter particle detector data",
    "condensed matter solid state physics crystal lattices band theory semiconductors superconductivity magnetism",
    "plasma physics magnetohydrodynamics fusion tokamak stellarator plasma diagnostics instabilities",
    "astrophysics stellar evolution exoplanets galaxies high energy astrophysics observational astronomy",
    "geophysics seismology Earth's interior geomagnetism gravity field planetary physics",
    "biophysics biomechanics medical physics radiation physics imaging instrumentation",
    "computational physics numerical methods Monte Carlo finite difference finite element molecular dynamics",
    "experimental physics laboratory methods calibration uncertainty propagation sensors detectors metrology",
    "applied physics materials physics nanophysics surface physics thin films photonics quantum devices",
    "physics education demonstrations conceptual misconceptions worked examples problem solving curriculum"
  ],
  "physics_classical_mechanics": [
    "introductory mechanics units dimensions vectors scalars coordinate systems position displacement speed velocity acceleration graphs",
    "Newton laws free body diagrams friction tension normal force inclined planes circular motion drag",
    "work energy power conservation laws potential kinetic energy collisions impulse momentum center of mass",
    "rotational motion torque angular momentum moment of inertia rolling motion gyroscope precession",
    "gravitation Kepler laws orbital mechanics satellites escape velocity tides gravitational potential",
    "simple harmonic motion pendulums coupled oscillators resonance damping driven oscillations chaos",
    "Lagrangian mechanics Hamiltonian mechanics generalized coordinates constraints variational principles"
  ],
  "physics_fluids": [
    "fluid statics pressure buoyancy Pascal principle Archimedes principle manometers",
    "fluid dynamics continuity Bernoulli Euler equations viscosity Poiseuille flow Reynolds number",
    "Navier Stokes equations turbulence boundary layers wakes vortices drag lift aerodynamics",
    "computational fluid dynamics CFD finite volume methods mesh convergence validation benchmark datasets"
  ],
  "physics_thermodynamics": [
    "temperature heat calorimetry thermal expansion specific heat latent heat conduction convection radiation",
    "laws of thermodynamics entropy enthalpy Gibbs free energy Helmholtz free energy thermodynamic potentials",
    "kinetic theory ideal gases real gases equations of state Maxwell Boltzmann distribution",
    "statistical mechanics microcanonical canonical grand canonical ensembles partition functions phase transitions",
    "heat engines refrigerators Carnot cycle Stirling Otto Diesel Rankine cycles efficiency"
  ],
  "physics_electromagnetism": [
    "electric charge Coulomb law electric fields potential Gauss law capacitors dielectrics",
    "electric current circuits Ohm Kirchhoff RC RL RLC circuits AC impedance resonance",
    "magnetic fields Biot Savart Ampere law Faraday induction Lenz law inductance transformers",
    "Maxwell equations electromagnetic waves waveguides antennas transmission lines radiation"
  ],
  "physics_waves_optics": [
    "wave motion superposition standing waves beats Doppler effect dispersion group velocity",
    "sound acoustics resonance ultrasound noise measurement psychoacoustics",
    "reflection refraction Snell law mirrors lenses optical instruments ray tracing",
    "interference diffraction polarization coherence Fourier optics lasers holography fiber optics"
  ],
  "physics_modern": [
    "special relativity Lorentz transformations time dilation length contraction relativistic energy momentum",
    "general relativity equivalence principle curved spacetime Einstein field equations gravitational lensing",
    "quantum mechanics wave particle duality uncertainty principle Schrödinger equation operators",
    "quantum measurement entanglement tunneling spin angular momentum perturbation approximation"
  ],
  "physics_atomic_nuclear_particle": [
    "atomic physics hydrogen atom fine structure hyperfine structure Zeeman Stark effects spectroscopy",
    "molecular physics rotational vibrational electronic spectra molecular collisions",
    "nuclear physics binding energy radioactive decay fission fusion nuclear models",
    "particle physics Standard Model quarks leptons gauge bosons neutrinos antimatter collider experiments"
  ],
  "physics_condensed_matter": [
    "solid state physics crystal structures reciprocal lattice phonons band theory electronic transport",
    "semiconductor physics pn junction diodes transistors MOSFET carrier transport optoelectronics",
    "superconductivity BCS theory Josephson effect topological materials quantum Hall effect",
    "magnetism spin systems phase transitions nanomaterials surfaces defects"
  ],
  "physics_plasma_fusion": [
    "plasma physics Debye shielding plasma frequency kinetic theory magnetohydrodynamics",
    "plasma waves instabilities confinement diagnostics tokamak stellarator inertial confinement fusion",
    "fusion reactions Lawson criterion energy balance plasma heating magnetic confinement"
  ],
  "physics_astronomy_cosmology": [
    "astrophysics stellar structure nucleosynthesis supernova neutron stars black holes",
    "galaxies active galactic nuclei dark matter dark energy large scale structure",
    "cosmology Big Bang cosmic microwave background inflation expansion observational constraints",
    "exoplanet detection planetary atmospheres orbital dynamics gravitational wave astronomy"
  ],
  "physics_geophysics_biophysics": [
    "geophysics seismology seismic waves Earth's interior geomagnetism gravity and geodesy",
    "biophysics molecular motors membranes protein folding electrophysiology biomechanics",
    "medical physics radiation dosimetry radiotherapy diagnostic imaging MRI CT ultrasound"
  ],
  "physics_computational_experimental": [
    "computational physics numerical integration ODE PDE solvers Monte Carlo molecular dynamics",
    "finite difference finite element spectral methods computational electromagnetics computational quantum physics",
    "experimental design laboratory instrumentation sensors detectors calibration uncertainty propagation",
    "metrology significant figures error analysis reproducibility data acquisition scientific visualization"
  ],
  "india": ["India public health agriculture census education", "India history languages geography"],
  "animal_taxonomy": ["global animal taxonomy species subspecies taxonomy phylogeny open datasets", "invertebrates vertebrates mammals birds reptiles amphibians fish taxonomy"],
  "animal_morphology": ["animal morphology anatomy body size shape coloration pattern pigmentation", "animal development sexual dimorphism seasonal plumage coat morphology variation"],
  "animal_behavior": ["animal behaviour ethology social behaviour feeding mating migration territoriality", "animal cognition problem solving tool use play cooperation learning"],
  "animal_communication": ["animal communication signals calls courtship alarm contact vocal repertoire", "interspecies communication acoustic signaling chemical visual tactile signals"],
  "animal_bioacoustics": ["animal bioacoustics birdsong mammal calls amphibian insects sound datasets", "whale dolphin bat echolocation wolf howling frog calls annotated audio"],
  "animal_vision_color": ["animal coloration camouflage mimicry iridescence structural color visual ecology", "animal vision ultraviolet polarization color perception comparative datasets"],
  "animal_life_history": ["animal life history development reproduction lifespan growth survival datasets", "seasonal behavior hibernation torpor migration breeding phenology animals"],
  "plants_traits_ecology": ["plant morphology leaf flower root seed traits phenology open datasets", "plant behavior tropism signaling pollination dispersal ecological interactions"],
  "ecosystems_foodwebs": ["ecosystem ecology food webs trophic interactions predator prey datasets", "population dynamics habitat connectivity biodiversity conservation monitoring"],
  "neuroscience_cognition": ["neuroscience cognition perception attention memory decision making open datasets", "brain development plasticity learning executive function cognitive neuroscience"],
  "brain_imaging": ["human brain MRI fMRI EEG MEG connectomics open neuroimaging datasets", "neural circuits brain atlases cell types electrophysiology neuroscience data"],
  "learning_intelligence": ["learning science intelligence cognitive abilities reasoning problem solving research", "skill acquisition expertise metacognition education cognitive development datasets"],
  "psychometrics_behavior": ["psychometrics measurement scales reliability validity cognitive assessment datasets", "human behavior social cognition personality decision making experimental research"],
  "medicine_clinical": ["clinical medicine diagnosis treatment outcomes guidelines evidence datasets", "medical specialties cardiology neurology oncology infectious disease clinical research"],
  "medicine_public_health": ["epidemiology disease surveillance public health health systems open datasets", "nutrition maternal child health environmental health occupational health research"],
  "medical_methods": ["medical research methodology clinical study design randomized trials cohort studies", "systematic reviews meta analysis biostatistics reproducibility clinical evidence"],
  "engineering_methods": [ "engineering design methodology systems engineering reliability safety analysis", "engineering simulation finite element computational fluid dynamics optimization methods", "systems engineering requirements traceability architecture trade studies verification validation", "finite element analysis CFD multiphysics simulation uncertainty quantification", "reliability engineering FMEA fault tree root cause failure mode analysis", "design for manufacturability assembly tolerance stackup lifecycle assessment", "control theory system identification estimation Kalman filtering robust adaptive control", "measurement science metrology calibration uncertainty propagation standards"],
  "manufacturing_processes": [ "manufacturing process planning quality control metrology lean production datasets", "industrial process monitoring failure analysis yield optimization maintenance research", "manufacturing digital twins process planning CNC machining tool wear datasets", "additive manufacturing metal polymer powder bed fusion defects process monitoring", "industrial robotics PLC SCADA MES OPC UA interoperability manufacturing", "statistical process control SPC six sigma metrology inspection quality engineering", "predictive maintenance vibration acoustic emission motor current thermal sensor data", "semiconductor fabrication process control wafer metrology yield analytics"],
  "electronics_circuits": [ "electronics analog digital circuits PCB embedded systems open hardware research", "semiconductor testing chip design verification signal integrity power electronics", "analog circuit design op amp filters oscillators noise stability SPICE simulation", "digital logic FSM RTL verification FPGA timing synthesis hardware description language", "power electronics converters inverters motor drives wide bandgap semiconductor control", "embedded systems microcontrollers RTOS peripherals buses sensors low power firmware", "PCB stackup impedance control EMC EMI signal integrity thermal design manufacturing", "RF microwave antennas radar SDR mixers low noise amplifiers frequency synthesizers", "battery management systems charging protection state of health state of charge"],
  "robotics_perception_control": [ "robotics perception localization mapping motion planning control datasets", "robot manipulation locomotion grasping tactile sensing human robot interaction", "robot perception object pose estimation scene graphs 3D reconstruction", "robot control model predictive control impedance admittance force torque control", "visual servoing grasp detection tactile visual sensor fusion", "autonomous navigation obstacle avoidance path planning localization mapping", "robot safety collision detection emergency stop functional safety standards"],
  "computer_science_methods": ["algorithms data structures distributed systems databases operating systems research", "programming languages formal methods software testing verification benchmarks"],
  "materials_properties": [ "materials properties mechanical thermal electrical optical chemical datasets", "materials characterization microscopy spectroscopy crystallography open data", "mechanical properties stress strain hardness toughness fatigue creep fracture", "thermal conductivity expansion heat capacity phase transitions materials databases", "electrical dielectric magnetic optical properties spectroscopy open datasets", "corrosion wear tribology surface engineering coatings degradation"],
  "energy_systems": ["energy systems power generation transmission storage grid reliability datasets", "solar wind hydrogen batteries nuclear energy lifecycle research"],
  "earth_observation": ["remote sensing satellite imagery land cover climate atmosphere ocean datasets", "geospatial GIS hydrology hazards geology earth observation research"],
  "history_knowledge": ["world history primary sources archives manuscripts archaeology material culture", "history of science technology medicine engineering inventions methods"],
  "philosophy_ethics": ["philosophy epistemology logic ethics reasoning knowledge theory research", "research ethics scientific integrity responsible innovation technology governance"],
  "economics_work": ["labor economics productivity occupations workplace skills industry datasets", "development economics inequality institutions markets behavioral economics research"],
  "agriculture_animal_husbandry": ["livestock animal husbandry breeding welfare behavior nutrition datasets", "crop science soil plant disease irrigation farm management open research"],
  "language_culture": ["world languages linguistics phonetics dialects endangered language corpora", "cultural anthropology folklore oral history social practices public datasets"],
  "audio_environment": ["environmental soundscape acoustic ecology urban rural sound datasets", "sound event detection machinery weather transport household acoustic research"]
}

# Each provider returns bounded public search metadata, not unrestricted file mirrors.
PROVIDERS = ("openalex", "crossref", "zenodo", "gbif", "nasa_cmr",
             "huggingface", "pubmed", "stackoverflow", "arxiv", "europe_pmc", "wikidata",
             "openverse_images", "openverse_audio", "wikimedia_commons", "internet_archive")

def collect_global_research(topics=None, per_request=25, max_requests=300, home=None, offset=None):
    """Rotate through all domain/provider tasks so scheduled runs don't repeat only the first page."""
    selected = sorted({x.strip().lower() for x in (topics or []) if x.strip()})
    unknown = sorted(set(selected) - set(DOMAIN_QUERIES))
    if unknown:
        raise ValueError("Unknown topics: " + ", ".join(unknown) + ". Available: " + ", ".join(DOMAIN_QUERIES))
    chosen = selected or list(DOMAIN_QUERIES)
    per_request = max(1, min(int(per_request), 25))
    max_requests = max(1, min(int(max_requests), 300))
    tasks = [(topic, query, provider) for topic in chosen
             for query in DOMAIN_QUERIES[topic] for provider in PROVIDERS]
    if not tasks:
        raise ValueError("No provider-query tasks are configured.")
    state_path = Path(home or Path.home() / ".visual") / "global_research_state.json"
    state_key = "all" if not selected else ",".join(sorted(set(selected)))
    saved_offset = 0
    saved_state = {}
    if offset is None and state_path.is_file():
        try:
            saved_state = json.loads(state_path.read_text(encoding="utf-8"))
            saved_offset = int(saved_state.get("next_offsets", {}).get(
                state_key, saved_state.get("next_offset", 0) if state_key == "all" else 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError, AttributeError):
            saved_offset = 0
            saved_state = {}
    start = int(saved_offset if offset is None else offset) % len(tasks)
    rotated_tasks = tasks[start:] + tasks[:start]
    results, errors = [], []
    attempted = 0
    for topic, query, provider in rotated_tasks[:max_requests]:
        attempted += 1
        try:
            item = harvest_public_metadata(provider, query, per_request, home, topic=topic)
            results.append({"topic": topic, **item})
        except Exception as exc:
            errors.append({"topic": topic, "provider": provider,
                           "query": query, "error": str(exc)[:240]})
        time.sleep(0.4)
    next_offset = (start + attempted) % len(tasks)
    state_error = ""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = state_path.with_suffix(".tmp")
        offsets = saved_state.get("next_offsets", {}) if isinstance(saved_state, dict) else {}
        if not isinstance(offsets, dict):
            offsets = {}
        offsets[state_key] = next_offset
        new_state = {"next_offsets": offsets, "last_task_key": state_key,
                     "next_offset": offsets.get("all", 0), "total_tasks": len(tasks),
                     "updated_at": time.time()}
        temp_path.write_text(json.dumps(new_state, indent=2), encoding="utf-8")
        os.replace(temp_path, state_path)
    except OSError as exc:
        state_error = str(exc)[:240]
    summary = _summary(results, errors, attempted, chosen)
    summary["task_offset"] = start
    summary["next_task_offset"] = next_offset
    summary["total_provider_query_tasks"] = len(tasks)
    summary["rotation_state_error"] = state_error
    summary["stopped_reason"] = "per-run request cap reached" if len(tasks) > max_requests else "all selected tasks processed"
    return summary

def _summary(results, errors, attempted, topics):
    provider_status_counts = {}
    for item in results:
        provider = item.get("provider", "unknown")
        status = item.get("status", "unknown")
        counts = provider_status_counts.setdefault(provider, {})
        counts[status] = counts.get(status, 0) + 1
    for item in errors:
        provider = item.get("provider", "unknown")
        counts = provider_status_counts.setdefault(provider, {})
        counts["error"] = counts.get("error", 0) + 1
    return {
        "topics": topics,
        "requests_attempted": attempted,
        "successful_requests": sum(1 for x in results if x.get("status") in ("indexed", "already_indexed")),
        "empty_results": sum(1 for x in results if x.get("status") == "empty"),
        "failed_requests": len(errors) + sum(1 for x in results if x.get("status") not in ("indexed", "already_indexed", "empty")),
        "indexed_characters": sum(int(x.get("indexed_characters", 0)) for x in results),
        "fetched_characters": sum(int(x.get("fetched_characters", x.get("indexed_characters", 0))) for x in results),
        "provider_status_counts": provider_status_counts,
        "results": results,
        "errors": errors,
        "scope": "Public API search metadata only; full-text and bulk dataset files require separate item-level rights and download workflows.",
    }
