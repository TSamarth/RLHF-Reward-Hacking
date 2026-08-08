"""Typed config, loaded from .env. Later phases add OLLAMA_HOST and API keys here."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CONTAINER_BIN: str = os.getenv("CONTAINER_BIN", "podman")
IMAGE_NAME: str = "redactor-sandbox:latest"

# Ollama (local model, dev + volume).
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL: str = "qwen3.6:27b-mtp-q4_K_M"  # NOT qwen3.6:27b — that tag isn't on the host
TEMPERATURE: float = 0.0
OLLAMA_TIMEOUT_S: float = 600.0  # 27B model on a remote GPU can take minutes for one turn

# Agent loop caps (SPEC §4).
STEP_CAP: int = 60
WALL_CLOCK_S: float = 20 * 60
