"""Evaluation helpers for the Recovery Road ML service."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support


def class_distribution(values: Iterable[str]) -> dict[str, int]:
    return dict(Counter(values))


def evaluate_predictions(y_true, y_pred, labels: list[str]) -> dict[str, Any]:
    y_true = list(y_true)
    y_pred = list(y_pred)
    accuracy = float(np.mean(np.array(y_true) == np.array(y_pred))) if y_true else 0.0
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="weighted", zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)

    false_positive_counts = {}
    false_negative_counts = {}
    for idx, label in enumerate(labels):
        fp = int(cm[:, idx].sum() - cm[idx, idx])
        fn = int(cm[idx, :].sum() - cm[idx, idx])
        false_positive_counts[label] = fp
        false_negative_counts[label] = fn

    return {
        "accuracy": round(accuracy, 4),
        "precisionMacro": round(float(precision_macro), 4),
        "recallMacro": round(float(recall_macro), 4),
        "f1Macro": round(float(f1_macro), 4),
        "precisionWeighted": round(float(precision_weighted), 4),
        "recallWeighted": round(float(recall_weighted), 4),
        "f1Weighted": round(float(f1_weighted), 4),
        "confusionMatrix": cm.tolist(),
        "classificationReport": report,
        "falsePositives": false_positive_counts,
        "falseNegatives": false_negative_counts,
        "classDistribution": class_distribution(y_true),
    }


def evaluate_binary_positive_class(y_true, y_pred, positive_label: str = "HIGH") -> dict[str, Any]:
    y_true = [1 if value == positive_label else 0 for value in y_true]
    y_pred = [1 if value == positive_label else 0 for value in y_pred]
    tp = int(sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 1))
    fp = int(sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 1))
    fn = int(sum(1 for truth, pred in zip(y_true, y_pred) if truth == 1 and pred == 0))
    tn = int(sum(1 for truth, pred in zip(y_true, y_pred) if truth == 0 and pred == 0))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {"positiveLabel": positive_label, "tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
