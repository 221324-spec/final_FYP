#!/usr/bin/env node

const { loadTextDataset, loadEmotionDataset, loadRiskDataset, getTextStats, getRiskStats } = require('../utils/datasetLoader');

function printSection(title, stats) {
  console.log(`\n${title}`);
  console.log(JSON.stringify(stats, null, 2));
}

function main() {
  const text = loadTextDataset();
  const emotion = loadEmotionDataset();
  const risk = loadRiskDataset();

  printSection('TEXT DATASET', {
    train: getTextStats(text.train),
    validation: getTextStats(text.validation),
    test: getTextStats(text.test),
    all: getTextStats(text.all),
  });

  printSection('EMOTION DATASET', {
    train: getTextStats(emotion.train),
    validation: getTextStats(emotion.validation),
    test: getTextStats(emotion.test),
    all: getTextStats(emotion.all),
  });

  printSection('RISK DATASET', {
    train: getRiskStats(risk.train),
    validation: getRiskStats(risk.validation),
    test: getRiskStats(risk.test),
    all: getRiskStats(risk.all),
  });
}

if (require.main === module) {
  main();
}