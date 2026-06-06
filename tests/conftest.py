"""Test-wide environment defaults (applied before app imports)."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_WARMUP", "false")  # don't load bge-m3 in unit tests
os.environ.setdefault("EMBEDDING_DEVICE", "cpu")
