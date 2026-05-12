"""ML models for Recovery Road.

This module keeps the existing Flask API stable while improving preprocessing,
dataset handling, evaluation, and confidence reliability.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

from utils.dataset_loader import (
    FEATURE_ORDER,
    dataset_summary,
    load_emotion_dataset,
    load_risk_dataset,
    load_text_dataset,
)
from utils.evaluation import evaluate_binary_positive_class, evaluate_predictions
from utils.text_normalization import normalize_text
from utils.transformer_adapter import TransformerComparator

try:
    from xgboost import XGBClassifier  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    LGBMClassifier = None

MODELS_DIR = Path(__file__).resolve().parent / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TEXT_RISK_MODEL_PATH = MODELS_DIR / 'text_risk_classifier.joblib'
EMOTION_MODEL_PATH = MODELS_DIR / 'emotion_classifier.joblib'
RISK_FEATURE_MODEL_PATH = MODELS_DIR / 'risk_feature_classifier.joblib'
META_PATH = MODELS_DIR / 'model_meta.json'

HIGH_RISK_REGEX = [
    re.compile(r'\b(kill\s*(my)?self|sui[cs]ide|suicidal)\b', re.I),
    re.compile(r'\b(want\s+to\s+die|wanna\s+die|rather\s+be\s+dead)\b', re.I),
    re.compile(r'\b(end\s+(my\s+)?life|end\s+it\s+all)\b', re.I),
    re.compile(r'\b(self[- ]?harm|cut(ting)?\s*(my)?self|hurt(ing)?\s*(my)?self)\b', re.I),
    re.compile(r'\b(overdos(e|ed|ing)|took?\s+too\s+many\s+(pills|tablets|meds))\b', re.I),
    re.compile(r'\b(going\s+to\s+jump|jump\s+off)\b', re.I),
    re.compile(r'\b(no\s+reason\s+to\s+live|nothing\s+to\s+live\s+for)\b', re.I),
    re.compile(r'\b(plan\s+to\s+(die|end))\b', re.I),
    re.compile(r'\b(goodbye\s*(forever|world|everyone))\b', re.I),
    re.compile(r"\b(can'?t\s+go\s+on|can'?t\s+take\s+(it|this)\s+any\s*more)\b", re.I),
    re.compile(r"\b(i'?m\s+going\s+to\s+do\s+it)\b", re.I),
    re.compile(r'\b(slit\s+(my\s+)?wrist|hang(ing)?\s*(my)?self)\b', re.I),
]

MED_RISK_KEYWORDS = [
    'relapse', 'relapsed', 'relapsing', 'craving', 'cravings',
    "can't cope", 'cannot cope', 'panic attack', 'panicking',
    'using again', 'used again', 'want to use', 'falling apart',
    'breaking down', 'desperate', 'unbearable', 'spiraling',
    'out of control', 'give up', 'giving up', 'drinking again',
    'smoking again', 'tempted', 'temptation',
]

EMOTION_KEYWORDS = {
    'anxiety': ['panic', 'panicking', 'anxious', 'anxiety', 'scared', 'shaky', "can't breathe", 'nervous', 'worried', 'terrified', 'fear', 'restless', 'on edge', 'heart racing', 'trembling', 'ghabrahat', 'bechain'],
    'sadness': ['hopeless', 'depressed', 'depression', 'empty', 'crying', 'tears', 'lonely', 'alone', 'miserable', 'worthless', 'numb', 'broken', 'grief', 'loss', 'sad', 'devastated', 'udas'],
    'anger': ['angry', 'furious', 'rage', 'hate', 'pissed', 'frustrated', 'irritated', 'enraged', 'livid', 'resentment', 'bitter'],
    'hope': ['proud', 'improving', 'better', 'progress', 'grateful', 'clean', 'sober', 'streak', 'milestone', 'accomplished', 'optimistic', 'hopeful', 'stronger', 'recovered', 'healing', 'positive', 'motivated', 'moving forward', 'umeed'],
}

_text_risk_model = None
_emotion_model = None
_risk_feature_model = None
_model_meta: dict[str, Any] = {}
_decision_thresholds = {'riskHigh': 0.7, 'riskUncertain': 0.5, 'emotionUncertain': 0.45}
_runtime_stats = {'trainMs': 0.0, 'inferCount': 0, 'avgInferMs': 0.0}
_transformer = TransformerComparator()


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _make_text_pipeline() -> Pipeline:
    return Pipeline([
        (
            'tfidf',
            TfidfVectorizer(
                preprocessor=normalize_text,
                lowercase=False,
                ngram_range=(1, 2),
                max_features=3500,
                min_df=1,
                sublinear_tf=True,
                token_pattern=r'(?u)\b\w+\b',
            ),
        ),
        (
            'clf',
            LogisticRegression(
                max_iter=3000,
                class_weight='balanced',
                multi_class='auto',
                solver='lbfgs',
                random_state=42,
            ),
        ),
    ])


def _make_risk_model():
    if LGBMClassifier is not None:
        return LGBMClassifier(
            n_estimators=200,
            learning_rate=0.08,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
    if XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric='mlogloss',
            random_state=42,
        )
    return GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        min_samples_split=3,
        min_samples_leaf=2,
        random_state=42,
    )


def _as_frame(records: list[dict[str, Any]], kind: str):
    import pandas as pd

    if kind == 'text':
        rows = [{
            'text': item.get('text', ''),
            'risk': item.get('risk', 'LOW'),
            'emotion': item.get('emotion', 'neutral'),
        } for item in records]
        return pd.DataFrame(rows)

    if kind == 'risk':
        rows = [{**item.get('features', {}), 'label': item.get('label', 'LOW')} for item in records]
        return pd.DataFrame(rows, columns=[*FEATURE_ORDER, 'label'])

    raise ValueError(f'Unsupported kind: {kind}')


def _extract_top_text_reasons(model: Pipeline, text: str, top_n: int = 5) -> list[str]:
    try:
        vectorizer = model.named_steps['tfidf']
        classifier = model.named_steps['clf']
        if not hasattr(classifier, 'coef_') or not hasattr(classifier, 'predict_proba'):
            return []
        X = vectorizer.transform([normalize_text(text)])
        feature_names = vectorizer.get_feature_names_out()
        class_index = int(np.argmax(classifier.predict_proba(X)[0]))
        coef = classifier.coef_[class_index] if getattr(classifier.coef_, 'ndim', 1) > 1 else classifier.coef_
        x = X.toarray()[0]
        contributions = [(feature_names[idx], x[idx] * coef[idx]) for idx in np.where(x > 0)[0]]
        contributions.sort(key=lambda item: abs(item[1]), reverse=True)
        return [f'{term}:{score:.3f}' for term, score in contributions[:top_n]]
    except Exception:
        return []


def _high_risk_rule(text: str) -> tuple[bool, str | None]:
    for pattern in HIGH_RISK_REGEX:
        match = pattern.search(text)
        if match:
            return True, match.group(0)
    return False, None


def _merge_runtime_latency(sample_ms: float) -> None:
    _runtime_stats['inferCount'] += 1
    count = _runtime_stats['inferCount']
    current = _runtime_stats['avgInferMs']
    _runtime_stats['avgInferMs'] = round(current + ((sample_ms - current) / count), 3)


def _choose_risk_from_probabilities(proba: np.ndarray, classes: list[str], rule_high: bool) -> tuple[str, float, dict[str, float], bool, list[str]]:
    probabilities = {label: round(float(prob), 4) for label, prob in zip(classes, proba)}
    sorted_items = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    top_label, top_prob = sorted_items[0]
    second_prob = sorted_items[1][1] if len(sorted_items) > 1 else 0.0
    uncertain = (top_prob < _decision_thresholds['riskUncertain']) or ((top_prob - second_prob) < 0.12)
    reasons: list[str] = []

    if rule_high:
        return 'HIGH', max(top_prob, 0.95), probabilities, False, ['Safety rule matched: explicit high-risk language']

    if top_label == 'HIGH' and top_prob < _decision_thresholds['riskHigh']:
        fallback_label = 'MED' if probabilities.get('MED', 0.0) >= probabilities.get('LOW', 0.0) else 'LOW'
        reasons.append(f'High-risk probability below threshold ({top_prob:.2f} < {_decision_thresholds["riskHigh"]:.2f}); downgraded to {fallback_label}')
        top_label = fallback_label
        top_prob = probabilities.get(fallback_label, top_prob)

    if uncertain:
        reasons.append('Low confidence / small margin; marked uncertain')

    return top_label, top_prob, probabilities, uncertain, reasons


def _choose_emotion_from_probabilities(proba: np.ndarray, classes: list[str]) -> tuple[str, float, dict[str, float], bool]:
    probabilities = {label: round(float(prob), 4) for label, prob in zip(classes, proba)}
    sorted_items = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    top_label, top_prob = sorted_items[0]
    second_prob = sorted_items[1][1] if len(sorted_items) > 1 else 0.0
    uncertain = (top_prob < _decision_thresholds['emotionUncertain']) or ((top_prob - second_prob) < 0.1)
    if uncertain and top_label != 'neutral':
        top_label = 'neutral'
    return top_label, top_prob, probabilities, uncertain


def _threshold_search_high_risk(model: Pipeline, validation_frame) -> dict[str, Any]:
    if validation_frame.empty:
        return {'highThreshold': _decision_thresholds['riskHigh'], 'uncertaintyThreshold': _decision_thresholds['riskUncertain']}
    proba = model.predict_proba(validation_frame['text'].values)
    classes = list(model.classes_)
    high_idx = classes.index('HIGH') if 'HIGH' in classes else 0
    y_true = validation_frame['risk'].values
    best_threshold = _decision_thresholds['riskHigh']
    best_f1 = -1.0
    for threshold in np.linspace(0.35, 0.9, 12):
        predictions = []
        for row in proba:
            label = classes[int(np.argmax(row))]
            high_prob = float(row[high_idx])
            if label == 'HIGH' and high_prob < threshold:
                label = 'MED' if row[classes.index('MED')] >= row[classes.index('LOW')] else 'LOW'
            predictions.append(label)
        binary = evaluate_binary_positive_class(y_true, predictions, positive_label='HIGH')
        if binary['f1'] > best_f1:
            best_f1 = binary['f1']
            best_threshold = float(threshold)
    return {'highThreshold': round(best_threshold, 3), 'uncertaintyThreshold': 0.5, 'bestHighF1': best_f1}


def _write_meta() -> None:
    with META_PATH.open('w', encoding='utf-8') as handle:
        json.dump(_model_meta, handle, indent=2, ensure_ascii=False)


def train_all() -> dict[str, Any]:
    global _text_risk_model, _emotion_model, _risk_feature_model, _model_meta, _decision_thresholds, _runtime_stats

    start_time = time.perf_counter()
    print('=' * 60)
    print('  Recovery Road — Python ML Model Training')
    print('=' * 60)

    text_ds = load_text_dataset()
    emotion_ds = load_emotion_dataset()
    risk_ds = load_risk_dataset()

    text_train = _as_frame(text_ds['train'], 'text')
    text_validation = _as_frame(text_ds['validation'], 'text')
    text_test = _as_frame(text_ds['test'], 'text')

    emotion_train = _as_frame(emotion_ds['train'], 'text')
    emotion_validation = _as_frame(emotion_ds['validation'], 'text')
    emotion_test = _as_frame(emotion_ds['test'], 'text')

    risk_train = _as_frame(risk_ds['train'], 'risk')
    risk_validation = _as_frame(risk_ds['validation'], 'risk')
    risk_test = _as_frame(risk_ds['test'], 'risk')

    _text_risk_model = _make_text_pipeline()
    _text_risk_model.fit(text_train['text'].values, text_train['risk'].values)

    text_train_pred = _text_risk_model.predict(text_train['text'].values)
    text_val_pred = _text_risk_model.predict(text_validation['text'].values) if not text_validation.empty else []
    text_test_pred = _text_risk_model.predict(text_test['text'].values) if not text_test.empty else []

    text_risk_eval = {
        'train': evaluate_predictions(text_train['risk'].values, text_train_pred, labels=['HIGH', 'MED', 'LOW']),
        'validation': evaluate_predictions(text_validation['risk'].values, text_val_pred, labels=['HIGH', 'MED', 'LOW']) if not text_validation.empty else {'accuracy': 0.0},
        'test': evaluate_predictions(text_test['risk'].values, text_test_pred, labels=['HIGH', 'MED', 'LOW']) if not text_test.empty else {'accuracy': 0.0},
    }

    _emotion_model = _make_text_pipeline()
    _emotion_model.fit(emotion_train['text'].values, emotion_train['emotion'].values)

    emotion_train_pred = _emotion_model.predict(emotion_train['text'].values)
    emotion_val_pred = _emotion_model.predict(emotion_validation['text'].values) if not emotion_validation.empty else []
    emotion_test_pred = _emotion_model.predict(emotion_test['text'].values) if not emotion_test.empty else []

    emotion_eval = {
        'train': evaluate_predictions(emotion_train['emotion'].values, emotion_train_pred, labels=['anxiety', 'sadness', 'anger', 'hope', 'neutral']),
        'validation': evaluate_predictions(emotion_validation['emotion'].values, emotion_val_pred, labels=['anxiety', 'sadness', 'anger', 'hope', 'neutral']) if not emotion_validation.empty else {'accuracy': 0.0},
        'test': evaluate_predictions(emotion_test['emotion'].values, emotion_test_pred, labels=['anxiety', 'sadness', 'anger', 'hope', 'neutral']) if not emotion_test.empty else {'accuracy': 0.0},
    }

    _risk_feature_model = _make_risk_model()
    _risk_feature_model.fit(risk_train[FEATURE_ORDER].values, risk_train['label'].values)

    risk_train_pred = _risk_feature_model.predict(risk_train[FEATURE_ORDER].values)
    risk_val_pred = _risk_feature_model.predict(risk_validation[FEATURE_ORDER].values) if not risk_validation.empty else []
    risk_test_pred = _risk_feature_model.predict(risk_test[FEATURE_ORDER].values) if not risk_test.empty else []

    risk_eval = {
        'train': evaluate_predictions(risk_train['label'].values, risk_train_pred, labels=['HIGH', 'MED', 'LOW']),
        'validation': evaluate_predictions(risk_validation['label'].values, risk_val_pred, labels=['HIGH', 'MED', 'LOW']) if not risk_validation.empty else {'accuracy': 0.0},
        'test': evaluate_predictions(risk_test['label'].values, risk_test_pred, labels=['HIGH', 'MED', 'LOW']) if not risk_test.empty else {'accuracy': 0.0},
    }

    _decision_thresholds = _threshold_search_high_risk(_text_risk_model, text_validation)

    if _transformer.load():
        _transformer.fit(text_train.to_dict('records') + emotion_train.to_dict('records'))
        transformer_benchmark = _transformer.benchmark(text_validation.to_dict('records') + emotion_validation.to_dict('records'))
    else:
        transformer_benchmark = {'enabled': False, 'available': False}

    joblib.dump(_text_risk_model, TEXT_RISK_MODEL_PATH)
    joblib.dump(_emotion_model, EMOTION_MODEL_PATH)
    joblib.dump(_risk_feature_model, RISK_FEATURE_MODEL_PATH)

    risk_feature_importances = []
    if hasattr(_risk_feature_model, 'feature_importances_'):
        importances = getattr(_risk_feature_model, 'feature_importances_')
        risk_feature_importances = [
            {'feature': feature, 'importance': round(float(value), 5)}
            for feature, value in sorted(zip(FEATURE_ORDER, importances), key=lambda item: item[1], reverse=True)
        ]

    _model_meta = {
        'textRiskClassifier': {
            'algorithm': 'TF-IDF + Logistic Regression',
            'trained': True,
            'trainedAt': _now_iso(),
            'samplesUsed': int(len(text_train)),
            'accuracy': round(text_risk_eval['train']['accuracy'] * 100, 1),
            'trainAccuracy': round(text_risk_eval['train']['accuracy'] * 100, 1),
            'validationAccuracy': round(text_risk_eval['validation'].get('accuracy', 0.0) * 100, 1),
            'testAccuracy': round(text_risk_eval['test'].get('accuracy', 0.0) * 100, 1),
            'validationF1Macro': round(text_risk_eval['validation'].get('f1Macro', 0.0) * 100, 1),
            'testF1Macro': round(text_risk_eval['test'].get('f1Macro', 0.0) * 100, 1),
            'cvAccuracy': round(text_risk_eval['validation'].get('accuracy', 0.0) * 100, 1),
            'confusionMatrixValidation': text_risk_eval['validation'].get('confusionMatrix', []),
            'confusionMatrixTest': text_risk_eval['test'].get('confusionMatrix', []),
            'falsePositivesValidation': text_risk_eval['validation'].get('falsePositives', {}),
            'falseNegativesValidation': text_risk_eval['validation'].get('falseNegatives', {}),
            'classDistribution': text_risk_eval['train'].get('classDistribution', {}),
            'thresholds': _decision_thresholds,
            'topReasons': _extract_top_text_reasons(_text_risk_model, 'I want to kill myself'),
        },
        'emotionClassifier': {
            'algorithm': 'TF-IDF + Logistic Regression',
            'trained': True,
            'trainedAt': _now_iso(),
            'samplesUsed': int(len(emotion_train)),
            'accuracy': round(emotion_eval['train']['accuracy'] * 100, 1),
            'trainAccuracy': round(emotion_eval['train']['accuracy'] * 100, 1),
            'validationAccuracy': round(emotion_eval['validation'].get('accuracy', 0.0) * 100, 1),
            'testAccuracy': round(emotion_eval['test'].get('accuracy', 0.0) * 100, 1),
            'validationF1Macro': round(emotion_eval['validation'].get('f1Macro', 0.0) * 100, 1),
            'testF1Macro': round(emotion_eval['test'].get('f1Macro', 0.0) * 100, 1),
            'confusionMatrixValidation': emotion_eval['validation'].get('confusionMatrix', []),
            'confusionMatrixTest': emotion_eval['test'].get('confusionMatrix', []),
            'falsePositivesValidation': emotion_eval['validation'].get('falsePositives', {}),
            'falseNegativesValidation': emotion_eval['validation'].get('falseNegatives', {}),
            'classDistribution': emotion_eval['train'].get('classDistribution', {}),
        },
        'riskFeatureClassifier': {
            'algorithm': 'LightGBM' if LGBMClassifier is not None else ('XGBoost' if XGBClassifier is not None else 'Gradient Boosting Classifier'),
            'trained': True,
            'trainedAt': _now_iso(),
            'samplesUsed': int(len(risk_train)),
            'accuracy': round(risk_eval['train']['accuracy'] * 100, 1),
            'trainAccuracy': round(risk_eval['train']['accuracy'] * 100, 1),
            'validationAccuracy': round(risk_eval['validation'].get('accuracy', 0.0) * 100, 1),
            'testAccuracy': round(risk_eval['test'].get('accuracy', 0.0) * 100, 1),
            'validationF1Macro': round(risk_eval['validation'].get('f1Macro', 0.0) * 100, 1),
            'testF1Macro': round(risk_eval['test'].get('f1Macro', 0.0) * 100, 1),
            'confusionMatrixValidation': risk_eval['validation'].get('confusionMatrix', []),
            'confusionMatrixTest': risk_eval['test'].get('confusionMatrix', []),
            'falsePositivesValidation': risk_eval['validation'].get('falsePositives', {}),
            'falseNegativesValidation': risk_eval['validation'].get('falseNegatives', {}),
            'classDistribution': risk_eval['train'].get('classDistribution', {}),
            'featureImportance': risk_feature_importances,
        },
        'datasets': {
            'text': {
                'train': dataset_summary(text_ds['train']),
                'validation': dataset_summary(text_ds['validation']),
                'test': dataset_summary(text_ds['test']),
            },
            'emotion': {
                'train': dataset_summary(emotion_ds['train'], label_key='emotion'),
                'validation': dataset_summary(emotion_ds['validation'], label_key='emotion'),
                'test': dataset_summary(emotion_ds['test'], label_key='emotion'),
            },
            'risk': {
                'train': dataset_summary(risk_ds['train'], label_key='label'),
                'validation': dataset_summary(risk_ds['validation'], label_key='label'),
                'test': dataset_summary(risk_ds['test'], label_key='label'),
            },
        },
        'evaluation': {
            'textRisk': text_risk_eval,
            'emotion': emotion_eval,
            'riskFeature': risk_eval,
        },
        'transformerBenchmark': transformer_benchmark,
        'framework': 'scikit-learn',
        'pythonVersion': f"{__import__('sys').version}",
        'runtime': {
            'trainMs': round((time.perf_counter() - start_time) * 1000.0, 2),
            'avgInferMs': _runtime_stats['avgInferMs'],
            'inferCount': _runtime_stats['inferCount'],
        },
    }

    _write_meta()
    print(json.dumps({
        'textRisk': _model_meta['textRiskClassifier']['validationAccuracy'],
        'emotion': _model_meta['emotionClassifier']['validationAccuracy'],
        'riskFeature': _model_meta['riskFeatureClassifier']['validationAccuracy'],
        'transformer': transformer_benchmark,
        'thresholds': _decision_thresholds,
    }, indent=2))
    return _model_meta


def load_models() -> None:
    global _text_risk_model, _emotion_model, _risk_feature_model, _model_meta, _decision_thresholds

    if not all(path.exists() for path in [TEXT_RISK_MODEL_PATH, EMOTION_MODEL_PATH, RISK_FEATURE_MODEL_PATH]):
        print('[WARN] Models not found on disk — training now...')
        train_all()
        return

    _text_risk_model = joblib.load(TEXT_RISK_MODEL_PATH)
    _emotion_model = joblib.load(EMOTION_MODEL_PATH)
    _risk_feature_model = joblib.load(RISK_FEATURE_MODEL_PATH)

    if META_PATH.exists():
        with META_PATH.open('r', encoding='utf-8') as handle:
            _model_meta = json.load(handle)
            _decision_thresholds = _model_meta.get('textRiskClassifier', {}).get('thresholds', _decision_thresholds)
    print('  [OK] All ML models loaded from disk')


def is_ready() -> bool:
    return all([_text_risk_model, _emotion_model, _risk_feature_model])


def get_model_meta() -> dict[str, Any]:
    return {**_model_meta, 'modelsLoaded': is_ready()}


def _build_text_response(model: Pipeline, text: str, label_name: str) -> dict[str, Any]:
    start = time.perf_counter()
    normalized_text = normalize_text(text)
    high_rule, matched_pattern = _high_risk_rule(normalized_text)
    proba = model.predict_proba([normalized_text])[0]
    classes = list(model.classes_)
    if label_name == 'risk':
        predicted, confidence, probabilities, uncertain, threshold_notes = _choose_risk_from_probabilities(proba, classes, high_rule)
        reasons = threshold_notes + _extract_top_text_reasons(model, normalized_text)
        if matched_pattern:
            reasons.insert(0, f'High-risk phrase matched: {matched_pattern}')
        response = {
            'risk': predicted,
            'riskConfidence': round(float(confidence), 3),
            'riskProbabilities': probabilities,
            'riskUncertain': uncertain,
            'riskThresholds': _decision_thresholds,
            'reasons': reasons,
        }
    else:
        predicted, confidence, probabilities, uncertain = _choose_emotion_from_probabilities(proba, classes)
        response = {
            'emotion': predicted,
            'emotionConfidence': round(float(confidence), 3),
            'emotionProbabilities': probabilities,
            'emotionUncertain': uncertain,
        }
    _merge_runtime_latency((time.perf_counter() - start) * 1000.0)
    return response


def classify_text(text: str) -> dict[str, Any]:
    if not _text_risk_model or not _emotion_model:
        return {'risk': 'LOW', 'emotion': 'neutral', 'riskConfidence': 0, 'emotionConfidence': 0, 'method': 'fallback'}

    start = time.perf_counter()
    risk_response = _build_text_response(_text_risk_model, text, 'risk')
    emotion_response = _build_text_response(_emotion_model, text, 'emotion')

    risk_conf = risk_response.get('riskConfidence', 0.0)
    emotion_conf = emotion_response.get('emotionConfidence', 0.0)
    result = {
        'risk': risk_response['risk'],
        'emotion': emotion_response['emotion'],
        'riskConfidence': risk_conf,
        'emotionConfidence': emotion_conf,
        'confidence': round((risk_conf + emotion_conf) / 2.0, 3),
        'method': 'python-scikit-learn',
        'riskProbabilities': risk_response.get('riskProbabilities', {}),
        'emotionProbabilities': emotion_response.get('emotionProbabilities', {}),
        'riskUncertain': risk_response.get('riskUncertain', False),
        'emotionUncertain': emotion_response.get('emotionUncertain', False),
        'reasons': risk_response.get('reasons', []),
    }

    if _transformer.available():
        result['transformer'] = _transformer.predict(text)

    _merge_runtime_latency((time.perf_counter() - start) * 1000.0)
    return result


def predict_risk(features: dict[str, Any]) -> dict[str, Any]:
    if not _risk_feature_model:
        return {'riskLevel': 'LOW', 'confidence': 0, 'method': 'fallback', 'probabilities': {}}

    start = time.perf_counter()
    X = np.array([[float(features.get(feature, 0.0)) for feature in FEATURE_ORDER]])
    probabilities = _risk_feature_model.predict_proba(X)[0]
    classes = list(_risk_feature_model.classes_)
    top_index = int(np.argmax(probabilities))
    risk_level = classes[top_index]
    confidence = float(probabilities[top_index])

    if risk_level == 'HIGH' and confidence < _decision_thresholds['riskHigh']:
        risk_level = 'MED' if probabilities[classes.index('MED')] >= probabilities[classes.index('LOW')] else 'LOW'
        confidence = float(probabilities[classes.index(risk_level)])

    response = {
        'riskLevel': risk_level,
        'confidence': round(confidence, 3),
        'method': 'python-scikit-learn',
        'probabilities': {cls: round(float(prob), 3) for cls, prob in zip(classes, probabilities)},
        'thresholds': _decision_thresholds,
        'uncertain': confidence < _decision_thresholds['riskUncertain'],
    }
    _merge_runtime_latency((time.perf_counter() - start) * 1000.0)
    return response


if __name__ == '__main__':
    meta = train_all()
    print('\n🧪 Quick Test Predictions:')
    print('-' * 40)
    for sample in [
        "I want to kill myself I can't take this anymore",
        'cravings are really strong today I want to use',
        'had a great day 90 days sober feeling proud',
        "I'm so anxious and scared I can't breathe",
    ]:
        print(sample)
        print(classify_text(sample))
