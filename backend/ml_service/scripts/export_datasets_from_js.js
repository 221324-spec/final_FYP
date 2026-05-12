#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const jsDatasets = require(path.join(root, '..', 'ml', 'trainingData'));

const outputRoot = path.join(root, 'datasets');

const files = {
  text: { train: jsDatasets.textTrainData, validation: jsDatasets.textValidationData, test: jsDatasets.textTestData },
  emotions: { train: jsDatasets.emotionTrainData, validation: jsDatasets.emotionValidationData, test: jsDatasets.emotionTestData },
  risk: { train: jsDatasets.riskTrainData, validation: jsDatasets.riskValidationData, test: jsDatasets.riskTestData },
};

for (const [category, splits] of Object.entries(files)) {
  for (const [split, data] of Object.entries(splits)) {
    const dir = path.join(outputRoot, category);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, `${split}.json`), JSON.stringify(data, null, 2), 'utf-8');
    console.log(`[export] ${category}/${split}.json -> ${data.length} records`);
  }
}
