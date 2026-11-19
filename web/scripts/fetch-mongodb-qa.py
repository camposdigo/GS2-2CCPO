"""Fetch only mongod.exe from the official ZIP using HTTP ranges (local QA).

The archive also contains large debug symbols. zipfile validates the selected
member's CRC; HTTPS authenticates the host. The executable in the official ZIP
may be unsigned; inspect Authenticode separately. No service is installed.
"""
from __future__ import annotations

import io
import pathlib
import urllib.request
import zipfile

URL = "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.2.12.zip"
DEST = pathlib.Path(__file__).resolve().parents[1] / ".tools" / "mongodb" / "mongod.exe"


class RemoteArchive(io.RawIOBase):
    def __init__(self, url: str):
        self.url = url
        self.pos = 0
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=30) as response:
            self.length = int(response.headers["Content-Length"])

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.length + offset
        return self.pos

    def tell(self):
        return self.pos

    def read(self, size=-1):
        if size < 0:
            size = self.length - self.pos
        if not size:
            return b""
        end = min(self.length - 1, self.pos + size - 1)
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 206:
                raise RuntimeError("Official host did not honor HTTP Range; stopped to avoid downloading debug symbols.")
            body = response.read()
        if len(body) != end - self.pos + 1:
            raise RuntimeError("Incomplete archive range.")
        self.pos += len(body)
        return body


if __name__ == "__main__":
    if DEST.exists():
        print(f"Already present: {DEST}")
    else:
        with zipfile.ZipFile(RemoteArchive(URL)) as archive:
            members = [entry for entry in archive.infolist() if entry.filename.endswith("/bin/mongod.exe")]
            if len(members) != 1:
                raise RuntimeError("Unexpected archive members.")
            selected = members[0]
            print(f"Official archive: {URL}", flush=True)
            print(f"Selected executable: {selected.file_size:,} bytes; download: {selected.compress_size:,} bytes", flush=True)
            payload = archive.read(selected)
        DEST.parent.mkdir(parents=True, exist_ok=True)
        DEST.write_bytes(payload)
        print(f"Saved CRC-verified member to {DEST}")
