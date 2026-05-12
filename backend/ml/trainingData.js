/**
 * ML Training Data — Compatibility wrapper.
 *
 * The canonical datasets now live in backend/ml/datasets/ and are loaded
 * through backend/ml/utils/datasetLoader.js so we can keep train/validation/test
 * splits, augmentation, and normalization in one place.
 */

const { loadTextDataset, loadEmotionDataset, loadRiskDataset } = require('./utils/datasetLoader');

const textDataset = loadTextDataset();
const emotionDataset = loadEmotionDataset();
const riskDataset = loadRiskDataset();

module.exports = {
  textTrainingData: textDataset.all,
  textTrainData: textDataset.train,
  textValidationData: textDataset.validation,
  textTestData: textDataset.test,
  emotionTrainingData: emotionDataset.all,
  emotionTrainData: emotionDataset.train,
  emotionValidationData: emotionDataset.validation,
  emotionTestData: emotionDataset.test,
  riskTrainingData: riskDataset.all,
  riskTrainData: riskDataset.train,
  riskValidationData: riskDataset.validation,
  riskTestData: riskDataset.test,
};