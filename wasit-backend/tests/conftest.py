"""Ensure test env is set before any `app` imports (Settings loads at import time)."""

import os

# Minimal values so `app.core.config.settings` can load in tests without a real .env.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-min-32-chars-long!!")
os.environ.setdefault("MISTRAL_API_KEY", "test-mistral-key")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test")
os.environ.setdefault("CLOUDINARY_API_KEY", "test")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test")
# Non-empty so `chat_json` runs against respx in pipeline e2e tests (classifier tests ignore it).
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
