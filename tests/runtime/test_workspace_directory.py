"""BUG-RUNNER-path: pinned directories are not command sandboxes."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from rd_platform.runner import run_command


class WorkspaceDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.work=self.root/'work'; self.work.mkdir()
        self.outside=self.root/'outside'; self.outside.mkdir()

    def tearDown(self): self.temp.cleanup()

    def test_create_and_exclusive_json(self):
        from rd_platform._workspace_directory import confined_directory
        with confined_directory(self.root,'new/nested',create=True) as guard:
            guard.write_new_json('result.json',{'result':'OBSERVED'})
            with self.assertRaises(FileExistsError): guard.write_new_json('result.json',{})
            for name in ('../escape','x/y','x\\y','', 'a:stream'):
                with self.subTest(name=name), self.assertRaises(ValueError): guard.write_new_json(name,{})
        self.assertEqual({'result':'OBSERVED'},json.loads((self.root/'new/nested/result.json').read_text()))

    def test_invalid_relative_and_closed_guard(self):
        from rd_platform._workspace_directory import confined_directory
        for relative in ('../outside',str(self.outside),'work/../../outside'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                with confined_directory(self.root,relative): pass
        with confined_directory(self.root,'work') as guard: pass
        with self.assertRaises(ValueError): guard.write_new_json('closed.json',{})
        with self.assertRaises(ValueError): run_command([sys.executable,'-c','pass'],self.work,cwd_guard=guard)

    def test_unicode_directory_and_result_name(self):
        from rd_platform._workspace_directory import confined_directory
        with confined_directory(self.root,'测试-😀',create=True) as guard:
            guard.write_new_json('结果😀.json',{'正文':'验证'})
        self.assertEqual({'正文':'验证'},json.loads((self.root/'测试-😀/结果😀.json').read_text(encoding='utf-8')))

    def test_cwd_and_publication_not_redirected_by_directory_swap(self):
        from rd_platform._workspace_directory import confined_directory
        (self.work/'check.py').write_text("print('OWNED')")
        (self.outside/'check.py').write_text("print('OUTSIDE')")
        with confined_directory(self.root,'work') as guard:
            if os.name=='nt':
                with self.assertRaises(OSError): self.work.rename(self.root/'moved')
            else:
                self.work.rename(self.root/'moved'); self.work.symlink_to(self.outside,target_is_directory=True)
            result=run_command([sys.executable,'check.py'],self.work,cwd_guard=guard)
            self.assertEqual('PASS',result['status'],result); self.assertEqual('OWNED',result['stdout'].strip())
            guard.write_new_json('result.json',{'owned':True})
            self.assertFalse((self.outside/'result.json').exists())
        expected=self.work if os.name=='nt' else self.root/'moved'
        self.assertTrue((expected/'result.json').is_file())
        if os.name!='nt': self.work.unlink()

    def test_existing_symlink_or_junction_rejected(self):
        from rd_platform._workspace_directory import confined_directory
        link=self.root/'link'
        if os.name=='nt':
            import subprocess
            result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(self.outside)],capture_output=True)
            self.assertEqual(0,result.returncode,result.stderr)
        else: link.symlink_to(self.outside,target_is_directory=True)
        try:
            with self.assertRaises((ValueError,OSError)):
                with confined_directory(self.root,'link'): pass
        finally:
            if os.name=='nt': os.rmdir(link)
            else: link.unlink()

    def test_root_ancestor_is_pinned_and_handles_release(self):
        from rd_platform._workspace_directory import confined_directory
        parent=self.root/'parent'; parent.mkdir(); child=parent/'child'; child.mkdir()
        moved=self.root/'parent-moved'
        with confined_directory(parent,'child') as guard:
            if os.name=='nt':
                with self.assertRaises(OSError): parent.rename(moved)
            else:
                parent.rename(moved); parent.symlink_to(self.outside,target_is_directory=True)
            guard.write_new_json('pinned.json',{})
            self.assertFalse((self.outside/'child/pinned.json').exists())
        if os.name=='nt': parent.rename(moved) # Handles no longer block rename.
        else: parent.unlink()
        self.assertTrue((moved/'child/pinned.json').exists())

    def test_publish_failure_never_exposes_partial_result(self):
        from rd_platform._workspace_directory import confined_directory
        from unittest.mock import patch
        with confined_directory(self.root,'work') as guard:
            with self.assertRaises(ValueError): guard.write_new_json('result.json',{'bad':float('nan')})
            self.assertEqual([],list(self.work.iterdir()))
            if os.name!='nt':
                with patch('rd_platform._workspace_directory.os.fsync',side_effect=OSError('synthetic fsync failure')):
                    with self.assertRaises(OSError): guard.write_new_json('result.json',{})
                self.assertEqual([],list(self.work.iterdir()))

    @unittest.skipIf(os.name=='nt','POSIX temp-file replacement attack')
    def test_temp_name_replacement_cannot_publish_attacker_content(self):
        from rd_platform._workspace_directory import confined_directory
        from unittest.mock import patch
        original=os.link
        def replace_temp(source,target,**kwargs):
            temp=next(self.work.glob('.publish-*'))
            temp.unlink(); temp.write_text('attacker')
            return original(source,target,**kwargs)
        with confined_directory(self.root,'work') as guard:
            with patch('rd_platform._workspace_directory.os.link',side_effect=replace_temp):
                try: guard.write_new_json('result.json',{'owned':True})
                except FileNotFoundError: pass # Original inode unlinked: fail closed.
        if (self.work/'result.json').exists():
            self.assertEqual({'owned':True},json.loads((self.work/'result.json').read_text()))


if __name__=='__main__': unittest.main()
