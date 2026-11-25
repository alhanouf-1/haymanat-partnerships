"""Content-hash based asset versions used for cache busting."""
import hashlib
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=512)
def _hash(path: str, mtime_ns: int, size: int) -> str:
    # mtime/size are part of the cache key, so a replaced file is re-hashed automatically.
    return hashlib.sha1(Path(path).read_bytes(), usedforsecurity=False).hexdigest()[:10]


def asset_version(static_folder, filename):
    """Return a short content hash for a file inside static_folder, or None if unavailable/unsafe."""
    if not static_folder or not filename:
        return None
    try:
        base = Path(static_folder).resolve()
        target = (base / filename).resolve()
        if base not in target.parents or not target.is_file():
            return None
        st = target.stat()
        return _hash(str(target), st.st_mtime_ns, st.st_size)
    except (OSError, ValueError):
        return None
