from typing import List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field, field_validator

from services import media
from services.llm import image_part, run_validated
from services.schemas import Num, StrList, Txt, clamp_pct

router = APIRouter(prefix="/api/freshness-detector", tags=["Freshness Detector"])

LEVELS = ["Appears fresh", "Possible deterioration", "Visible signs of spoilage", "Inconclusive"]

SYSTEM = (
    "You are a cautious food-quality assistant. Respond ONLY with a JSON object. "
    "You judge VISIBLE appearance only. You can never certify that food is safe: bacteria, toxins and "
    "improper storage are invisible. Never say 'safe to eat' or '100% safe'. Never suggest tasting or smelling "
    "food to test it. Treat food-specific context properly (for example brown spots on a banana usually mean "
    "ripeness, not danger; visible mould on soft or cooked food means it should be discarded). "
    "Use 'Inconclusive' when the photo is unclear. Take the stated storage time and conditions into account."
)

SCHEMA_HINT = f"""Return JSON with these keys:
{{
  "item_name": "string",
  "freshness_level": one of {LEVELS},
  "confidence": number 0-100,
  "detected_signs": ["visible signs you actually see; empty list if none"],
  "reasoning": "explanation based on visible evidence and the storage context",
  "recommendation": "practical next step suited to this food type",
  "safety_status": "carefully worded, e.g. 'No visible spoilage, but safety cannot be confirmed from a photo' or 'Discard recommended'",
  "limitations": ["what this photo-based check cannot tell"]
}}"""


class FreshnessAnalysis(BaseModel):
    item_name: Txt = "Unknown"
    freshness_level: Txt = "Inconclusive"
    confidence: Num = None
    detected_signs: StrList = Field(default_factory=list)
    reasoning: Txt = ""
    recommendation: Txt = ""
    safety_status: Txt = ""
    limitations: StrList = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def _pct(cls, v):
        return clamp_pct(v)

    @field_validator("freshness_level")
    @classmethod
    def _level(cls, v: str):
        low = v.lower()
        for lvl in LEVELS:
            if low == lvl.lower():
                return lvl
        if "spoil" in low or "rot" in low or "mould" in low or "mold" in low:
            return LEVELS[2]
        if "fresh" in low and "not" not in low:
            return LEVELS[0]
        if "moderate" in low or "deteriorat" in low or "aging" in low or "ripe" in low:
            return LEVELS[1]
        return LEVELS[3]


class FreshnessResponse(FreshnessAnalysis):
    disclaimer: str = (
        "This is a visual assessment only. It cannot detect bacteria, toxins or unsafe storage. "
        "When in doubt, throw it out."
    )
    input_notes: List[str] = Field(default_factory=list)


@router.post("/analyze", response_model=FreshnessResponse)
async def analyze(
    file: UploadFile = File(...),
    storage_time: Optional[str] = Form(None),
    storage_type: Optional[str] = Form(None),
    text_context: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
):
    b64, mime = await media.load_image_upload(file)
    audio_text, audio_warning = await media.audio_note(audio_file)

    ctx = []
    if (storage_time or "").strip():
        ctx.append(f"Stored for: {storage_time.strip()}")
    if (storage_type or "").strip():
        ctx.append(f"Storage conditions: {storage_type.strip()}")
    if (text_context or "").strip():
        ctx.append(f"Notes: {text_context.strip()}")
    if audio_text:
        ctx.append(f"Voice note: {audio_text}")
    context = "\n".join(ctx) if ctx else "No storage information was provided; mention this as a limitation."

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": [
            {"type": "text", "text": f"{SCHEMA_HINT}\n\nContext:\n{context}"},
            image_part(b64, mime),
        ]},
    ]
    result = run_validated(messages, FreshnessAnalysis, vision=True)
    return FreshnessResponse(**result.model_dump(), input_notes=[audio_warning] if audio_warning else [])
