"""Asynchronous temporary file and directory managers with safe cleanup."""

import asyncio
import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path


@asynccontextmanager
async def async_temp_directory(prefix: str = "vanilla_temp_") -> AsyncIterator[Path]:
    """Async context manager that creates a temporary directory and guarantees its removal."""
    temp_dir = await asyncio.to_thread(tempfile.mkdtemp, prefix=prefix)
    dir_path = Path(temp_dir)
    try:
        yield dir_path
    finally:
        await asyncio.to_thread(shutil.rmtree, dir_path, ignore_errors=True)


@asynccontextmanager
async def async_temp_file(suffix: str = ".tmp", prefix: str = "vanilla_") -> AsyncIterator[Path]:
    """Async context manager for temporary files."""
    fd, path_str = await asyncio.to_thread(tempfile.mkstemp, suffix=suffix, prefix=prefix)
    os.close(fd)
    file_path = Path(path_str)
    try:
        yield file_path
    finally:
        if file_path.exists():
            await asyncio.to_thread(file_path.unlink, missing_ok=True)
