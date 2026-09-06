"""Bounded no-tools Responses API transport."""
from __future__ import annotations
import json, os, time, threading, urllib.error, urllib.parse, urllib.request
from .store import Store

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None

_TYPES=["BG","MR","PRD","REQ","NFR","DES","ADR","TASK","CODE_CHANGE","CR","RISK","DOC"]
_TRANSPORT_SLOTS=threading.BoundedSemaphore(8)
def response_schema():
    p={"type":"object","additionalProperties":False,"required":["action","id","type","title","relative_path","content","expected_sha256"],"properties":{"action":{"type":"string","enum":["create","update"]},"id":{"type":"string"},"type":{"type":"string","enum":_TYPES},"title":{"type":"string"},"relative_path":{"type":"string"},"content":{"type":"string","maxLength":1048576},"expected_sha256":{"anyOf":[{"type":"null"},{"type":"string","pattern":"^[0-9a-f]{64}$"}]}}}
    return {"type":"object","additionalProperties":False,"required":["status","summary","proposals"],"properties":{"status":{"type":"string","enum":["DONE","FAILED","WAITING_USER","BLOCKED"]},"summary":{"type":"string","minLength":1,"maxLength":4000},"proposals":{"type":"array","items":p}}}

def _output_text(data):
    text=[]
    if not isinstance(data.get("output"), list): raise ValueError()
    for item in data["output"]:
        if not isinstance(item,dict): raise ValueError()
        if item.get("type") not in {"reasoning", "message"}: raise ValueError()
        if item.get("type")=="message" and item.get("role")=="assistant":
            for part in item.get("content",[]):
                if not isinstance(part,dict): raise ValueError()
                if part.get("type")=="refusal": raise ValueError()
                if part.get("type")=="output_text" and isinstance(part.get("text"),str): text.append(part["text"])
    if len(text)!=1: raise ValueError()
    return text[0]

def run_responses(spec, *, prompt, timeout_seconds, max_output_bytes, transport=None, cancel_event=None):
    started=time.monotonic(); key=os.environ.get(spec["api_key_env"])
    if not key: return {"status":"NOT_AVAILABLE","stdout":"","launch_error":"Responses API key is NOT_AVAILABLE","duration_seconds":0}
    parsed=urllib.parse.urlparse(spec["endpoint"])
    if parsed.scheme!="https" or parsed.username or parsed.password or parsed.query or parsed.fragment: raise ValueError("Responses endpoint must be trusted HTTPS URL")
    body={"model":spec["model"],"input":prompt,"tools":[],"tool_choice":"none","store":False,"max_output_tokens":spec["max_output_tokens"],"text":{"format":{"type":"json_schema","name":"worker_proposal","strict":True,"schema":response_schema()}}}
    req=urllib.request.Request(spec["endpoint"],data=json.dumps(body).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    if not _TRANSPORT_SLOTS.acquire(blocking=False): return {"status":"FAIL","stdout":"","launch_error":"Responses transport capacity exhausted","duration_seconds":0}
    box = {}
    aborted = threading.Event()
    def request():
        response = None
        try:
            socket_timeout = min(timeout_seconds, 30)
            response = transport(req, socket_timeout) if transport else urllib.request.build_opener(_NoRedirect()).open(req, timeout=socket_timeout)
            box["response"] = response
            if not aborted.is_set(): box["raw"] = response.read(max_output_bytes + 1)
        except Exception:
            box["error"] = True
        finally:
            try:
                if response is not None: response.close()
            except Exception: pass
            _TRANSPORT_SLOTS.release()
    thread = threading.Thread(target=request, daemon=True, name="rd-proposal-transport")
    thread.start()
    while thread.is_alive():
        thread.join(.025)
        cancelled = bool(cancel_event and cancel_event.is_set())
        timed_out = time.monotonic() - started >= timeout_seconds
        if cancelled or timed_out:
            aborted.set()
            # Closing a socket can itself block. It cannot block the dispatcher.
            # Slots remain held until the request thread actually exits.
            response = box.get("response")
            if response is not None:
                def close():
                    try: response.close()
                    except Exception: pass
                threading.Thread(target=close, daemon=True, name="rd-proposal-close").start()
            return {"status": "FAIL", "stdout": "", "cancelled": cancelled, "timed_out": timed_out,
                    "request_may_still_be_running": True,
                    "launch_error": "Responses cancelled or deadline exceeded; remote outcome unknown",
                    "duration_seconds": round(time.monotonic()-started, 6)}
    if cancel_event and cancel_event.is_set():
        return {"status": "FAIL", "stdout": "", "cancelled": True, "request_may_still_be_running": True}
    if "error" in box or "raw" not in box:
        return {"status":"FAIL","stdout":"","launch_error":"Responses transport failed","duration_seconds":round(time.monotonic()-started,6)}
    raw = box["raw"]
    if len(raw)>max_output_bytes: return {"status":"FAIL","stdout":"","launch_error":"Responses output budget exceeded","duration_seconds":round(time.monotonic()-started,6)}
    try:
        data=Store.loads(raw.decode())
        if not isinstance(data,dict): raise ValueError()
        text=_output_text(data)
    except (ValueError,UnicodeDecodeError,RecursionError): return {"status":"FAIL","stdout":"","launch_error":"Responses response rejected","duration_seconds":round(time.monotonic()-started,6)}
    if data.get("status")!="completed" or data.get("incomplete_details"): return {"status":"FAIL","stdout":"","launch_error":"Responses incomplete","duration_seconds":round(time.monotonic()-started,6)}
    return {"status":"PASS","stdout":text,"exit_code":0,"timed_out":False,"output_truncated":False,"cancelled":False,"duration_seconds":round(time.monotonic()-started,6)}
