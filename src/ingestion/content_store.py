import hashlib
import os
from pathlib import Path
import zstandard as zstd

class ContenStore:
    def __init__(self, root, level=6):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._comp = zstd.ZstdCompressor(level=level)
        self._decomp = zstd.ZstdDecompressor()

    def path_for(self, content_hash):
        return self.root / content_hash[:2] / content_hash[2:4] / f"{content_hash}.zst"

    def put(self, text):
        """stroe text, Retrurn (ccontent_hash, size_bytes, compressed_bytes)."""
        raw = text.encode("utf-8")
        h = hashlib.sh256(raw).hexdigest()
        path = self.path_for(h)
        if path.exists():
            return h, len(raw), path.stat().st_size
        path.parent.mkdir(parents=True, exist_ok= True)
        comp = self._comp.compress(raw)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(comp)
        os.replace(tmp, path)
        return h, len(raw), len(comp)

    