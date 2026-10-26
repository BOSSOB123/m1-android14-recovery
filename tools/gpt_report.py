#!/usr/bin/env python3
"""Inspect a saved primary GPT; do not expose disk or partition GUIDs."""
import argparse
import json
import struct
import zlib
from pathlib import Path


def inspect_gpt(data, sector_size=512):
    if sector_size not in (512, 4096):
        raise ValueError("sector size must be 512 or 4096")
    offset = sector_size
    if len(data) < offset + 92 or data[offset:offset + 8] != b"EFI PART":
        raise ValueError("primary GPT header missing at LBA 1")
    header_size, stored_crc = struct.unpack_from("<II", data, offset + 12)
    if not 92 <= header_size <= sector_size or offset + header_size > len(data):
        raise ValueError("invalid or truncated GPT header length")
    header = bytearray(data[offset:offset + header_size])
    header[16:20] = b"\0" * 4
    if zlib.crc32(header) != stored_crc:
        raise ValueError("GPT header CRC mismatch")
    current_lba = struct.unpack_from("<Q", data, offset + 24)[0]
    first_usable, last_usable = struct.unpack_from("<QQ", data, offset + 40)
    if current_lba != 1 or first_usable > last_usable:
        raise ValueError("invalid primary GPT geometry")
    table_lba, count, entry_size, table_crc = struct.unpack_from("<QIII", data, offset + 72)
    if entry_size < 128 or entry_size % 128 or not count or table_lba < 2:
        raise ValueError("invalid GPT partition table shape")
    begin, length = table_lba * sector_size, count * entry_size
    if begin + length > len(data):
        raise ValueError("partition table is truncated")
    entries = data[begin:begin + length]
    if zlib.crc32(entries) != table_crc:
        raise ValueError("GPT partition table CRC mismatch")
    partitions = []
    for i in range(count):
        entry = entries[i * entry_size:(i + 1) * entry_size]
        if not any(entry[:16]):
            continue
        first, last = struct.unpack_from("<QQ", entry, 32)
        if first > last or first < first_usable or last > last_usable:
            raise ValueError("partition outside usable GPT bounds")
        name = entry[56:128].decode("utf-16le").rstrip("\0")
        partitions.append({"index": i + 1, "name": name,
                           "offset_bytes": first * sector_size,
                           "length_bytes": (last - first + 1) * sector_size})
    ordered = sorted(partitions, key=lambda x: x["offset_bytes"])
    for left, right in zip(ordered, ordered[1:]):
        if left["offset_bytes"] + left["length_bytes"] > right["offset_bytes"]:
            raise ValueError("overlapping GPT partitions")
    return {"header_crc_valid": True, "entries_crc_valid": True,
            "sector_size": sector_size, "partitions": partitions,
            "guid_values": "intentionally omitted",
            "limits": "Primary GPT only; no backup-GPT or actual-device comparison."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gpt", type=Path)
    parser.add_argument("--sector-size", type=int, default=512)
    args = parser.parse_args()
    try:
        # Limit input to the expected small saved GPT region, not a disk image.
        with args.gpt.open("rb") as stream:
            data = stream.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError("use a saved GPT region of at most 16 MiB")
        result = inspect_gpt(data, args.sector_size)
    except (OSError, ValueError, UnicodeError, struct.error) as exc:
        parser.exit(1, "GPT check failed: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
