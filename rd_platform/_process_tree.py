"""Owned process trees; Windows targets wait for Job assignment."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


class WindowsJob:
    def __init__(self):
        kernel = self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        for name, args, result in (
            ('CreateJobObjectW', [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            ('SetInformationJobObject', [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            ('QueryInformationJobObject', [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            ('AssignProcessToJobObject', [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            ('TerminateJobObject', [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            ('CloseHandle', [wintypes.HANDLE], wintypes.BOOL),
        ):
            function = getattr(kernel, name)
            function.argtypes, function.restype = args, result

        class BasicLimits(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', wintypes.DWORD), ('min_working', ctypes.c_size_t),
                        ('max_working', ctypes.c_size_t), ('active_limit', wintypes.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                        ('scheduling', wintypes.DWORD)]

        class Limits(ctypes.Structure):
            _fields_ = [('basic', BasicLimits), ('io', ctypes.c_uint64 * 6),
                        ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                        ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]

        self.handle = kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def active(self):
        class Accounting(ctypes.Structure):
            _fields_ = [('times', ctypes.c_int64 * 4), ('page_faults', wintypes.DWORD),
                        ('total', wintypes.DWORD), ('active', wintypes.DWORD), ('terminated', wintypes.DWORD)]
        info = Accounting()
        if not self.kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return bool(info.active)

    def stop(self):
        if not self.kernel.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            if not self.kernel.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = None


class ProcessTree:
    def __init__(self, argv, cwd):
        self.job = WindowsJob() if os.name == 'nt' else None
        self.process = None
        try:
            options = {'creationflags': subprocess.CREATE_NO_WINDOW} if self.job else {'start_new_session': True}
            # -S also disables global sitecustomize code before containment.
            command = [sys.executable, '-I', '-S', str(Path(__file__).resolve()), '--child'] if self.job else argv
            self.process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE if self.job else subprocess.DEVNULL,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, bufsize=0, **options)
            if self.job:
                self.job.assign(self.process)
                # No target code can run before this permission is sent.
                permission = memoryview((json.dumps(argv) + '\n').encode('utf-8'))
                while permission:
                    sent = self.process.stdin.write(permission)
                    if not sent:
                        raise OSError('Could not grant execution permission')
                    permission = permission[sent:]
                self.process.stdin.close()
        except BaseException:
            # Preserve the original launch error but attempt every cleanup. An
            # unassigned helper cannot spawn a target without the permission.
            cleanups = []
            if self.process and self.process.stdin and not self.process.stdin.closed:
                cleanups.append(self.process.stdin.close)
            if self.job:
                cleanups.append(self.job.close)
            if self.process:
                cleanups.extend((self.process.kill, lambda: self.process.wait(timeout=5), self.process.stdout.close))
            for cleanup in cleanups:
                try:
                    cleanup()
                except (OSError, subprocess.SubprocessError):
                    pass
            raise

    def active(self):
        self.process.poll()
        if self.job:
            return self.job.active()
        try:
            os.killpg(self.process.pid, 0)
            return True
        except ProcessLookupError:
            return False

    def stop(self):
        if self.job:
            self.job.stop()
        else:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.process.wait(timeout=5)

    def close(self):
        if self.job:
            self.job.close()


def _child():
    payload = sys.stdin.buffer.readline()
    if not payload:
        return 125
    try:
        process = subprocess.Popen(json.loads(payload), stdin=subprocess.DEVNULL, shell=False)
        return process.wait()
    except (OSError, ValueError):
        print('Executable could not be started', file=sys.stderr)
        return 127


if __name__ == '__main__':
    raise SystemExit(_child())
