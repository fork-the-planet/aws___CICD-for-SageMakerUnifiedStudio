"""SMUS CI/CD CLI package."""

import sys
from importlib.metadata import PackageNotFoundError, version

# Ensure stdout/stderr use UTF-8 encoding on all platforms (including Windows)
# This prevents UnicodeEncodeError when printing emoji on Windows consoles
# that default to cp1252 encoding
for _stream in (sys.stdout, sys.stderr):
    if _stream and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

try:
    __version__ = version("aws-smus-cicd-cli")
except PackageNotFoundError:
    __version__ = "unknown"
