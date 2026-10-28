"""Central configuration. Values are read from the environment at call time."""
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_VISION_MODEL = "qwen/qwen3.8-27b"
DEFAULT_FALLBACK_MODELS = "meta-llama/llama-4-scout-17b-16e-instruct,qwen/qwen3.6-27b"


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def groq_api_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return key or None


def vision_models() -> list[str]:
    """Primary vision model followed by fallbacks (used if the primary is retired)."""
    primary = os.environ.get("GROQ_VISION_MODEL", DEFAULT_VISION_MODEL).strip()
    fallbacks = os.environ.get("GROQ_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS).split(",")
    out = [primary] + [m.strip() for m in fallbacks if m.strip()]
    return list(dict.fromkeys(out))


def text_models() -> list[str]:
    primary = os.environ.get("GROQ_TEXT_MODEL", "").strip()
    models = vision_models()
    return list(dict.fromkeys(([primary] if primary else []) + models))


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


def max_upload_bytes() -> int:
    return _int("MAX_UPLOAD_MB", 10) * 1024 * 1024


def max_video_bytes() -> int:
    return _int("MAX_VIDEO_MB", 60) * 1024 * 1024


def max_video_frames() -> int:
    return max(1, min(_int("MAX_VIDEO_FRAMES", 6), 12))


def llm_timeout() -> int:
    return _int("LLM_TIMEOUT_SECONDS", 60)
