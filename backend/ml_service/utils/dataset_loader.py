"""Dataset loading and lightweight augmentation for Recovery Road ML."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .text_normalization import make_casual_variant, make_noisy_variant, make_roman_urdu_variant, normalize_text

DATASET_ROOT = Path(__file__).resolve().parents[1] / "datasets"
FEATURE_ORDER = ["avgCraving", "maxCraving", "avgMood", "moodDecline", "triggers", "activity", "missed", "relapses"]


def _load_json_records(category: str, split: str) -> list[dict[str, Any]]:
    file_path = DATASET_ROOT / category / f"{split}.json"
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, list) else []


def _clamp01(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _dedupe(records: Iterable[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for record in records:
        key = key_fn(record)
        if key in seen:
            continue
        seen.add(key)
        output.append(record)
    return output


def _normalize_text_record(record: dict[str, Any], index: int, split: str) -> dict[str, Any]:
    normalized = dict(record)
    normalized["text"] = normalize_text(str(record.get("text", "")))
    normalized["originalText"] = record.get("text", "")
    normalized["split"] = split
    normalized["source"] = record.get("source", f"{split}:{index}")
    return normalized


def _normalize_risk_record(record: dict[str, Any], index: int, split: str) -> dict[str, Any]:
    features = record.get("features") or record
    normalized = {
        "avgCraving": _clamp01(features.get("avgCraving")),
        "maxCraving": _clamp01(features.get("maxCraving")),
        "avgMood": _clamp01(features.get("avgMood")),
        "moodDecline": _clamp01(features.get("moodDecline")),
        "triggers": _clamp01(features.get("triggers")),
        "activity": _clamp01(features.get("activity")),
        "missed": _clamp01(features.get("missed")),
        "relapses": _clamp01(features.get("relapses")),
    }
    out = dict(record)
    out["features"] = normalized
    out["split"] = split
    out["source"] = record.get("source", f"{split}:{index}")
    return out


def _augment_text_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    variants = [
        {**record, "text": record["text"], "variant": "normalized"},
        {**record, "text": make_casual_variant(record["text"]), "variant": "casual-slang"},
        {**record, "text": make_noisy_variant(record["text"]), "variant": "noisy"},
    ]
    roman_variant = make_roman_urdu_variant(record["text"])
    if roman_variant != record["text"]:
        variants.append({**record, "text": roman_variant, "variant": "roman-urdu"})
    return variants


def _augment_risk_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    shifts = [
        {"name": "normalized", "avgCraving": 0.0, "maxCraving": 0.0, "avgMood": 0.0, "moodDecline": 0.0, "triggers": 0.0, "activity": 0.0, "missed": 0.0, "relapses": 0.0},
        {"name": "slight-up", "avgCraving": 0.03, "maxCraving": 0.03, "avgMood": -0.02, "moodDecline": 0.03, "triggers": 0.02, "activity": -0.02, "missed": 0.02, "relapses": 0.02},
        {"name": "slight-down", "avgCraving": -0.03, "maxCraving": -0.02, "avgMood": 0.02, "moodDecline": -0.02, "triggers": -0.02, "activity": 0.02, "missed": -0.02, "relapses": -0.02},
    ]

    augmented: list[dict[str, Any]] = []
    for shift in shifts:
        features = record["features"]
        augmented.append(
            {
                **record,
                "features": {
                    "avgCraving": _clamp01(features["avgCraving"] + shift["avgCraving"]),
                    "maxCraving": _clamp01(features["maxCraving"] + shift["maxCraving"]),
                    "avgMood": _clamp01(features["avgMood"] + shift["avgMood"]),
                    "moodDecline": _clamp01(features["moodDecline"] + shift["moodDecline"]),
                    "triggers": _clamp01(features["triggers"] + shift["triggers"]),
                    "activity": _clamp01(features["activity"] + shift["activity"]),
                    "missed": _clamp01(features["missed"] + shift["missed"]),
                    "relapses": _clamp01(features["relapses"] + shift["relapses"]),
                },
                "variant": shift["name"],
            }
        )
    return augmented


def _augment_text_record_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    augmented = (variant for record in records for variant in _augment_text_record(record))
    return _dedupe(augmented, lambda item: f"{item.get('risk', '')}|{item.get('emotion', '')}|{item['text']}")


def _augment_risk_record_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    augmented = (variant for record in records for variant in _augment_risk_record(record))
    return _dedupe(augmented, lambda item: f"{item.get('label', '')}|{json.dumps(item['features'], sort_keys=True)}")


def load_text_dataset() -> dict[str, list[dict[str, Any]]]:
    train = [_normalize_text_record(item, idx, "train") for idx, item in enumerate(_load_json_records("text", "train"))]
    validation = [_normalize_text_record(item, idx, "validation") for idx, item in enumerate(_load_json_records("text", "validation"))]
    test = [_normalize_text_record(item, idx, "test") for idx, item in enumerate(_load_json_records("text", "test"))]
    all_records = train + validation + test
    return {"train": _augment_text_record_batch(train), "validation": validation, "test": test, "all": _augment_text_record_batch(all_records)}


def load_emotion_dataset() -> dict[str, list[dict[str, Any]]]:
    train = [_normalize_text_record(item, idx, "train") for idx, item in enumerate(_load_json_records("emotions", "train"))]
    validation = [_normalize_text_record(item, idx, "validation") for idx, item in enumerate(_load_json_records("emotions", "validation"))]
    test = [_normalize_text_record(item, idx, "test") for idx, item in enumerate(_load_json_records("emotions", "test"))]
    all_records = train + validation + test
    return {"train": _augment_text_record_batch(train), "validation": validation, "test": test, "all": _augment_text_record_batch(all_records)}


def load_risk_dataset() -> dict[str, list[dict[str, Any]]]:
    train = [_normalize_risk_record(item, idx, "train") for idx, item in enumerate(_load_json_records("risk", "train"))]
    validation = [_normalize_risk_record(item, idx, "validation") for idx, item in enumerate(_load_json_records("risk", "validation"))]
    test = [_normalize_risk_record(item, idx, "test") for idx, item in enumerate(_load_json_records("risk", "test"))]
    all_records = train + validation + test
    return {"train": _augment_risk_record_batch(train), "validation": validation, "test": test, "all": _augment_risk_record_batch(all_records)}


def to_text_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    return frame[["text", "risk", "emotion"]].copy() if not frame.empty else pd.DataFrame(columns=["text", "risk", "emotion"])


def to_risk_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        return pd.DataFrame(columns=[*FEATURE_ORDER, "label"])
    features = pd.json_normalize(frame["features"])
    features["label"] = frame["label"].values
    return features[[*FEATURE_ORDER, "label"]].copy()


def class_distribution(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values))


def dataset_summary(records: list[dict[str, Any]], label_key: str = "risk") -> dict[str, Any]:
    if not records:
        return {"count": 0, "distribution": {}}
    values = [record.get(label_key, "unknown") if label_key != "label" else record["label"] for record in records]
    lengths = [len(str(record.get("text", ""))) for record in records if record.get("text")]
    return {
        "count": len(records),
        "distribution": class_distribution(values),
        "avgTextLength": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "minTextLength": min(lengths) if lengths else 0,
        "maxTextLength": max(lengths) if lengths else 0,
    }
