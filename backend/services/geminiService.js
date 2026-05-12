const {
  GoogleGenerativeAI,
} = require('@google/generative-ai');

const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.5-flash';

function withTimeout(promise, timeoutMs, label = 'operation') {
  let timeoutId;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => clearTimeout(timeoutId));
}

function buildSystemInstruction() {
  return (
    'You are RecoveryBot — a warm, emotionally intelligent addiction-recovery support companion.\n' +
    '\n' +
    'Mission:\n' +
    '- Support people in recovery with empathy, encouragement, and practical coping ideas.\n' +
    '- Help reduce shame, build hope, and promote safer choices in difficult moments.\n' +
    '- Stay calm, trauma-aware, and non-judgmental at all times.\n' +
    '\n' +
    'Conversation quality (NLP behavior):\n' +
    '- Maintain continuity: remember what the patient just shared and respond in a connected way.\n' +
    '- Mirror emotion gently: name the feeling in natural language (e.g., “That sounds heavy / scary / exhausting”).\n' +
    '- Validate first, then support: reflect → normalize → offer 1–2 next steps.\n' +
    '- Be specific and contextual: tailor coping suggestions to the user’s situation, not generic advice.\n' +
    '- Avoid robotic or repetitive phrasing; vary wording while staying consistent.\n' +
    '\n' +
    'Recovery focus:\n' +
    '- Encourage relapse prevention: urges pass; delay + distract + reach out; reduce triggers; plan for high-risk moments.\n' +
    '- Offer healthy coping skills when appropriate: grounding (5-4-3-2-1), paced breathing, urge surfing, journaling, a short walk, hydration/food, sleep routine, mindfulness, contacting a trusted person.\n' +
    '- Use motivational support: highlight strengths, small wins, and “next right step”.\n' +
    '\n' +
    'Style rules:\n' +
    '- Sound human, warm, and natural.\n' +
    '- Keep replies concise and calm: 2–5 short sentences.\n' +
    '- Ask exactly ONE gentle follow-up question at the end.\n' +
    '- Don’t lecture; don’t overwhelm with long lists.\n' +
    '\n' +
    'Healthcare-safe boundaries (must follow):\n' +
    '- Do NOT diagnose illness or provide medical/clinical instructions.\n' +
    '- Do NOT replace therapists, doctors, or emergency services.\n' +
    '- If asked for medication advice, dosages, or diagnosis: refuse briefly and suggest contacting a qualified professional/supervisor.\n' +
    '- Never encourage substance use, relapse, illegal activity, self-harm, or overdose.\n' +
    '- Never give instructions that could enable harm.\n' +
    '\n' +
    'Crisis handling:\n' +
    '- If the patient expresses intent or imminent risk of self-harm/overdose/suicide, respond briefly with urgency, encourage immediate local emergency/crisis help, and encourage reaching a trusted person/supervisor now.\n' +
    '\n' +
    'Privacy & internal context:\n' +
    '- You may receive INTERNAL context (emotion/risk/intensity). Use it to guide tone, but do not quote it or mention internal scoring.'
  );
}

/** Merge same-role turns so the API always gets a valid user/model alternation. */
function collapseConsecutiveRoles(contents) {
  const out = [];
  for (const c of contents) {
    const text = (c.parts || [])
      .map((p) => (typeof p.text === 'string' ? p.text : ''))
      .join('\n')
      .trim();
    if (!text) continue;
    const prev = out[out.length - 1];
    if (prev && prev.role === c.role) {
      prev.parts[0].text = `${prev.parts[0].text}\n\n${text}`;
    } else {
      out.push({ role: c.role, parts: [{ text }] });
    }
  }
  while (out.length && out[0].role !== 'user') {
    out.shift();
  }
  return out;
}

function normalizeConversationHistory(conversationHistory, currentText) {
  const history = Array.isArray(conversationHistory) ? conversationHistory : [];
  if (history.length === 0) return [];

  // Avoid duplicating the current patient message if it already appears in history.
  const last = history[history.length - 1];
  if (last?.sender === 'patient' && typeof last.text === 'string' && last.text.trim() === (currentText || '').trim()) {
    return history.slice(0, -1);
  }

  return history;
}

function buildInternalContextBlock(analysis) {
  if (!analysis) return '';
  const emotion = analysis.emotion || 'unknown';
  const risk = analysis.risk || 'unknown';
  const intensityPct =
    typeof analysis.intensity === 'number' ? `${Math.round(analysis.intensity * 100)}%` : 'unknown';

  return (
    '[INTERNAL CONTEXT — do not quote]\n' +
    `Emotion: ${emotion}\n` +
    `Risk: ${risk}\n` +
    `Intensity: ${intensityPct}\n`
  );
}

function buildUserPrompt({ analysis, currentText }) {
  const internal = buildInternalContextBlock(analysis);

  return (
    internal +
    '\n' +
    'Respond to the patient message below with recovery-focused emotional support.\n' +
    'Patient message:\n' +
    currentText
  );
}

/**
 * Generate a Gemini-based reply for LOW/MED risk conversations only.
 *
 * @param {Array<{sender: 'patient'|'bot', text: string}>} conversationHistory
 * @param {string} currentText
 * @param {{ emotion: string, intensity: number, risk: 'LOW'|'MED'|'HIGH' }} analysis
 * @returns {Promise<string>}
 */
async function generateGeminiReply(conversationHistory, currentText, analysis) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || typeof apiKey !== 'string' || apiKey.trim().length === 0) {
    throw new Error('GEMINI_API_KEY is not configured.');
  }

  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: GEMINI_MODEL.trim(),
    systemInstruction: buildSystemInstruction(),
  });

  const safeHistory = normalizeConversationHistory(conversationHistory, currentText);

  const contents = [];
  for (const msg of safeHistory) {
    const role = msg.sender === 'patient' ? 'user' : 'model';
    const text = typeof msg.text === 'string' ? msg.text.trim() : '';
    if (!text) continue;
    contents.push({ role, parts: [{ text }] });
  }

  contents.push({
    role: 'user',
    parts: [{ text: buildUserPrompt({ analysis, currentText }) }],
  });

  let collapsedContents = collapseConsecutiveRoles(contents);
  if (collapsedContents.length === 0) {
    collapsedContents.push({
      role: 'user',
      parts: [{ text: buildUserPrompt({ analysis, currentText }) }],
    });
  }

  const generationConfig = {
    temperature: 0.7,
    topP: 0.9,
    maxOutputTokens: 220,
  };

  const timeoutMs = Number(process.env.GEMINI_TIMEOUT_MS || 25000);

  try {
    const result = await withTimeout(
      model.generateContent({
        contents: collapsedContents,
        generationConfig,
      }),
      timeoutMs,
      'Gemini request'
    );

    let replyText = '';
    try {
      replyText = typeof result?.response?.text === 'function' ? result.response.text() : '';
    } catch (textErr) {
      console.warn('[GeminiService] response.text() failed:', textErr?.message || textErr);
    }
    if (!replyText || !String(replyText).trim()) {
      const parts = result?.response?.candidates?.[0]?.content?.parts;
      if (Array.isArray(parts)) {
        replyText = parts.map((p) => p?.text || '').join('');
      }
    }
    const cleaned = typeof replyText === 'string' ? replyText.trim() : '';

    if (!cleaned) {
      const fr = result?.response?.candidates?.[0]?.finishReason;
      throw new Error(
        fr ? `Gemini returned no text (finishReason: ${fr}).` : 'Gemini returned an empty response.'
      );
    }

    return cleaned;
  } catch (err) {
    const message = err?.message || String(err);
    console.error('[GeminiService] generateGeminiReply failed:', message);
    throw err;
  }
}

module.exports = {
  generateGeminiReply,
  GEMINI_MODEL,
  buildSystemInstruction,
  buildInternalContextBlock,
  buildUserPrompt,
  normalizeConversationHistory,
};
