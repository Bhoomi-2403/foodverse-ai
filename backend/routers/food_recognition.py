from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from services import media
from services.llm import image_part, run_validated
from services.schemas import Num, StrList, Txt, clamp_pct

router = APIRouter(prefix="/api/food-recognition", tags=["Food Recognition"])

SYSTEM = (
    "You are a careful food and nutrition analyst. Respond ONLY with a JSON object. "
    "You only see a photo and/or short notes, so every nutrition value is a rough ESTIMATE, never exact. "
    "If you cannot confidently identify the food, say so, set primary_food to \"Unidentified\" and use null "
    "for numbers you cannot estimate. Never invent precision."
)

SCHEMA_HINT = """Return JSON with these keys:
{
  "detected_foods": [ {"name": "string", "estimated_portion": "string or null"} ],
  "primary_food": "string",
  "description": "one or two sentences describing what is visible",
  "estimated_portion": "string such as '1 bowl (~300 g)' or null if unclear",
  "calories": number or null (kcal for the whole visible portion),
  "protein": number or null (grams),
  "carbohydrates": number or null (grams),
  "fats": number or null (grams),
  "fiber": number or null (grams),
  "sugar": number or null (grams),
  "confidence": number 0-100 (how sure you are about the identification),
  "reasoning": "how you reached the identification and estimates",
  "limitations": ["what a photo cannot tell you, e.g. oil used, exact weight, hidden ingredients"]
}"""


class DetectedFood(BaseModel):
    name: Txt = ""
    estimated_portion: Optional[str] = None


class FoodAnalysis(BaseModel):
    detected_foods: List[DetectedFood] = Field(default_factory=list)
    primary_food: Txt = "Unidentified"
    description: Txt = ""
    estimated_portion: Optional[str] = None
    calories: Num = None
    protein: Num = None
    carbohydrates: Num = None
    fats: Num = None
    fiber: Num = None
    sugar: Num = None
    confidence: Num = None
    reasoning: Txt = ""
    limitations: StrList = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def _pct(cls, v):
        return clamp_pct(v)


class FoodRecognitionResponse(FoodAnalysis):
    is_estimate: bool = True
    nutrition_note: str = (
        "Nutrition values are AI estimates from a photo and are not verified nutritional data. "
        "Actual values depend on weight, ingredients and cooking method."
    )
    input_notes: List[str] = Field(default_factory=list)


@router.post("/analyze", response_model=FoodRecognitionResponse)
async def analyze(
    file: Optional[UploadFile] = File(None),
    text_context: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
):
    has_file = file is not None and bool(file.filename)
    text = (text_context or "").strip()
    audio_text, audio_warning = await media.audio_note(audio_file)
    if not has_file and not text and not audio_text:
        raise HTTPException(400, "Provide a food image, a text description, or a voice note.")

    notes = [audio_warning] if audio_warning else []
    content = [{"type": "text", "text": SCHEMA_HINT}]
    context_parts = [p for p in (text, f"Voice note: {audio_text}" if audio_text else "") if p]
    if context_parts:
        content.append({"type": "text", "text": "User context:\n" + "\n".join(context_parts)})
    if has_file:
        b64, mime = await media.load_image_upload(file)
        content.append(image_part(b64, mime))
    else:
        content.append({"type": "text", "text": "No image was supplied; analyse the description only and say so in limitations."})
        notes.append("No image supplied: estimate is based on the text description only.")

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
    result = run_validated(messages, FoodAnalysis, vision=has_file)
    return FoodRecognitionResponse(**result.model_dump(), input_notes=notes)
