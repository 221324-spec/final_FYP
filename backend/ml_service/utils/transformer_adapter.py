"""Optional lightweight transformer-based comparator."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Any


def _enabled() -> bool:
    return str(os.environ.get("ENABLE_TRANSFORMER", "0")).lower() in {"1", "true", "yes", "on"}


class TransformerComparator:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.environ.get("TRANSFORMER_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        self._model = None
        self._risk_centroids: dict[str, Any] = {}
        self._emotion_centroids: dict[str, Any] = {}
        self._available = False

    def available(self) -> bool:
        return self._available

    def load(self) -> bool:
        if not _enabled():
            return False
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._available = True
            return True
        except Exception:
            self._available = False
            self._model = None
            return False

    def fit(self, records: list[dict[str, Any]]) -> None:
        if not self._available or not self._model:
            return

        labels_risk = defaultdict(list)
        labels_emotion = defaultdict(list)
        for record in records:
            text = record.get("text")
            if not text:
                continue
            if record.get("risk"):
                labels_risk[record["risk"]].append(text)
            if record.get("emotion"):
                labels_emotion[record["emotion"]].append(text)

        for label, samples in labels_risk.items():
            embeddings = self._model.encode(samples, normalize_embeddings=True)
            self._risk_centroids[label] = embeddings.mean(axis=0)

        for label, samples in labels_emotion.items():
            embeddings = self._model.encode(samples, normalize_embeddings=True)
            self._emotion_centroids[label] = embeddings.mean(axis=0)

    def predict(self, text: str) -> dict[str, Any] | None:
        if not self._available or not self._model or not text:
            return None

        start = time.perf_counter()
        embedding = self._model.encode([text], normalize_embeddings=True)[0]
        risk = self._nearest(self._risk_centroids, embedding)
        emotion = self._nearest(self._emotion_centroids, embedding)
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        return {"risk": risk[0], "riskScore": round(risk[1], 4), "emotion": emotion[0], "emotionScore": round(emotion[1], 4), "latencyMs": latency_ms, "model": self.model_name}

    def benchmark(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        if not self._available or not self._model:
            return {"enabled": False, "available": False}

        risk_correct = 0
        emotion_correct = 0
        latencies = []
        total = 0
        for record in records:
            text = record.get("text")
            if not text:
                continue
            total += 1
            start = time.perf_counter()
            prediction = self.predict(text)
            latencies.append((time.perf_counter() - start) * 1000.0)
            if prediction and prediction["risk"] == record.get("risk"):
                risk_correct += 1
            if prediction and prediction["emotion"] == record.get("emotion"):
                emotion_correct += 1

        return {"enabled": True, "available": True, "samples": total, "riskAccuracy": round(risk_correct / total, 4) if total else 0.0, "emotionAccuracy": round(emotion_correct / total, 4) if total else 0.0, "avgLatencyMs": round(sum(latencies) / len(latencies), 2) if latencies else 0.0}

    @staticmethod
    def _nearest(centroids: dict[str, Any], embedding):
        if not centroids:
            return ("neutral", 0.0)
        best_label = None
        best_score = -1.0
        for label, centroid in centroids.items():
            score = float((embedding @ centroid) / ((embedding @ embedding) ** 0.5 * (centroid @ centroid) ** 0.5 + 1e-12))
            if score > best_score:
                best_label = label
                best_score = score
        return best_label or "neutral", best_score
