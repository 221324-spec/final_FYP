/**
 * Local LLM via LM Studio (OpenAI-compatible /v1/chat/completions).
 * Set LMSTUDIO_URL (e.g. http://127.0.0.1:1234) and LMSTUDIO_MODEL to the loaded model id.
 */

const axios = require('axios');
const {
  buildSystemInstruction,
  buildUserPrompt,
  normalizeConversationHistory,
} = require('./groqService');

function openaiChatCompletionsUrl() {
  let base = (process.env.LMSTUDIO_URL || 'http://127.0.0.1:1234').trim().replace(/\/+$/, '');
  if (/\/v1$/i.test(base)) return `${base}/chat/completions`;
  return `${base}/v1/chat/completions`;
}

/**
 * @param {Array<{sender: string, text: string}>} conversationHistory
 * @param {string} currentText
 * @param {object} analysis
 * @returns {Promise<string>}
 */
async function generateLmStudioReply(conversationHistory, currentText, analysis) {
  const model = (process.env.LMSTUDIO_MODEL || 'local-model').trim();
  const url = openaiChatCompletionsUrl();
  const timeoutMs = Number(process.env.LMSTUDIO_TIMEOUT_MS || 120000);

  const messages = [{ role: 'system', content: buildSystemInstruction() }];
  const safeHistory = normalizeConversationHistory(conversationHistory, currentText);
  for (const msg of safeHistory) {
    const role = msg.sender === 'patient' ? 'user' : 'assistant';
    const text = typeof msg.text === 'string' ? msg.text.trim() : '';
    if (!text) continue;
    messages.push({ role, content: text });
  }
  messages.push({ role: 'user', content: buildUserPrompt({ analysis, currentText }) });

  let data;
  try {
    const res = await axios.post(
      url,
      {
        model,
        messages,
        temperature: 0.7,
        max_tokens: 512,
      },
      {
        timeout: timeoutMs,
        headers: { 'Content-Type': 'application/json' },
        validateStatus: (s) => s < 500,
      }
    );
    data = res.data;
    if (res.status >= 400) {
      const detail = typeof data === 'object' ? JSON.stringify(data) : String(data);
      throw new Error(`LM Studio HTTP ${res.status}: ${detail.slice(0, 400)}`);
    }
  } catch (err) {
    if (err.code === 'ECONNREFUSED' || err.code === 'ENOTFOUND') {
      throw new Error(
        `Cannot reach LM Studio at ${url}. Start LM Studio, load a model, enable the local server, and check LMSTUDIO_URL.`
      );
    }
    throw err;
  }

  const content = data?.choices?.[0]?.message?.content;
  const cleaned = typeof content === 'string' ? content.trim() : '';
  if (!cleaned) {
    throw new Error('LM Studio returned an empty reply. Check that a model is loaded and the id matches LMSTUDIO_MODEL.');
  }
  return cleaned;
}

module.exports = { generateLmStudioReply, openaiChatCompletionsUrl };
