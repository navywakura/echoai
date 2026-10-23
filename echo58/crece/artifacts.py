"""Durable exclusive publication: readers see a complete immutable artifact."""
import json
import os
from pathlib import Path
import tempfile


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_directory(path):
    path = Path(path)
    if path.is_dir():
        return
    durable_directory(path.parent)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        if not path.is_dir():
            raise
    sync_directory(path.parent)


def publish(path, content, *, identical=False):
    path = Path(path)
    durable_directory(path.parent)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not identical:
                raise
            if path.read_bytes() != content:
                raise ValueError('existing immutable artifact differs')
        sync_directory(path.parent)
    finally:
        os.unlink(temporary)


def save_new(path, value, *, identical=False):
    publish(path, (json.dumps(value, indent=2, sort_keys=True)+'\n').encode(), identical=identical)
