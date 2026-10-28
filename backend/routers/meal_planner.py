import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel, Field

from services.llm import AIError, run_validated
from services.schemas import Num, StrList, Txt

router = APIRouter(prefix="/api/meal-planner", tags=["Meal Planner"])

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very active": 1.9}
MEALS = ["breakfast", "mid_morning_snack", "lunch", "evening_snack", "dinner"]
MIN_KCAL = {"male": 1500, "female": 1200}

SYSTEM = (
    "You are a registered-dietitian style meal planning assistant. Respond ONLY with a JSON object. "
    "Never include any listed allergen or food the user avoids. Respect the diet type and cuisine. "
    "Use numeric values (kcal, grams) for nutrition. Do not give medical treatment advice."
)


class Macros(BaseModel):
    protein_g: Num = None
    carbs_g: Num = None
    fats_g: Num = None


class MealDetails(BaseModel):
    dish_name: Txt = ""
    description: Txt = ""
    ingredients: StrList = Field(default_factory=list)
    calories: Num = None
    macros: Macros = Field(default_factory=Macros)
    reasoning: Txt = ""
    portion_size: Txt = ""
    prep_style: Txt = ""


class MealAlternatives(BaseModel):
    original_dish: Txt = ""
    alternatives: List[MealDetails] = Field(default_factory=list)


class DailyMealPlan(BaseModel):
    breakfast: MealDetails
    mid_morning_snack: MealDetails
    lunch: MealDetails
    evening_snack: MealDetails
    dinner: MealDetails
    hydration_target: Txt = ""


class WeeklyReport(BaseModel):
    adherence_score: Num = None
    calorie_balance: Txt = ""
    macro_balance: Txt = ""
    consistency: Txt = ""
    concern_areas: StrList = Field(default_factory=list)
    highlights: StrList = Field(default_factory=list)
    next_week_suggestions: StrList = Field(default_factory=list)
    motivation: Txt = ""


class LLMPlan(BaseModel):
    user_profile_summary: Txt = ""
    daily_plan: DailyMealPlan
    alternatives: List[MealAlternatives] = Field(default_factory=list)
    weekly_report: Optional[WeeklyReport] = None
    cautions: StrList = Field(default_factory=list)


class Targets(BaseModel):
    bmr: int
    tdee: int
    target_calories: int
    protein_g: int
    carbs_g: int
    fats_g: int
    method: str


class DailyTotals(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fats_g: float


class FullMealPlanResponse(LLMPlan):
    targets: Targets
    daily_totals: DailyTotals
    warnings: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "These are general estimates, not medical advice. Consult a qualified doctor or dietitian, "
        "especially if you have a medical condition."
    )


def compute_targets(age: int, gender: str, height: float, weight: float, activity: str, goals: str) -> Targets:
    """Mifflin-St Jeor BMR x activity factor, adjusted for goal, with a safe calorie floor."""
    male = gender.strip().lower().startswith("m")
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if male else -161)
    tdee = bmr * ACTIVITY.get(activity.strip().lower(), 1.55)
    g = goals.lower()
    if any(k in g for k in ("lose", "loss", "fat", "cut")):
        target = tdee * 0.85
    elif any(k in g for k in ("gain", "muscle", "bulk")):
        target = tdee * 1.10
    else:
        target = tdee
    floor = MIN_KCAL["male" if male else "female"]
    target = max(target, floor)
    protein_per_kg = 1.8 if any(k in g for k in ("muscle", "gain")) else 1.4
    protein = protein_per_kg * weight
    fats = target * 0.27 / 9
    carbs = max(0.0, (target - protein * 4 - fats * 9) / 4)
    return Targets(bmr=round(bmr), tdee=round(tdee), target_calories=round(target), protein_g=round(protein),
                   carbs_g=round(carbs), fats_g=round(fats),
                   method="Mifflin-St Jeor BMR x activity factor; -15% for fat loss, +10% for muscle gain; "
                          "protein 1.4-1.8 g/kg; fats 27% of calories; remainder carbohydrates. Estimates only.")


def split_terms(text: str) -> List[str]:
    parts = [p.strip().lower() for p in re.split(r"[,;/]|\band\b", text or "")]
    return [p for p in parts if p and p not in ("none", "no", "n/a", "na", "nil", "nothing")]


def find_allergen_hits(plan: DailyMealPlan, terms: List[str]) -> List[str]:
    hits = []
    for name in MEALS:
        meal: MealDetails = getattr(plan, name)
        haystack = " ".join([meal.dish_name, *meal.ingredients]).lower()
        for t in terms:
            if re.search(rf"\b{re.escape(t)}s?\b", haystack):
                hits.append(f"{name.replace('_', ' ')}: contains '{t}'")
    return hits


def totals(plan: DailyMealPlan) -> DailyTotals:
    cal = p = c = f = 0.0
    for name in MEALS:
        m: MealDetails = getattr(plan, name)
        cal += m.calories or 0
        p += m.macros.protein_g or 0
        c += m.macros.carbs_g or 0
        f += m.macros.fats_g or 0
    return DailyTotals(calories=round(cal), protein_g=round(p), carbs_g=round(c), fats_g=round(f))


@router.post("/generate", response_model=FullMealPlanResponse)
async def generate(
    age: int = Form(...),
    gender: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    activity_level: str = Form("Moderate"),
    medical_conditions: str = Form("None"),
    goals: str = Form(...),
    diet_type: str = Form("Standard"),
    cuisine: str = Form("Global"),
    allergies: str = Form("None"),
    foods_to_avoid: str = Form("None"),
    recent_history: str = Form("No data"),
    weight_change: str = Form("Stable"),
):
    if not 14 <= age <= 100:
        raise HTTPException(422, "Age must be between 14 and 100. Please consult a professional for younger users.")
    if not 100 <= height <= 250:
        raise HTTPException(422, "Height must be between 100 and 250 cm.")
    if not 30 <= weight <= 300:
        raise HTTPException(422, "Weight must be between 30 and 300 kg.")
    if not goals.strip():
        raise HTTPException(422, "Please choose at least one goal.")

    targets = compute_targets(age, gender, height, weight, activity_level, goals)
    banned = split_terms(allergies) + split_terms(foods_to_avoid)
    conditions = split_terms(medical_conditions)

    prompt = f"""Create a one-day plan with 5 meals plus alternatives and a short weekly report.

PROFILE: age {age}, {gender}, {height} cm, {weight} kg, activity {activity_level}.
GOALS: {goals}. DIET: {diet_type}. CUISINE: {cuisine}.
MEDICAL CONDITIONS (user-declared): {medical_conditions}.
MUST NOT INCLUDE (allergies / avoid): {', '.join(banned) if banned else 'none'}.
RECENT HISTORY: {recent_history}. RECENT WEIGHT CHANGE: {weight_change}.
DAILY TARGETS: about {targets.target_calories} kcal, protein {targets.protein_g} g, carbs {targets.carbs_g} g, fats {targets.fats_g} g.

Return JSON:
{{
  "user_profile_summary": "short neutral summary",
  "daily_plan": {{
    "breakfast|mid_morning_snack|lunch|evening_snack|dinner": {{
      "dish_name": "", "description": "", "ingredients": ["with quantities"],
      "calories": number, "macros": {{"protein_g": number, "carbs_g": number, "fats_g": number}},
      "reasoning": "", "portion_size": "", "prep_style": ""
    }},
    "hydration_target": "e.g. about 2.5 litres of water"
  }},
  "alternatives": [{{"original_dish": "", "alternatives": [ same meal object, 1-2 items ]}}],
  "weekly_report": {{"adherence_score": number 0-100 or null, "calorie_balance": "", "macro_balance": "",
     "consistency": "", "concern_areas": [], "highlights": [], "next_week_suggestions": [], "motivation": ""}},
  "cautions": []
}}
Meal calories should add up close to the daily target. If there is no history, say the weekly report is a template."""

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]

    plan: Optional[LLMPlan] = None
    hits: List[str] = []
    for attempt in range(2):
        plan = run_validated(messages, LLMPlan, max_tokens=4000, temperature=0.4)
        hits = find_allergen_hits(plan.daily_plan, banned) if banned else []
        if not hits:
            break
        messages.append({"role": "user", "content": "Your plan included excluded items: " + "; ".join(hits) +
                         ". Regenerate the whole plan without them."})
    if hits:
        raise AIError(502, "The AI plan kept including a food you listed as an allergy or avoid, so it was discarded for your safety. Please try again.")

    # also scrub alternatives for the same terms
    for alt in plan.alternatives:
        alt.alternatives = [a for a in alt.alternatives
                            if not any(re.search(rf"\b{re.escape(t)}s?\b", " ".join([a.dish_name, *a.ingredients]).lower())
                                       for t in banned)]

    tot = totals(plan.daily_plan)
    warnings = list(plan.cautions)
    if tot.calories and abs(tot.calories - targets.target_calories) / targets.target_calories > 0.15:
        warnings.append(f"Meal calories ({int(tot.calories)} kcal) differ from the estimated target ({targets.target_calories} kcal) by more than 15%.")
    if conditions:
        warnings.append("You listed a medical condition. Please have this plan reviewed by a doctor or registered dietitian.")
    if targets.target_calories == MIN_KCAL["male" if gender.lower().startswith("m") else "female"]:
        warnings.append("The calorie target was raised to a safe minimum; very low intakes should only be followed under medical supervision.")

    data = plan.model_dump()
    data["cautions"] = []
    return FullMealPlanResponse(**data, targets=targets, daily_totals=tot, warnings=list(dict.fromkeys(warnings)))
