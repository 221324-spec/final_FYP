const SLANG_REPLACEMENTS = [
  [/\bim\b/g, 'i am'],
  [/\bive\b/g, 'i have'],
  [/\bdont\b/g, 'do not'],
  [/\bcant\b/g, 'cannot'],
  [/\bwont\b/g, 'will not'],
  [/\bdoesnt\b/g, 'does not'],
  [/\bdidnt\b/g, 'did not'],
  [/\bshouldnt\b/g, 'should not'],
  [/\bwouldnt\b/g, 'would not'],
  [/\bthere's\b/g, 'there is'],
  [/\btheres\b/g, 'there is'],
  [/\bpls\b/g, 'please'],
  [/\bplz\b/g, 'please'],
  [/\bu\b/g, 'you'],
  [/\bur\b/g, 'your'],
  [/\bgonna\b/g, 'going to'],
  [/\bwanna\b/g, 'want to'],
  [/\bkinda\b/g, 'kind of'],
  [/\bsorta\b/g, 'sort of'],
  [/\byaar\b/g, 'friend'],
  [/\bghabrahat\b/g, 'anxiety'],
  [/\bbechain\b/g, 'restless'],
  [/\budas\b/g, 'sad'],
  [/\budasi\b/g, 'sadness'],
  [/\bumeed\b/g, 'hope'],
  [/\bmehfooz\b/g, 'safe'],
  [/\bbohat\b/g, 'very'],
  [/\bbhot\b/g, 'very'],
  [/\bthora\b/g, 'a little'],
  [/\baaj\b/g, 'today'],
  [/\bkal\b/g, 'tomorrow'],
];

function normalizeText(text) {
  if (typeof text !== 'string') return '';

  let normalized = text.normalize('NFKC').toLowerCase().trim();
  normalized = normalized.replace(/[“”]/g, '"').replace(/[‘’]/g, "'");
  normalized = normalized.replace(/[^\p{L}\p{N}\s'’/-]+/gu, ' ');

  for (const [pattern, replacement] of SLANG_REPLACEMENTS) {
    normalized = normalized.replace(pattern, replacement);
  }

  normalized = normalized.replace(/\s+/g, ' ').trim();
  return normalized;
}

function stripPunctuation(text) {
  return normalizeText(text).replace(/[\/'-]/g, ' ').replace(/\s+/g, ' ').trim();
}

function makeCasualVariant(text) {
  return normalizeText(text)
    .replace(/\byou are\b/g, 'youre')
    .replace(/\bdo not\b/g, 'dont')
    .replace(/\bcannot\b/g, 'cant')
    .replace(/\bi am\b/g, "i'm")
    .replace(/\bi have\b/g, "i've");
}

function makeRomanUrduVariant(text) {
  return normalizeText(text)
    .replace(/\banxiety\b/g, 'ghabrahat')
    .replace(/\bsadness\b/g, 'udas')
    .replace(/\bsad\b/g, 'udas')
    .replace(/\bhope\b/g, 'umeed')
    .replace(/\bsafe\b/g, 'mehfooz')
    .replace(/\brestless\b/g, 'bechain')
    .replace(/\bvery\b/g, 'bohat');
}

function makeNoisyVariant(text) {
  return stripPunctuation(text)
    .replace(/\bvery\b/g, 'vry')
    .replace(/\bplease\b/g, 'pls')
    .replace(/\bfriend\b/g, 'yaar')
    .replace(/\btoday\b/g, 'aaj');
}

module.exports = {
  normalizeText,
  stripPunctuation,
  makeCasualVariant,
  makeRomanUrduVariant,
  makeNoisyVariant,
};