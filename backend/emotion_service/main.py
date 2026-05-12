"""
Module V — AI Emotion Detection Microservice
FastAPI service using DeepFace for facial emotion recognition.
Runs on port 8001.

Accuracy-oriented defaults:
  - Stronger face detectors (RetinaFace → MTCNN → OpenCV) with fallbacks
  - Gentle preprocessing (upscale small faces + light CLAHE) — avoids heavy
    histogram equalization that can distort expression cues
  - Optional dual-detector score fusion (EMOTION_ENSEMBLE=1)
  - Normalized emotion probabilities before mapping to app labels
"""
import io
import os
import sys
import traceback
import numpy as np
import cv2
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Windows consoles often use cp1252; emoji/log UTF-8 would crash without this.
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

app = FastAPI(title="RecoveryRoad Emotion Detection", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config (env overrides) -------------------------------------------------
DETECTOR_PRIMARY = os.environ.get("EMOTION_DETECTOR_PRIMARY", "retinaface").strip()
_raw_fallbacks = os.environ.get("EMOTION_DETECTOR_FALLBACKS", "mtcnn,opencv")
DETECTOR_FALLBACKS = [
    b.strip()
    for b in _raw_fallbacks.split(",")
    if b.strip() and b.strip() != DETECTOR_PRIMARY
]
EMOTION_ENSEMBLE = os.environ.get("EMOTION_ENSEMBLE", "0").lower() in ("1", "true", "yes")
MIN_FACE_EDGE = int(os.environ.get("EMOTION_MIN_UPSCALE_EDGE", "384"))

MODEL_VERSION = os.environ.get("EMOTION_MODEL_VERSION", "deepface-v3")

# Emotion mapping: DeepFace classes -> our 4 labels (for logging / future use)
EMOTION_MAP = {
    "happy": "happy",
    "neutral": "neutral",
    "sad": "sad",
    "sadness": "sad",
    "fear": "anxious",
    "angry": "anxious",
    "disgust": "anxious",
    "surprise": "neutral",
}

# Weighted scoring: aggregate ALL DeepFace class scores into our 4 labels
LABEL_WEIGHTS = {
    "happy": {"happy": 1.0},
    "sad": {"sad": 1.0, "sadness": 1.0},
    "anxious": {"fear": 1.0, "angry": 0.85, "disgust": 0.55},
    "neutral": {"neutral": 1.0, "surprise": 0.4},
}

# Eagerly load DeepFace on startup so first request doesn't timeout
print("⏳ Loading DeepFace model (first time may download ~100MB)...")
from deepface import DeepFace as _deepface

try:
    _dummy = np.zeros((224, 224, 3), dtype=np.uint8)
    _deepface.analyze(_dummy, actions=["emotion"], enforce_detection=False, silent=True)
    print("✅ DeepFace emotion model loaded and warmed up")
except Exception as e:
    print(f"⚠️ DeepFace warmup note: {e} (model will load on first request)")


def get_deepface():
    return _deepface


def get_image_sharpness(img):
    """Compute image sharpness score using Laplacian variance."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness = min(1.0, laplacian_var / 500.0)
    return float(sharpness)


def get_face_size_ratio(img, face_cascade):
    """Estimate what fraction of the image is covered by the largest frontal face."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) == 0:
        return 0.0
    largest_face = max(faces, key=lambda f: f[2] * f[3])
    face_area = largest_face[2] * largest_face[3]
    img_area = img.shape[0] * img.shape[1]
    ratio = face_area / img_area
    return float(min(1.0, ratio * 4))


def assess_lighting_quality(img):
    """Assess lighting quality using mean brightness."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    if 90 <= mean_brightness <= 170:
        lighting = 1.0 - abs(mean_brightness - 130) / 130.0
    else:
        lighting = max(0.0, 1.0 - abs(mean_brightness - 130) / 200.0)
    return float(lighting)


def gentle_preprocess(img):
    """
    Upscale small inputs so detectors see enough pixels; light CLAHE on luminance only.
    Avoids aggressive HSV equalization + denoise that can wash out micro-expressions.
    """
    h, w = img.shape[:2]
    m = min(h, w)
    out = img
    if m < MIN_FACE_EDGE and m > 0:
        scale = MIN_FACE_EDGE / float(m)
        nh, nw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
        out = cv2.resize(out, (nw, nh), interpolation=cv2.INTER_CUBIC)

    lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_ch = clahe.apply(l_ch)
    merged = cv2.merge([l_ch, a_ch, b_ch])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def normalize_emotion_scores(emotion_scores):
    """L1-normalize DeepFace emotion dict so weighting is scale-stable."""
    if not emotion_scores:
        return {}
    vals = np.array([max(0.0, float(v)) for v in emotion_scores.values()], dtype=np.float64)
    s = float(vals.sum())
    if s < 1e-9:
        n = max(1, len(emotion_scores))
        return {k: 1.0 / n for k in emotion_scores}
    keys = list(emotion_scores.keys())
    return {k: float(max(0.0, float(emotion_scores[k]))) / s for k in keys}


def merge_emotion_dicts(dicts):
    """Average overlapping keys from multiple DeepFace emotion dicts."""
    if not dicts:
        return {}
    keys = set()
    for d in dicts:
        keys |= set(d.keys())
    merged = {}
    for k in keys:
        vals = [float(d.get(k, 0.0)) for d in dicts]
        merged[k] = float(sum(vals) / max(1, len(vals)))
    return normalize_emotion_scores(merged)


def compute_mapped_emotion(emotion_scores):
    """
    Map normalized DeepFace scores -> our 4 labels + intensity.
    If top two labels are very close, damp confidence (ambiguous expression).
    """
    label_scores = {}
    for label, weight_map in LABEL_WEIGHTS.items():
        score = 0.0
        for raw_emotion, weight in weight_map.items():
            score += emotion_scores.get(raw_emotion, 0.0) * weight
        label_scores[label] = score

    best_label = max(label_scores, key=label_scores.get)
    best_score = label_scores[best_label]
    total = sum(label_scores.values())
    confidence = (best_score / total) if total > 0 else 0.25

    sorted_scores = sorted(label_scores.values(), reverse=True)
    gap = (sorted_scores[0] - sorted_scores[1]) / total if len(sorted_scores) > 1 and total > 0 else 0.5
    intensity_score = float(max(0.0, min(1.0, gap)))

    if gap < 0.10:
        confidence = min(confidence, 0.62)
        if best_label != "neutral" and label_scores.get("neutral", 0) / max(total, 1e-9) > 0.28:
            best_label = "neutral"
            best_score = label_scores["neutral"]
            confidence = max(0.48, min(0.62, best_score / max(total, 1e-9)))

    if intensity_score >= 0.7:
        intensity_level = "strong"
    elif intensity_score >= 0.4:
        intensity_level = "moderate"
    else:
        intensity_level = "mild"

    return best_label, confidence, label_scores, intensity_level, intensity_score


def _analyze_safe(DeepFace, img, detector_backend, enforce_detection):
    return DeepFace.analyze(
        img,
        actions=["emotion"],
        enforce_detection=enforce_detection,
        detector_backend=detector_backend,
        silent=True,
    )


def run_deepface_with_backends(DeepFace, img, backends, allow_no_face_fallback=True):
    """
    Try backends in order with enforce_detection=True; optionally one last
    enforce_detection=False on the last backend.
    Returns (emotion_scores dict, dominant str, detection_used str) or None.
    """
    last_err = None
    for backend in backends:
        try:
            results = _analyze_safe(DeepFace, img, backend, True)
            detection_used = backend
            break
        except Exception as e:
            last_err = e
            results = None
            detection_used = None
    else:
        results = None
        detection_used = None

    if results is None and allow_no_face_fallback and backends:
        backend = backends[-1]
        try:
            results = _analyze_safe(DeepFace, img, backend, False)
            detection_used = f"{backend}_noface"
        except Exception as e:
            last_err = e
            results = None

    if results is None:
        if last_err:
            print(f"⚠️ DeepFace all backends failed: {last_err}")
        return None

    result = results[0] if isinstance(results, list) else results
    raw_emotion = result.get("dominant_emotion", "neutral")
    emotion_scores = result.get("emotion") or {}
    emotion_scores = normalize_emotion_scores(emotion_scores)
    return emotion_scores, raw_emotion, detection_used


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "emotion-detection",
        "modelVersion": MODEL_VERSION,
        "detectorPrimary": DETECTOR_PRIMARY,
        "ensemble": EMOTION_ENSEMBLE,
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Accepts a single image (JPEG/PNG/WebP).
    Returns emotion label, confidence, intensity, and detailed quality metrics.
    """
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return JSONResponse(
                status_code=200,
                content={"ok": False, "error": "INVALID_IMAGE"},
            )

        original_height, original_width = img.shape[:2]
        sharpness = get_image_sharpness(img)
        lighting = assess_lighting_quality(img)

        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        face_size_ratio = get_face_size_ratio(img, face_cascade)

        img_proc = gentle_preprocess(img)

        DeepFace = get_deepface()
        chain = [DETECTOR_PRIMARY] + DETECTOR_FALLBACKS
        # de-dupe while preserving order
        seen = set()
        chain = [b for b in chain if not (b in seen or seen.add(b))]

        score_sets = []
        detection_used = "unknown"
        raw_emotion = "neutral"

        if EMOTION_ENSEMBLE and len(chain) >= 2:
            for backend in chain[:2]:
                out = run_deepface_with_backends(DeepFace, img_proc, [backend], allow_no_face_fallback=True)
                if out:
                    scores, dom, det = out
                    score_sets.append(scores)
                    raw_emotion = dom
                    detection_used = f"ensemble:{det}"
            if len(score_sets) >= 2:
                emotion_scores = merge_emotion_dicts(score_sets)
            elif len(score_sets) == 1:
                emotion_scores = score_sets[0]
            else:
                emotion_scores = None
        else:
            out = run_deepface_with_backends(DeepFace, img_proc, chain, allow_no_face_fallback=True)
            if out:
                emotion_scores, raw_emotion, detection_used = out
            else:
                emotion_scores = None

        if emotion_scores is None:
            return JSONResponse(
                status_code=200,
                content={"ok": False, "error": "NO_FACE_DETECTED"},
            )

        mapped_emotion, confidence, label_scores, intensity_level, intensity_score = compute_mapped_emotion(
            emotion_scores
        )

        quality_score = (sharpness + lighting + min(1.0, face_size_ratio * 1.5)) / 3.0
        quality_factor = 0.82 + (quality_score * 0.18)
        if face_size_ratio < 0.07:
            quality_factor *= 0.92
        adjusted_confidence = min(0.99, max(0.45, confidence * quality_factor))

        print(
            f"🔍 Emotion: {mapped_emotion} | conf {confidence:.3f}→{adjusted_confidence:.3f} | "
            f"raw={raw_emotion} | det={detection_used} | Q={quality_score:.2f}"
        )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "emotion": mapped_emotion,
                "confidence": float(round(adjusted_confidence, 3)),
                "intensity": {
                    "level": intensity_level,
                    "score": float(round(intensity_score, 3)),
                },
                "quality": {
                    "overallScore": float(round(quality_score, 3)),
                    "sharpness": float(round(sharpness, 3)),
                    "lighting": float(round(lighting, 3)),
                    "faceSize": float(round(face_size_ratio, 3)),
                },
                "raw": {
                    "dominant_emotion": raw_emotion,
                    "scores": {k: float(round(v, 4)) for k, v in emotion_scores.items()},
                    "mapped_scores": {k: float(round(v, 4)) for k, v in label_scores.items()},
                    "detection": detection_used,
                },
                "modelVersion": MODEL_VERSION,
                "imageResolution": [original_width, original_height],
            },
        )

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": "INFERENCE_FAILED", "detail": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    print("🧠 Starting Emotion Detection Service on port 8001...")
    get_deepface()
    uvicorn.run(app, host="0.0.0.0", port=8001)
