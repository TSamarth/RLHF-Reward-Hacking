"""Typed config, loaded from .env. Later phases add OLLAMA_HOST and API keys here."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CONTAINER_BIN: str = os.getenv("CONTAINER_BIN", "podman")
IMAGE_NAME: str = "redactor-sandbox:latest"
