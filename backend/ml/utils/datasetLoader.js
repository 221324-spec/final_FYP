const fs = require('fs');
const path = require('path');
const {
  normalizeText,
  stripPunctuation,
  makeCasualVariant,
  makeRomanUrduVariant,
  makeNoisyVariant,
} = require('./textNormalization');

const DATASET_ROOT = path.join(__dirname, '..', 'datasets');

function loadModule(category, split) {
  const modulePath = path.join(DATASET_ROOT, category, `${split}.js`);
  if (!fs.existsSync(modulePath)) return [];
  delete require.cache[require.resolve(modulePath)];
  const items = require(modulePath);
  return Array.isArray(items) ? items : [];
}

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function normalizeTextRecord(record, index, split) {
  const text = normalizeText(record.text);
  return {
    ...record,
    text,
    originalText: record.text,
    split,
    source: record.source || `${split}:${index}`,
  };
}

function normalizeRiskRecord(record, index, split) {
  const features = record.features || {};
  const normalized = {
    avgCraving: clamp01(Number(features.avgCraving ?? 0)),
    maxCraving: clamp01(Number(features.maxCraving ?? 0)),
    avgMood: clamp01(Number(features.avgMood ?? 0)),
    moodDecline: clamp01(Number(features.moodDecline ?? 0)),
    triggers: clamp01(Number(features.triggers ?? 0)),
    activity: clamp01(Number(features.activity ?? 0)),
    missed: clamp01(Number(features.missed ?? 0)),
    relapses: clamp01(Number(features.relapses ?? 0)),
  };

  return {
    ...record,
    features: normalized,
    split,
    source: record.source || `${split}:${index}`,
  };
}

function augmentTextRecord(record) {
  const variants = [
    { ...record, text: record.text, variant: 'normalized' },
    { ...record, text: stripPunctuation(record.text), variant: 'punctuation-stripped' },
    { ...record, text: makeCasualVariant(record.text), variant: 'casual-slang' },
  ];

  const romanVariant = makeRomanUrduVariant(record.text);
  if (romanVariant !== record.text) {
    variants.push({ ...record, text: romanVariant, variant: 'roman-urdu' });
  }

  const noisyVariant = makeNoisyVariant(record.text);
  if (noisyVariant !== record.text) {
    variants.push({ ...record, text: noisyVariant, variant: 'noisy' });
  }

  return variants;
}

function augmentRiskRecord(record) {
  const deltas = [
    { avgCraving: 0, maxCraving: 0, avgMood: 0, moodDecline: 0, triggers: 0, activity: 0, missed: 0, relapses: 0, variant: 'normalized' },
    { avgCraving: 0.03, maxCraving: 0.03, avgMood: -0.02, moodDecline: 0.03, triggers: 0.02, activity: -0.02, missed: 0.02, relapses: 0.02, variant: 'slight-up' },
    { avgCraving: -0.03, maxCraving: -0.02, avgMood: 0.02, moodDecline: -0.02, triggers: -0.02, activity: 0.02, missed: -0.02, relapses: -0.02, variant: 'slight-down' },
  ];

  return deltas.map((delta) => ({
    ...record,
    features: {
      avgCraving: clamp01(record.features.avgCraving + delta.avgCraving),
      maxCraving: clamp01(record.features.maxCraving + delta.maxCraving),
      avgMood: clamp01(record.features.avgMood + delta.avgMood),
      moodDecline: clamp01(record.features.moodDecline + delta.moodDecline),
      triggers: clamp01(record.features.triggers + delta.triggers),
      activity: clamp01(record.features.activity + delta.activity),
      missed: clamp01(record.features.missed + delta.missed),
      relapses: clamp01(record.features.relapses + delta.relapses),
    },
    variant: delta.variant,
  }));
}

function dedupeByKey(records, keyFn) {
  const seen = new Set();
  const output = [];

  for (const record of records) {
    const key = keyFn(record);
    if (seen.has(key)) continue;
    seen.add(key);
    output.push(record);
  }

  return output;
}

function loadTextDataset() {
  const train = loadModule('text', 'train').map((record, index) => normalizeTextRecord(record, index, 'train'));
  const validation = loadModule('text', 'validation').map((record, index) => normalizeTextRecord(record, index, 'validation'));
  const test = loadModule('text', 'test').map((record, index) => normalizeTextRecord(record, index, 'test'));
  const all = [...train, ...validation, ...test];

  return {
    train: dedupeByKey(train.flatMap(augmentTextRecord), (record) => `${record.risk || ''}|${record.emotion || ''}|${record.text}`),
    validation,
    test,
    all: dedupeByKey(all.flatMap(augmentTextRecord), (record) => `${record.risk || ''}|${record.emotion || ''}|${record.text}`),
  };
}

function loadEmotionDataset() {
  const train = loadModule('emotions', 'train').map((record, index) => normalizeTextRecord(record, index, 'train'));
  const validation = loadModule('emotions', 'validation').map((record, index) => normalizeTextRecord(record, index, 'validation'));
  const test = loadModule('emotions', 'test').map((record, index) => normalizeTextRecord(record, index, 'test'));
  const all = [...train, ...validation, ...test];

  return {
    train: dedupeByKey(train.flatMap(augmentTextRecord), (record) => `${record.emotion || ''}|${record.text}`),
    validation,
    test,
    all: dedupeByKey(all.flatMap(augmentTextRecord), (record) => `${record.emotion || ''}|${record.text}`),
  };
}

function loadRiskDataset() {
  const train = loadModule('risk', 'train').map((record, index) => normalizeRiskRecord(record, index, 'train'));
  const validation = loadModule('risk', 'validation').map((record, index) => normalizeRiskRecord(record, index, 'validation'));
  const test = loadModule('risk', 'test').map((record, index) => normalizeRiskRecord(record, index, 'test'));
  const all = [...train, ...validation, ...test];

  return {
    train: dedupeByKey(train.flatMap(augmentRiskRecord), (record) => `${record.label}|${JSON.stringify(record.features)}`),
    validation,
    test,
    all: dedupeByKey(all.flatMap(augmentRiskRecord), (record) => `${record.label}|${JSON.stringify(record.features)}`),
  };
}

function getLabelCounts(records, key) {
  return records.reduce((counts, record) => {
    const value = record[key] || 'unknown';
    counts[value] = (counts[value] || 0) + 1;
    return counts;
  }, {});
}

function getTextStats(records) {
  const lengths = records.map((record) => record.text.length);
  const total = lengths.reduce((sum, value) => sum + value, 0);
  return {
    count: records.length,
    avgLength: records.length ? +(total / records.length).toFixed(1) : 0,
    minLength: lengths.length ? Math.min(...lengths) : 0,
    maxLength: lengths.length ? Math.max(...lengths) : 0,
    riskCounts: getLabelCounts(records, 'risk'),
    emotionCounts: getLabelCounts(records, 'emotion'),
  };
}

function getRiskStats(records) {
  return {
    count: records.length,
    labelCounts: getLabelCounts(records, 'label'),
  };
}

module.exports = {
  loadTextDataset,
  loadEmotionDataset,
  loadRiskDataset,
  getTextStats,
  getRiskStats,
  normalizeTextRecord,
  normalizeRiskRecord,
};