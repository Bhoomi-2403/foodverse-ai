"""Upload validation, image preprocessing, video frame extraction and audio transcription."""
import base64
import io
import logging
import os
import tempfile
from contextlib import contextmanager
from typing import Optional

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

import config
from services.llm import AIError

logger = logging.getLogger("foodverse.media")

IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac", ".aac"}


async def read_limited(upload: UploadFile, limit: int, label: str) -> bytes:
    """Read an upload fully but reject it as soon as it exceeds the limit."""
    chunks, size = [], 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise AIError(413, f"The {label} is too large (limit {limit // (1024 * 1024)} MB).")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise AIError(400, f"The {label} is empty.")
    return data


def prepare_image(data: bytes, max_side: int = 1280) -> tuple[str, str]:
    """Validate by decoding, resize, and return (base64, mime). Never trusts the extension."""
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in IMAGE_FORMATS:
            raise AIError(415, "Unsupported image type. Use JPEG, PNG or WebP.")
        img = Image.open(io.BytesIO(data))
        img.load()
    except AIError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise AIError(400, "The file is not a valid or readable image.")
    if img.width < 32 or img.height < 32:
        raise AIError(400, "The image is too small to analyse (minimum 32x32 pixels).")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
    if img.mode not in ("RGB",):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode("ascii"), "image/jpeg"


async def load_image_upload(upload: UploadFile) -> tuple[str, str]:
    data = await read_limited(upload, config.max_upload_bytes(), "image")
    return prepare_image(data)


@contextmanager
def temp_file(data: bytes, suffix: str):
    """Write bytes to a uniquely named temp file and always delete it afterwards."""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="fv_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        yield path
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _ext(upload: UploadFile) -> str:
    return os.path.splitext(upload.filename or "")[1].lower()


def frame_to_b64(frame, max_side: int = 960) -> str:
    import cv2

    h, w = frame.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise AIError(400, "Could not encode a video frame.")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def extract_video_frames(path: str, max_frames: Optional[int] = None) -> tuple[list[tuple[float, str]], dict]:
    """Return ([(timestamp_seconds, b64_jpeg)], metadata). Releases the capture in all cases."""
    import cv2

    max_frames = max_frames or config.max_video_frames()
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise AIError(400, "The video could not be opened. Try MP4 (H.264).")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total <= 0:
            raise AIError(400, "The video contains no readable frames.")
        duration = total / fps if fps > 0 else 0.0
        n = min(max_frames, total)
        indices = sorted({int(total * (i + 0.5) / n) for i in range(n)})
        frames: list[tuple[float, str]] = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            ts = round(idx / fps, 1) if fps > 0 else float(idx)
            frames.append((ts, frame_to_b64(frame)))
        if not frames:
            raise AIError(400, "No frames could be read from the video.")
        meta = {"duration_seconds": round(duration, 1), "fps": round(fps, 1), "total_frames": total,
                "frames_sampled": len(frames)}
        return frames, meta
    finally:
        cap.release()


async def load_video_upload(upload: UploadFile):
    if _ext(upload) not in VIDEO_EXTS and not (upload.content_type or "").startswith("video/"):
        raise AIError(415, "Unsupported video type. Use MP4, MOV, AVI, MKV or WebM.")
    return await read_limited(upload, config.max_video_bytes(), "video"), (_ext(upload) or ".mp4")


def transcribe_audio(data: bytes, suffix: str) -> tuple[str, Optional[str]]:
    """Returns (text, warning). Never raises; warning explains why audio was ignored."""
    if suffix not in AUDIO_EXTS:
        return "", "Audio format not supported; the voice note was ignored."
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
    except ImportError:
        return "", "Audio libraries are not installed; the voice note was ignored."
    try:
        with temp_file(data, suffix) as src:
            wav_fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="fv_")
            os.close(wav_fd)
            try:
                AudioSegment.from_file(src).set_channels(1).set_frame_rate(16000).export(wav_path, format="wav")
                rec = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio = rec.record(source)
                text = rec.recognize_google(audio)
                return text, None
            finally:
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
    except Exception as exc:  # noqa: BLE001 - audio is optional; report instead of failing
        logger.warning("Audio transcription failed: %s", type(exc).__name__)
        return "", "The voice note could not be transcribed (ffmpeg or network may be missing); it was ignored."


async def audio_note(upload: Optional[UploadFile]) -> tuple[str, Optional[str]]:
    if upload is None or not upload.filename:
        return "", None
    data = await read_limited(upload, config.max_upload_bytes(), "audio file")
    return transcribe_audio(data, _ext(upload))
