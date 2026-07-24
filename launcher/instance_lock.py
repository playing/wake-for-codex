"""Cross-platform non-blocking singleton lock for the wake listener."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from types import TracebackType
from typing import IO

from .model_config import default_data_dir


class SingleInstance:
    def __init__(self, lock_path: Path | None = None) -> None:
        self.lock_path = lock_path or default_data_dir() / "wake-launcher.lock"
        self._windows_handle: int | None = None
        self._file_handle: IO[str] | None = None
        self.acquired = False

    def __enter__(self) -> "SingleInstance":
        if sys.platform == "win32":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            create_mutex = kernel32.CreateMutexW
            create_mutex.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            create_mutex.restype = ctypes.c_void_p
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = [ctypes.c_void_p]
            close_handle.restype = ctypes.c_bool
            ctypes.set_last_error(0)
            handle = create_mutex(None, False, "Local\\WakeForCodex.SingleInstance")
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            if ctypes.get_last_error() == 183:
                close_handle(handle)
                return self
            self._windows_handle = int(handle)
            self.acquired = True
            return self

        if sys.platform == "darwin":
            import fcntl

            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.lock_path.open("a+", encoding="utf-8")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                return self
            handle.seek(0)
            handle.truncate()
            handle.write(str(os.getpid()))
            handle.flush()
            self._file_handle = handle
            self.acquired = True
            return self

        raise RuntimeError(f"Unsupported platform: {sys.platform}")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        if self._windows_handle is not None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = [ctypes.c_void_p]
            close_handle.restype = ctypes.c_bool
            close_handle(ctypes.c_void_p(self._windows_handle))
            self._windows_handle = None
        if self._file_handle is not None:
            import fcntl

            fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_UN)
            self._file_handle.close()
            self._file_handle = None
        self.acquired = False
