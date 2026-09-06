"""CI JSON regression: deterministic limits independent of encoder recursion."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rd_platform.store import Store
from rd_platform.runtime import Runtime


def nested(depth):
    value=0
    for _ in range(depth): value=[value]
    return value


class JsonLimitTests(unittest.TestCase):
    def test_explicit_depth_before_permissive_encoder(self):
        for depth in (65,5000):
            with self.subTest(depth=depth), patch('rd_platform.store.json.dumps',return_value='{}') as encoder:
                with self.assertRaisesRegex(ValueError,'depth|deep'): Store.dumps(nested(depth))
                encoder.assert_not_called()

    def test_exact_depth_boundary_and_scalar(self):
        self.assertEqual('0',Store.dumps(0))
        self.assertEqual(nested(64),Store.loads(Store.dumps(nested(64))))
        for value in (nested(65),{'outer':nested(64)}):
            with self.assertRaises(ValueError): Store.dumps(value)

    def test_cycles_rejected_before_encoder_shared_dag_allowed(self):
        loop=[]; loop.append(loop)
        other={}; other['loop']=[other]
        for value in (loop,other):
            with patch('rd_platform.store.json.dumps',return_value='{}') as encoder:
                with self.assertRaisesRegex(ValueError,'circular|cycle'): Store.dumps(value)
                encoder.assert_not_called()
        shared={'items':[1,2]}
        self.assertEqual([shared,shared],Store.loads(Store.dumps([shared,shared])))

    def test_width_boundary(self):
        self.assertEqual(99999,len(Store.loads(Store.dumps([None]*99999))))
        with patch('rd_platform.store.json.dumps',return_value='[]') as encoder:
            with self.assertRaisesRegex(ValueError,'node|large|size'): Store.dumps([None]*100000)
            encoder.assert_not_called()

    def test_shared_dag_expanded_size_is_bounded(self):
        value=0
        for _ in range(6): value=[value]*10
        with patch('rd_platform.store.json.dumps',return_value='[]') as encoder:
            with self.assertRaisesRegex(ValueError,'node|large|size'): Store.dumps(value)
            encoder.assert_not_called()

    def test_decoding_has_same_depth_and_nonfinite_limits(self):
        self.assertEqual(nested(64),Store.loads('['*64+'0'+']'*64))
        with self.assertRaises(ValueError): Store.loads('['*65+'0'+']'*65)
        for text in ('NaN','Infinity','-Infinity','1e999','{"x":1e999}'):
            with self.subTest(text=text),self.assertRaises(ValueError): Store.loads(text)

    def test_nonfinite_keys_and_values_rejected(self):
        for number in (float('nan'),float('inf'),float('-inf')):
            for value in ({'x':[number]},{number:'value'}):
                with self.assertRaises(ValueError): Store.dumps(value)
        self.assertEqual({'x':[1.25]},Store.loads(Store.dumps({'x':(1.25,)})))

    def test_runtime_rejects_deep_or_wide_json_without_any_database_write(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=Runtime(Path(directory)/'state.db')
            project=runtime.execute('project.create',{'name':'JSON fixture','idea':'CI boundary'})
            def database():
                with runtime.store.transaction(write=False) as c: return list(c.iterdump())
            before=database()
            for index,inputs in enumerate((nested(65),nested(5000),[None]*100000)):
                data={'project_id':project['id'],'title':'must reject','why':'test','role':'developer','requirements':['REQ-JSON'],'dependencies':[],'inputs':{'value':inputs}}
                with self.assertRaises(ValueError): runtime.execute('task.create',data,request_id='invalid-'+str(index))
                self.assertEqual(before,database())


if __name__=='__main__': unittest.main()
