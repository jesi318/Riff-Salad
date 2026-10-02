"""
Configuration loaded from environment variables.
Never hard-code model names in application logic.
"""
import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER  = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL     = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
DATA_DIR      = os.path.abspath(os.getenv("DATA_DIRECTORY", "./data"))
