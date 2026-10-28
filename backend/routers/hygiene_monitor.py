import io
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

from services import media
from services.llm import AIError, image_part, run_validated
from services.schemas import StrList, Txt

router = APIRouter(prefix="/api/hygiene-monitor", tags=["Hygiene Monitor"])

SEVERITY_WEIGHTS = {"high": 15, "medium": 8, "low": 3}

SYSTEM = (
    "You are a preliminary kitchen hygiene observer. Respond ONLY with a JSON object. "
    "Report only what is clearly VISIBLE. Do not invent violations. Gloves, hair coverings and similar items "
    "are context dependent, so only flag them if the context says they are required or handling of ready-to-eat "
    "food is clearly unsafe. If something cannot be seen, list it under unobserved. Do not give a numeric score."
)

SCHEMA_HINT = """Return JSON with these keys:
{
  "violations": [
    {"violation": "short name", "severity": "High" | "Medium" | "Low",
     "location": "where in the frame", "reason": "visible evidence"}
  ],
  "positive_observations": ["good practices that are visible"],
  "unobserved": ["relevant things that could not be assessed from this image"],
  "ai_summary": "two or three neutral sentences"
}
Use an empty violations list if none are visible."""


class Violation(BaseModel):
    violation: Txt = ""
    severity: Txt = "Low"
    location: Txt = ""
    reason: Txt = ""
    timestamp: Optional[float] = None


class FrameObservation(BaseModel):
    violations: List[Violation] = Field(default_factory=list)
    positive_observations: StrList = Field(default_factory=list)
    unobserved: StrList = Field(default_factory=list)
    ai_summary: Txt = ""


class HygieneResponse(BaseModel):
    overall_score: int
    score_method: str
    violations: List[Violation]
    positive_observations: List[str]
    unobserved: List[str]
    ai_summary: str
    frames_analysed: int
    frames_failed: int = 0
    media_type: str
    video_info: Optional[dict] = None
    limitations: List[str]
    input_notes: List[str] = Field(default_factory=list)


LIMITATIONS = [
    "Preliminary AI review of uploaded media only. It is not real-time monitoring and does not replace a qualified inspection.",
    "Only the sampled image or frames were reviewed, so conditions at other times or places were not observed.",
    "Observations may be wrong; verify each finding before acting on it.",
]


def norm_severity(s: str) -> str:
    s = (s or "").strip().lower()
    return s.capitalize() if s in SEVERITY_WEIGHTS else "Low"


def compute_score(violations: List[Violation], frames: int) -> int:
    """Start at 100 and deduct per distinct violation by severity (High 15, Medium 8, Low 3).
    Repeated sightings across frames are averaged so a long video is not unfairly penalised."""
    frames = max(1, frames)
    total = sum(SEVERITY_WEIGHTS[norm_severity(v.severity).lower()] for v in violations)
    return int(max(0, min(100, round(100 - total / frames))))


def dedupe(violations: List[Violation]) -> List[Violation]:
    seen, out = set(), []
    for v in violations:
        key = (re.sub(r"\W+", " ", v.violation.lower()).strip(), norm_severity(v.severity))
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def observe(b64: str, context: str, label: str) -> FrameObservation:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": [
            {"type": "text", "text": f"{SCHEMA_HINT}\n\nMedia: {label}\nKitchen context / rules: {context or 'none supplied'}"},
            image_part(b64),
        ]},
    ]
    return run_validated(messages, FrameObservation, vision=True)


def build_response(observations: list[tuple[Optional[float], FrameObservation]], failed: int, media_type: str,
                   video_info: Optional[dict], notes: list[str]) -> HygieneResponse:
    all_v: List[Violation] = []
    positives, unobserved, summaries = [], [], []
    for ts, obs in observations:
        for v in obs.violations:
            v.severity = norm_severity(v.severity)
            v.timestamp = ts
            all_v.append(v)
        positives += obs.positive_observations
        unobserved += obs.unobserved
        if obs.ai_summary:
            summaries.append(obs.ai_summary)
    n = len(observations)
    if failed:
        notes = notes + [f"{failed} frame(s) could not be analysed and are not reflected in the score."]
    return HygieneResponse(
        overall_score=compute_score(dedupe(all_v) if n == 1 else all_v, n),
        score_method="100 minus severity penalties (High 15, Medium 8, Low 3), averaged over analysed frames.",
        violations=sorted(dedupe(all_v), key=lambda v: -SEVERITY_WEIGHTS[v.severity.lower()]),
        positive_observations=list(dict.fromkeys(positives))[:12],
        unobserved=list(dict.fromkeys(unobserved))[:12],
        ai_summary=" ".join(summaries[:3]) if summaries else "No summary available.",
        frames_analysed=n, frames_failed=failed, media_type=media_type, video_info=video_info,
        limitations=LIMITATIONS, input_notes=notes,
    )


@router.post("/analyze", response_model=HygieneResponse)
async def analyze(
    file: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    context: Optional[str] = Form(None),
):
    ctx = (context or "").strip()
    if video is not None and video.filename:
        data, ext = await media.load_video_upload(video)
        with media.temp_file(data, ext) as path:
            frames, meta = media.extract_video_frames(path)
        observations, failed, last_error = [], 0, None
        for ts, b64 in frames:
            try:
                observations.append((ts, observe(b64, ctx, f"Video frame at {ts}s")))
            except AIError as exc:
                if exc.status_code in (503, 429):  # systemic, no point continuing
                    raise
                failed += 1
                last_error = exc
        if not observations:
            raise last_error or AIError(502, "No frames could be analysed.")
        return build_response(observations, failed, "video", meta, [])
    if file is not None and file.filename:
        b64, _ = await media.load_image_upload(file)
        return build_response([(None, observe(b64, ctx, "Static image"))], 0, "image", None, [])
    raise HTTPException(400, "Upload a kitchen image (field 'file') or a video (field 'video').")


class ReportRequest(BaseModel):
    result: dict


def _safe(text) -> str:
    return str(text).encode("latin-1", "replace").decode("latin-1")


@router.post("/report")
async def report(req: ReportRequest):
    """Render a PDF from a previous analysis result."""
    from fpdf import FPDF

    try:
        r = HygieneResponse(**req.result)
    except Exception:
        raise HTTPException(422, "The supplied result is not a valid hygiene analysis.")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "FoodVerse AI - Hygiene Observation Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _safe(f"Generated {datetime.now():%Y-%m-%d %H:%M} | Media: {r.media_type} | Frames analysed: {r.frames_analysed}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def h(t):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, t, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

    def para(t):
        pdf.multi_cell(0, 5, _safe(t), new_x="LMARGIN", new_y="NEXT")

    h(f"Indicative score: {r.overall_score}/100")
    para(r.score_method)
    h("Summary")
    para(r.ai_summary)
    h("Potential issues")
    if r.violations:
        for v in r.violations:
            ts = f" @ {v.timestamp}s" if v.timestamp is not None else ""
            para(f"- [{v.severity}] {v.violation}{ts} ({v.location}): {v.reason}")
    else:
        para("None observed in the reviewed media.")
    h("Positive observations")
    para("\n".join(f"- {p}" for p in r.positive_observations) or "None recorded.")
    h("Not observed")
    para("\n".join(f"- {p}" for p in r.unobserved) or "None recorded.")
    h("Limitations")
    para("\n".join(f"- {p}" for p in r.limitations))
    out = bytes(pdf.output())
    return Response(out, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="hygiene-report.pdf"'})
