"""Configuration module for API relying on environment variables.

Loads variables from a `.env` file at the repository root using python-dotenv
and exposes constants for API keys and resource paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve repository root directory
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load variables from .env at the project root
load_dotenv(ROOT_DIR / ".env")

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# Optional Google Sheets integration
AV_SHEETS_CREDENTIALS = os.getenv("AV_SHEETS_CREDENTIALS", "")
AV_SHEETS_ID = os.getenv("AV_SHEETS_ID", "")
AV_SHEETS_NAME = os.getenv("AV_SHEETS_NAME", "")

# Paths to PDF resources
DEMANDAS_PATH = ROOT_DIR / os.getenv("DEMANDAS_PATH", "data/demandas_ejemplo")
JURIS_PATH = ROOT_DIR / os.getenv("JURIS_PATH", "data/jurisprudencia")
LEGAL_CORPUS_PATH = ROOT_DIR / os.getenv("LEGAL_CORPUS_PATH", "data/legal_corpus")
CASOS_PATH = ROOT_DIR / os.getenv("CASOS_PATH", "data/casos")
