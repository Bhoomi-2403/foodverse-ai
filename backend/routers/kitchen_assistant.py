from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from services import media
from services.llm import image_part, run_validated
from services.schemas import StrList, Txt

router = APIRouter(prefix="/api/kitchen-assistant", tags=["Smart Kitchen"])

SYSTEM = (
    "You are a practical home-cooking assistant. Respond ONLY with a JSON object. "
    "Give clear, safe recipes. Include food-safety temperatures where relevant (for example poultry 74C / 165F). "
    "If ingredients come from a photo, say which are uncertain. Never promise a dish is allergen-free."
)

SCHEMA_HINT = """Return JSON with these keys:
{
  "dish_name": "string",
  "description": "one or two sentences",
  "ingredients": ["quantity and ingredient, one per item"],
  "steps": ["ordered cooking steps, one action per item"],
  "preparation_time": "e.g. '15 minutes'",
  "cooking_time": "e.g. '25 minutes'",
  "servings": "e.g. '2 servings'",
  "dietary_notes": ["e.g. vegetarian, high protein, contains gluten"],
  "allergen_notes": ["allergens likely present; say they are not exhaustive"],
  "substitutions": ["useful ingredient swaps"],
  "safety_notes": ["food-safety tips relevant to this recipe"],
  "uncertainty_note": "mention uncertain ingredients from the photo, or empty string"
}"""


class Recipe(BaseModel):
    dish_name: Txt = "Untitled dish"
    description: Txt = ""
    ingredients: StrList = Field(default_factory=list)
    steps: StrList = Field(default_factory=list)
    preparation_time: Txt = ""
    cooking_time: Txt = ""
    servings: Txt = ""
    dietary_notes: StrList = Field(default_factory=list)
    allergen_notes: StrList = Field(default_factory=list)
    substitutions: StrList = Field(default_factory=list)
    safety_notes: StrList = Field(default_factory=list)
    uncertainty_note: Txt = ""


class RecipeResponse(Recipe):
    input_notes: List[str] = Field(default_factory=list)


@router.post("/generate-recipe", response_model=RecipeResponse)
async def generate_recipe(
    text_input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None),
):
    has_file = file is not None and bool(file.filename)
    text = (text_input or "").strip()
    audio_text, warning = await media.audio_note(audio_file)
    if not (has_file or text or audio_text):
        raise HTTPException(400, "Describe your ingredients or dish, upload a photo, or record a voice note.")

    request_text = "\n".join(p for p in (text, f"Voice note: {audio_text}" if audio_text else "") if p)
    content = [{"type": "text", "text": SCHEMA_HINT}]
    if request_text:
        content.append({"type": "text", "text": f"User request:\n{request_text}"})
    if has_file:
        b64, mime = await media.load_image_upload(file)
        content.append({"type": "text", "text": "The photo shows ingredients or a dish. Use it together with the request above."})
        content.append(image_part(b64, mime))

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
    result = run_validated(messages, Recipe, vision=has_file, max_tokens=3000)
    if not result.ingredients or not result.steps:
        from services.llm import AIError
        raise AIError(502, "The AI could not produce a complete recipe. Please add more detail and try again.")
    return RecipeResponse(**result.model_dump(), input_notes=[warning] if warning else [])
