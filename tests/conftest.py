"""Test-wide environment defaults (applied before app imports)."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
