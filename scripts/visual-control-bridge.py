#!/usr/bin/env python3
"""Phone-side, allowlisted GitHub issue relay for VISUAL. No shell/code execution."""
import json, os, re, subprocess, sys, time, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HOME=Path.home()/".visual"
STATE=HOME/"control_bridge_state.json"
REPO="bhupendarsingh785/visual-data"
OWNER="bhupendarsingh785"
LABEL="visual-command"
ALLOWED={"knowledge_collect_global_research","knowledge_status"}
SECRET_RE=re.compile(r"(AIza[0-9A-Za-z_-]{30,}|AQ\.[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|gsk_[A-Za-z0-9]{30,}|nvapi-[A-Za-z0-9_-]{30,}|csk-[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,})")
def gh(*args,timeout=25):
 p=subprocess.run(["gh",*args],cwd=str(ROOT),text=True,capture_output=True,timeout=timeout)
 if p.returncode: raise RuntimeError((p.stderr or p.stdout or "GitHub CLI request failed").strip()[:500])
 return p.stdout.strip()
def load_state():
 try:
  d=json.loads(STATE.read_text(encoding="utf-8"))
  if not isinstance(d,dict) or not isinstance(d.get("issues"),dict): raise RuntimeError("Bridge state schema invalid; refusing to replay commands.")
  return d
 except FileNotFoundError: return {"issues":{}}
 except (OSError,ValueError) as e: raise RuntimeError("Bridge state corrupt; refusing to replay commands: "+str(e))
def save_state(s):
 HOME.mkdir(parents=True,exist_ok=True); tmp=STATE.with_suffix(".tmp")
 tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8"); os.chmod(tmp,0o600); os.replace(tmp,STATE); os.chmod(STATE,0o600)
def verify_connection():
 if not shutil.which("gh"): raise RuntimeError("GitHub CLI gh nahi mila.")
 login=gh("api","user","--jq",".login")
 if login.lower()!=OWNER.lower(): raise RuntimeError(f"Galat GitHub account: {login}; {OWNER} chahiye.")
 if gh("api",f"repos/{REPO}","--jq",".private").lower()!="true": raise RuntimeError("Control queue repo private nahi hai; bridge refuse.")
 return login
def parse_payload(body):
 if not body or len(body)>16000: raise ValueError("Issue body khaali ya limit se bada.")
 d=json.loads(body)
 if not isinstance(d,dict) or set(d)-{"action","args","nonce","expires_at"}: raise ValueError("Unknown envelope fields.")
 action,args,nonce,expires=d.get("action"),d.get("args",{}),d.get("nonce"),d.get("expires_at")
 if action not in ALLOWED or not isinstance(args,dict): raise ValueError("Action allowlist mein nahi ya args invalid.")
 if not isinstance(nonce,str) or not re.fullmatch(r"[A-Za-z0-9_-]{12,80}",nonce): raise ValueError("Nonce invalid.")
 now=int(time.time())
 if not isinstance(expires,int) or isinstance(expires,bool) or expires<now or expires>now+86400: raise ValueError("Command expired/expiry 24h se zyada.")
 if action=="knowledge_status" and args: raise ValueError("knowledge_status args nahi leta.")
 if action=="knowledge_collect_global_research":
  if set(args)-{"topics","per_request","max_requests"}: raise ValueError("Unsupported research args.")
  topics=args.get("topics",""); pr=args.get("per_request",25); mr=args.get("max_requests",300)
  if not isinstance(topics,str) or len(topics)>600: raise ValueError("topics max 600 characters.")
  if not isinstance(pr,int) or isinstance(pr,bool) or not 1<=pr<=25: raise ValueError("per_request 1-25.")
  if not isinstance(mr,int) or isinstance(mr,bool) or not 1<=mr<=300: raise ValueError("max_requests 1-300.")
  args={"topics":topics,"per_request":pr,"max_requests":mr}
 return action,args,nonce
def post_comment(n,text):
 safe=SECRET_RE.sub("[REDACTED_SECRET]",str(text))
 gh("api",f"repos/{REPO}/issues/{n}/comments","--method","POST","-f","body="+safe[:6000])
def close_issue(n): gh("api",f"repos/{REPO}/issues/{n}","--method","PATCH","-f","state=closed")
def run_tool(action,args):
 sys.path.insert(0,str(ROOT)); import visual
 item=visual.TOOLS.get(action)
 if not item: raise RuntimeError("VISUAL tool load nahi hua: "+action)
 return str(item["fn"](**args))
def handle_issue(issue,state):
 n=int(issue["number"]); k=str(n)
 if k in state["issues"]:
  if state["issues"][k].get("status")=="processing":
   post_comment(n,"VISUAL bridge: previous run interrupted; outcome unknown. Duplicate execution se bachne ke liye retry nahi kiya.")
   state["issues"][k]={"status":"unknown","updated_at":int(time.time())}; save_state(state)
  return
 if issue.get("user",{}).get("login","").lower()!=OWNER.lower():
  post_comment(n,"VISUAL bridge reject: issue owner account se nahi aaya.")
  state["issues"][k]={"status":"rejected","updated_at":int(time.time())}; save_state(state); close_issue(n); return
 if LABEL not in {x.get("name") for x in issue.get("labels",[])} or "pull_request" in issue: return
 try:
  action,args,nonce=parse_payload(issue.get("body") or "")
  if nonce in {v.get("nonce") for v in state["issues"].values()}: raise ValueError("Nonce already used.")
 except Exception as e:
  post_comment(n,"VISUAL bridge reject: "+str(e)); state["issues"][k]={"status":"rejected","updated_at":int(time.time())}; save_state(state); close_issue(n); return
 state["issues"][k]={"status":"processing","nonce":nonce,"action":action,"updated_at":int(time.time())}; save_state(state)
 try:
  result=run_tool(action,args); post_comment(n,"VISUAL RESULT\nAction: "+action+"\nStatus: completed\n\n"+result); state["issues"][k]["status"]="completed"
 except Exception as e:
  post_comment(n,"VISUAL RESULT\nAction: "+action+"\nStatus: error\n\n"+type(e).__name__+": "+str(e)[:1000]); state["issues"][k]["status"]="error"
 state["issues"][k]["updated_at"]=int(time.time()); save_state(state); close_issue(n)
def poll_once(state):
 issues=json.loads(gh("api",f"repos/{REPO}/issues","-f","state=open","-f","per_page=100","-f","labels="+LABEL))
 for issue in issues:
  if "pull_request" not in issue: handle_issue(issue,state)
def main():
 if len(sys.argv)>1 and sys.argv[1]=="--check":
  print("GitHub account:",verify_connection()); print("Private queue:",REPO); print("Allowed:",", ".join(sorted(ALLOWED))); return 0
 print("VISUAL ChatGPT control bridge running. CTRL+C to stop.")
 verify_connection(); state=load_state()
 while True:
  try: poll_once(state)
  except KeyboardInterrupt: raise
  except Exception as e: print("Bridge error:",type(e).__name__,str(e)[:400],flush=True)
  time.sleep(30)
if __name__=="__main__":
 try: raise SystemExit(main() or 0)
 except KeyboardInterrupt: print("\nBridge stopped."); raise SystemExit(130)
