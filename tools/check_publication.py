#!/usr/bin/env python3
"""Catch common accidental private/binary additions; not a security audit."""
import re
from pathlib import Path


def problems(root):
    findings = []
    binary_suffixes = {".img", ".bin", ".apk", ".xapk", ".apkm", ".xz", ".zip", ".dmg", ".pkg", ".log", ".sqlite"}
    patterns = {
        "local home path": re.compile("/" + "Users" + r"/[^/\s<>]+/"),
        "GitHub credential": re.compile(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}"),
        "private key": re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----"),
        "hardware MAC": re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
    }
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(x in {".git", "__pycache__", ".venv"} for x in relative.parts) or not path.is_file():
            continue
        if path.is_symlink():
            findings.append((str(relative), "unexpected symlink"))
            continue
        if path.suffix.lower() in binary_suffixes or path.stat().st_size > 1024 * 1024:
            findings.append((str(relative), "binary, backup, log, or oversized file"))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            findings.append((str(relative), "non-UTF8 file"))
            continue
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append((str(relative), label))
    return findings


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    findings = problems(root)
    for path, label in findings:
        print(path + ": " + label)
    if findings:
        raise SystemExit(1)
    print("Publication checks passed. Manual privacy/content review is still required.")
