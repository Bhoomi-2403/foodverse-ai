import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from routers import food_recognition, freshness_detector, hygiene_monitor, kitchen_assistant, meal_planner
from services.llm import AIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("foodverse")

app = FastAPI(title="FoodVerse AI", description="Multimodal AI Platform for Food Analysis", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AIError)
async def ai_error_handler(_: Request, exc: AIError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    logger.exception("Unhandled error: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Please try again."})


@app.get("/")
def read_root():
    return {"message": "Welcome to FoodVerse AI API", "status": "active", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ai_configured": bool(config.groq_api_key()),
        "vision_model": config.vision_models()[0],
    }


for module in (food_recognition, freshness_detector, hygiene_monitor, kitchen_assistant, meal_planner):
    app.include_router(module.router)
