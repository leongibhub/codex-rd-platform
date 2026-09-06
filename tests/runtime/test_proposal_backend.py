import json, os, threading, time, unittest
from unittest.mock import patch
from rd_platform.proposal_backend import run_responses

class _Response:
    def __init__(self, raw): self.raw=raw
    def read(self, n): return self.raw
    def __enter__(self): return self
    def __exit__(self,*_): pass
    def close(self): pass

class ProposalBackendTests(unittest.TestCase):
    def spec(self): return {"model":"test","api_key_env":"TEST_RESPONSE_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":32}
    def test_standard_raw_response_extracts_assistant_output_text(self):
        raw=json.dumps({"status":"completed","output":[{"type":"reasoning"},{"type":"message","role":"assistant","content":[{"type":"output_text","text":"{\"status\":\"DONE\",\"summary\":\"x\",\"proposals\":[]}"}]}]}).encode()
        with patch.dict(os.environ,{"TEST_RESPONSE_KEY":"x"}):
            result=run_responses(self.spec(),prompt="x",timeout_seconds=1,max_output_bytes=10000,transport=lambda *_:_Response(raw))
        self.assertEqual("PASS",result["status"])
    def test_missing_key_is_not_available(self):
        with patch.dict(os.environ,{},clear=True): self.assertEqual("NOT_AVAILABLE",run_responses(self.spec(),prompt="x",timeout_seconds=1,max_output_bytes=10)["status"])
    def test_tool_call_is_rejected(self):
        raw=json.dumps({"status":"completed","output":[{"type":"function_call"}]}).encode()
        with patch.dict(os.environ,{"TEST_RESPONSE_KEY":"x"}): self.assertEqual("FAIL",run_responses(self.spec(),prompt="x",timeout_seconds=1,max_output_bytes=10000,transport=lambda *_:_Response(raw))["status"])
    def test_slow_read_cancel_returns_cancelled_failure(self):
        started=threading.Event()
        class Slow(_Response):
            def read(self,n):
                started.set()
                while not getattr(self,"closed",False): time.sleep(.01)
                raise OSError()
            def close(self): self.closed=True
        cancel=threading.Event(); box={}
        with patch.dict(os.environ,{"TEST_RESPONSE_KEY":"x"}):
            thread=threading.Thread(target=lambda:box.setdefault("r",run_responses(self.spec(),prompt="x",timeout_seconds=10,max_output_bytes=10,transport=lambda *_:Slow(b""),cancel_event=cancel)))
            thread.start(); self.assertTrue(started.wait(1)); cancel.set(); thread.join(2)
        self.assertFalse(thread.is_alive()); self.assertTrue(box["r"]["cancelled"])
    def test_reader_exception_is_failure(self):
        class Broken(_Response):
            def read(self,n): raise OSError()
        with patch.dict(os.environ,{"TEST_RESPONSE_KEY":"x"}):
            self.assertEqual("FAIL",run_responses(self.spec(),prompt="x",timeout_seconds=1,max_output_bytes=10,transport=lambda *_:Broken(b""))["status"])

    def test_connect_stage_cancel_and_total_deadline_are_bounded(self):
        for mode in ('cancel', 'deadline'):
            with self.subTest(mode=mode):
                entered, release, cancel = threading.Event(), threading.Event(), threading.Event()
                box = {}
                def connect(*_):
                    entered.set(); release.wait(3); return _Response(b'{}')
                with patch.dict(os.environ, {'TEST_RESPONSE_KEY': 'x'}):
                    thread = threading.Thread(target=lambda: box.setdefault('r', run_responses(self.spec(),
                        prompt='x', timeout_seconds=.15 if mode == 'deadline' else 5,
                        max_output_bytes=100, transport=connect, cancel_event=cancel)))
                    try:
                        thread.start(); self.assertTrue(entered.wait(1))
                        if mode == 'cancel': cancel.set()
                        thread.join(1)
                        self.assertFalse(thread.is_alive())
                        self.assertEqual('FAIL', box['r']['status'])
                        self.assertTrue(box['r']['request_may_still_be_running'])
                    finally: release.set(); thread.join(3)
