import io
import os
import sys

import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app  # noqa: E402
from services import llm  # noqa: E402
from routers import hygiene_monitor as hy, meal_planner as mp  # noqa: E402

client = TestClient(app)


def png_bytes(size=(64, 64)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 120, 40)).save(buf, "PNG")
    return buf.getvalue()


def img(name="a.png", data=None):
    return ("file", (name, data or png_bytes(), "image/png"))


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    llm.reset_client()


def mock_llm(monkeypatch, payload):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: payload)


def test_health_and_root():
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").json()["status"] == "active"
    assert client.get("/docs").status_code == 200


def test_food_requires_input():
    assert client.post("/api/food-recognition/analyze").status_code == 400


def test_food_rejects_bad_image():
    r = client.post("/api/food-recognition/analyze", files=[("file", ("x.png", b"not an image", "image/png"))])
    assert r.status_code == 400


def test_food_rejects_oversize(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    assert client.post("/api/food-recognition/analyze", files=[img()]).status_code == 413


def test_food_missing_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY")
    llm.reset_client()
    monkeypatch.setattr("config.load_dotenv", lambda: None, raising=False)
    r = client.post("/api/food-recognition/analyze", files=[img()])
    assert r.status_code == 503 and "GROQ_API_KEY" in r.json()["detail"]


def test_food_valid_tolerant_numbers(monkeypatch):
    mock_llm(monkeypatch, {"primary_food": "Apple", "calories": "95 kcal", "protein": 0.5, "confidence": 0.9,
                           "limitations": "photo only", "detected_foods": [{"name": "Apple"}]})
    r = client.post("/api/food-recognition/analyze", files=[img()]).json()
    assert r["calories"] == 95 and r["confidence"] == 90 and r["is_estimate"] is True
    assert r["limitations"] == ["photo only"]


def test_invalid_json_rejected():
    with pytest.raises(llm.AIError) as e:
        llm.extract_json("sorry, I cannot do that")
    assert e.value.status_code == 502
    assert llm.extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_provider_failure_is_error_not_success(monkeypatch):
    def boom(*a, **k):
        raise llm.AIError(504, "timeout")
    monkeypatch.setattr(llm, "chat_json", boom)
    r = client.post("/api/freshness-detector/analyze", files=[img()])
    assert r.status_code == 504


def test_schema_mismatch_returns_502(monkeypatch):
    mock_llm(monkeypatch, {"daily_plan": "nonsense"})
    r = client.post("/api/meal-planner/generate", data=dict(age=30, gender="Male", height=175, weight=70, goals="Maintain"))
    assert r.status_code == 502


def test_freshness_normalises_level(monkeypatch):
    mock_llm(monkeypatch, {"item_name": "Banana", "freshness_level": "Fresh", "confidence": 80})
    r = client.post("/api/freshness-detector/analyze", files=[img()], data={"storage_time": "2 days"}).json()
    assert r["freshness_level"] == "Appears fresh" and "visual" in r["disclaimer"].lower()


def test_kitchen_needs_input_and_combines(monkeypatch):
    assert client.post("/api/kitchen-assistant/generate-recipe").status_code == 400
    seen = {}

    def fake(messages, *a, **k):
        seen["m"] = messages
        return {"dish_name": "Omelette", "ingredients": ["2 eggs"], "steps": ["Cook"]}
    monkeypatch.setattr(llm, "chat_json", fake)
    r = client.post("/api/kitchen-assistant/generate-recipe", data={"text_input": "eggs, onion"}, files=[img()])
    assert r.status_code == 200
    kinds = [p["type"] for p in seen["m"][1]["content"]]
    assert "image_url" in kinds and any("eggs, onion" in p.get("text", "") for p in seen["m"][1]["content"])


def test_hygiene_score_formula():
    V = hy.Violation
    assert hy.compute_score([], 1) == 100
    assert hy.compute_score([V(violation="a", severity="High"), V(violation="b", severity="Low")], 1) == 82
    assert hy.compute_score([V(violation="a", severity="High")] * 2, 2) == 85  # averaged across frames


def test_hygiene_requires_media():
    assert client.post("/api/hygiene-monitor/analyze").status_code == 400


def test_hygiene_image_and_report(monkeypatch):
    mock_llm(monkeypatch, {"violations": [{"violation": "Dirty floor", "severity": "medium", "location": "floor", "reason": "spill"}],
                           "ai_summary": "ok"})
    r = client.post("/api/hygiene-monitor/analyze", files=[img()])
    body = r.json()
    assert r.status_code == 200 and body["overall_score"] == 92 and body["violations"][0]["severity"] == "Medium"
    pdf = client.post("/api/hygiene-monitor/report", json={"result": body})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_video_frame_extraction(tmp_path):
    import cv2
    import numpy as np
    from services import media

    path = str(tmp_path / "t.mp4")
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 64))
    for i in range(30):
        out.write(np.full((64, 64, 3), i * 8, dtype=np.uint8))
    out.release()
    frames, meta = media.extract_video_frames(path, max_frames=4)
    assert len(frames) == 4 and meta["total_frames"] == 30


def test_video_endpoint_rejects_wrong_type():
    r = client.post("/api/hygiene-monitor/analyze", files=[("video", ("x.txt", b"hello", "text/plain"))])
    assert r.status_code == 415


def test_targets_safe_floor_and_goal():
    t = mp.compute_targets(30, "Female", 150, 45, "Sedentary", "Lose weight")
    assert t.target_calories >= 1200
    m = mp.compute_targets(30, "Male", 175, 70, "Moderate", "Maintain")
    assert m.bmr == 1649 and m.target_calories == m.tdee


def _meal(name, ing):
    return {"dish_name": name, "ingredients": ing, "calories": 400, "macros": {"protein_g": 20, "carbs_g": 40, "fats_g": 10}}


def _plan(ing):
    return {"daily_plan": {k: _meal(k, ing) for k in mp.MEALS} | {"hydration_target": "2 L"}}


def test_meal_plan_ok_and_totals(monkeypatch):
    mock_llm(monkeypatch, _plan(["oats", "milk"]))
    r = client.post("/api/meal-planner/generate", data=dict(age=30, gender="Male", height=175, weight=70, goals="Maintain",
                                                             medical_conditions="diabetes"))
    b = r.json()
    assert r.status_code == 200 and b["daily_totals"]["calories"] == 2000
    assert any("doctor" in w for w in b["warnings"])


def test_meal_plan_blocks_allergen(monkeypatch):
    mock_llm(monkeypatch, _plan(["peanut butter", "bread"]))
    r = client.post("/api/meal-planner/generate", data=dict(age=30, gender="Male", height=175, weight=70, goals="Maintain",
                                                             allergies="peanut"))
    assert r.status_code == 502


def test_meal_plan_validation():
    r = client.post("/api/meal-planner/generate", data=dict(age=5, gender="Male", height=175, weight=70, goals="x"))
    assert r.status_code == 422
