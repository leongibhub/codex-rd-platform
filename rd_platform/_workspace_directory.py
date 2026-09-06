"""Pinned workspace directory traversal and exclusive result publication.

This protects platform path resolution, not arbitrary trusted command behavior.
Keep the context open through process completion and result publication.
"""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path, PureWindowsPath
from uuid import uuid4


def _relative_parts(relative):
    value=os.fspath(relative)
    if not isinstance(value,str) or '\0' in value or Path(value).is_absolute() or PureWindowsPath(value).is_absolute() or PureWindowsPath(value).drive:
        raise ValueError('relative directory must be a confined relative path')
    parts=value.replace('\\','/').split('/')
    if '..' in parts: raise ValueError('parent traversal is not permitted')
    result=[p for p in parts if p not in ('','.')]
    for part in result:
        if ':' in part or part.endswith((' ','.')): raise ValueError('unsafe directory component')
    return result


class _WindowsHandles:
    def __init__(self):
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        signatures=(
            ('CreateFileW',[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE],wintypes.HANDLE),
            ('GetFileInformationByHandleEx',[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD],wintypes.BOOL),
            ('WriteFile',[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p],wintypes.BOOL),
            ('FlushFileBuffers',[wintypes.HANDLE],wintypes.BOOL),
            ('SetFileInformationByHandle',[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD],wintypes.BOOL),
            ('CloseHandle',[wintypes.HANDLE],wintypes.BOOL),
        )
        for name,args,result in signatures:
            function=getattr(self.kernel,name); function.argtypes=args; function.restype=result

    def check(self,result):
        if not result: raise ctypes.WinError(ctypes.get_last_error())
        return result

    def open(self,path,access,share,creation,flags):
        handle=self.kernel.CreateFileW(str(path),access,share,None,creation,flags,None)
        if handle==ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def directory(self,path):
        handle=self.open(path,0x81,3,3,0x02200000) # LIST_DIRECTORY|attributes, read/write share only, OPEN_REPARSE+BACKUP
        try:
            info=(wintypes.DWORD*2)()
            self.check(self.kernel.GetFileInformationByHandleEx(handle,9,info,ctypes.sizeof(info)))
            if info[0]&0x400 or not info[0]&0x10: raise ValueError('directory links/reparse points are not permitted')
            return handle
        except BaseException:
            self.kernel.CloseHandle(handle); raise

    def write_new(self,path,payload):
        temp=path.parent/('.publish-'+uuid4().hex+'.tmp')
        handle=self.open(temp,0x40010000,1,1,0x00200000) # GENERIC_WRITE|DELETE, CREATE_NEW, no delete sharing
        try:
            buffer=ctypes.create_string_buffer(payload); written=wintypes.DWORD()
            self.check(self.kernel.WriteFile(handle,buffer,len(payload),ctypes.byref(written),None))
            if written.value!=len(payload): raise OSError('incomplete JSON write')
            self.check(self.kernel.FlushFileBuffers(handle))
            name=str(path)
            encoded_name=name.encode('utf-16-le')
            class RenameInfo(ctypes.Structure):
                _fields_=[('replace',wintypes.BOOLEAN),('root',wintypes.HANDLE),('length',wintypes.DWORD),('name',wintypes.WCHAR*(len(encoded_name)//2+1))]
            info=RenameInfo(); info.replace=0; info.root=None; info.length=len(encoded_name); info.name=name
            self.check(self.kernel.SetFileInformationByHandle(handle,3,ctypes.byref(info),ctypes.sizeof(info)))
            self.check(self.kernel.FlushFileBuffers(handle))
        finally:
            self.kernel.CloseHandle(handle)
            try: temp.unlink()
            except FileNotFoundError: pass


class DirectoryGuard:
    def __init__(self,path,handles,windows=None):
        self.path=path; self._handles=handles; self._windows=windows; self._closed=False

    def _live(self):
        if self._closed: raise ValueError('directory guard is closed')

    def process_directory(self):
        """Return cwd and inherited fd tuple without re-resolving a path."""
        self._live()
        if self._windows: return str(self.path),()
        fd=self._handles[-1]
        path=f'/proc/self/fd/{fd}'
        if not Path('/proc/self/fd').is_dir(): raise OSError('pinned process cwd requires procfs on this host')
        return path,(fd,)

    def write_new_json(self,name,value):
        self._live()
        if not isinstance(name,str) or not name or name in ('.','..') or any(s in name for s in ('/','\\',':','\0')) or name.endswith((' ','.')):
            raise ValueError('result name must be a safe basename')
        payload=(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
        if self._windows:
            self._windows.write_new(self.path/name,payload)
        else:
            directory=self._handles[-1]; temp='.publish-'+uuid4().hex+'.tmp'
            fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
            try:
                with os.fdopen(fd,'wb') as stream:
                    stream.write(payload); stream.flush(); os.fsync(stream.fileno())
                    # Link the open inode, not a temporary name a peer process
                    # could replace. procfs dereference is intentional here.
                    os.link(f'/proc/self/fd/{stream.fileno()}',name,dst_dir_fd=directory,follow_symlinks=True)
                os.unlink(temp,dir_fd=directory); os.fsync(directory)
            finally:
                try: os.unlink(temp,dir_fd=directory)
                except FileNotFoundError: pass
        return self.path/name

    def close(self):
        if not self._closed:
            self._closed=True
            for handle in reversed(self._handles):
                if self._windows: self._windows.kernel.CloseHandle(handle)
                else: os.close(handle)


@contextmanager
def confined_directory(root,relative='.',*,create=False):
    """Pin every directory component, rejecting links before traversal.

    POSIX writes/cwd use directory descriptors even if a pathname is replaced.
    Windows excludes delete sharing to prevent moving all opened ancestors.
    """
    parts=_relative_parts(relative); raw=Path(root)
    if '..' in raw.parts: raise ValueError('root must not contain parent traversal')
    root=Path(os.path.abspath(raw)); path=Path(root.anchor)
    handles=[]; windows=_WindowsHandles() if os.name=='nt' else None
    guard=DirectoryGuard(root.joinpath(*parts),handles,windows)
    try:
        if windows: handles.append(windows.directory(path))
        else: handles.append(os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
        root_parts=list(root.parts[1:])
        for index,part in enumerate(root_parts+parts):
            path=path/part
            make=create and index>=len(root_parts)
            if windows:
                if make:
                    try: path.mkdir()
                    except FileExistsError: pass
                handles.append(windows.directory(path))
            else:
                if make:
                    try: os.mkdir(part,mode=0o700,dir_fd=handles[-1])
                    except FileExistsError: pass
                handles.append(os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=handles[-1]))
        yield guard
    finally: guard.close()
