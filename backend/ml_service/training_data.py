"""Compatibility wrappers around the modular dataset loader."""

from __future__ import annotations

from typing import Any

import pandas as pd

from utils.dataset_loader import load_emotion_dataset, load_risk_dataset, load_text_dataset, to_risk_dataframe, to_text_dataframe


_TEXT_DATASET = load_text_dataset()
_EMOTION_DATASET = load_emotion_dataset()
_RISK_DATASET = load_risk_dataset()

TEXT_TRAINING_DATA = _TEXT_DATASET["all"]
TEXT_TRAIN_DATA = _TEXT_DATASET["train"]
TEXT_VALIDATION_DATA = _TEXT_DATASET["validation"]
TEXT_TEST_DATA = _TEXT_DATASET["test"]

EMOTION_TRAINING_DATA = _EMOTION_DATASET["all"]
EMOTION_TRAIN_DATA = _EMOTION_DATASET["train"]
EMOTION_VALIDATION_DATA = _EMOTION_DATASET["validation"]
EMOTION_TEST_DATA = _EMOTION_DATASET["test"]

RISK_FEATURE_DATA = _RISK_DATASET["all"]
RISK_TRAIN_DATA = _RISK_DATASET["train"]
RISK_VALIDATION_DATA = _RISK_DATASET["validation"]
RISK_TEST_DATA = _RISK_DATASET["test"]


def get_text_records(split: str = "all") -> list[dict[str, Any]]:
    return list(_TEXT_DATASET.get(split, _TEXT_DATASET["all"]))


def get_emotion_records(split: str = "all") -> list[dict[str, Any]]:
    return list(_EMOTION_DATASET.get(split, _EMOTION_DATASET["all"]))


def get_risk_records(split: str = "all") -> list[dict[str, Any]]:
    return list(_RISK_DATASET.get(split, _RISK_DATASET["all"]))


def get_text_dataframe(split: str = "all") -> pd.DataFrame:
    return to_text_dataframe(get_text_records(split))


def get_risk_dataframe(split: str = "all") -> pd.DataFrame:
    return to_risk_dataframe(get_risk_records(split))

