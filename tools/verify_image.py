#!/usr/bin/env python3
"""Read-only raw/XZ image inspection. No device access or writes."""
import argparse
import hashlib
import json
import lzma
import re
import struct
from pathlib import Path


def inspect_image(path, expected_sha256=None, max_bytes=4 * 1024**3):
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if expected_sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("expected SHA256 must contain exactly 64 hex characters")
    path = Path(path)
    with path.open("rb") as stream:
        compressed = stream.read(6) == b"\xfd7zXZ\x00"
    opener = lzma.open if compressed else open
    sha = hashlib.sha256()
    head, tail, size = bytearray(), b"", 0
    with opener(path, "rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            if size > max_bytes:
                raise ValueError("expanded image exceeds the configured partition-size limit")
            sha.update(block)
            if len(head) < 4096:
                head.extend(block[:4096 - len(head)])
            tail = (tail + block)[-64:]
    if head[:4] == b"\x3a\xff\x26\xed":
        raise ValueError("Android sparse image: convert and re-verify raw output separately")
    if len(head) < 2048 or struct.unpack_from("<H", head, 1024 + 56)[0] != 0xEF53:
        raise ValueError("raw ext superblock magic not found")
    log_block_size = struct.unpack_from("<I", head, 1024 + 24)[0]
    if log_block_size > 6:
        raise ValueError("unsupported ext block size")
    block_size = 1024 << log_block_size
    blocks = struct.unpack_from("<I", head, 1024 + 4)[0]
    incompat = struct.unpack_from("<I", head, 1024 + 96)[0]
    if incompat & 0x80:
        blocks |= struct.unpack_from("<I", head, 1024 + 336)[0] << 32
    fs_bytes = blocks * block_size
    if not blocks or fs_bytes > size:
        raise ValueError("ext filesystem declares blocks beyond the available image")
    digest = sha.hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise ValueError("expanded/raw SHA256 does not match expected value")
    return {
        "input_format": "xz" if compressed else "raw",
        "expanded_bytes": size,
        "sha256_raw": digest,
        "expected_hash_checked": expected_sha256 is not None,
        "ext_block_size": block_size,
        "ext_filesystem_bytes": fs_bytes,
        "shared_blocks_flag": bool(struct.unpack_from("<I", head, 1024 + 100)[0] & 0x4000),
        "avb_footer_magic_present": tail[:4] == b"AVBf",
        "limits": "Not a complete filesystem, AVB signature/trust, or compatibility check.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--max-bytes", type=int, default=4 * 1024**3)
    args = parser.parse_args()
    try:
        result = inspect_image(args.image, args.expected_sha256, args.max_bytes)
    except (OSError, ValueError, EOFError, lzma.LZMAError) as exc:
        parser.exit(1, "Image check failed: " + str(exc) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
