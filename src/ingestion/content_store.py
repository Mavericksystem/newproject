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

   