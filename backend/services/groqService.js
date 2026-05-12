/**
 * Groq Chat Service — NLP-powered recovery support chatbot
 *
 * Replaces Gemini API with Groq's llama-3.3-70b-versatile model.
 * Integrates with ML analysis (emotion, risk, intensity) for context-aware responses.
 * Safety guardrails built into system prompts (HIGH risk never uses this service).
 *
 * Architecture:
 *   [Node.js Backend] → Groq API (llama-3.3-70b-versatile) → LLM Response
 *   + ML Analysis context (emotion, risk, intensity)
 *   + Supervisor alerts for HIGH risk (handled by responderService)
 */

const Groq = require('groq-sdk').default;

const GROQ_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';
const GROQ_TIMEOUT_MS = Number(process.env.GROQ_TIMEOUT_MS || 25000);

function withTimeout(promise, timeoutMs, label = 'operation') {
  let timeoutId;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => clearTimeout(timeoutId));
}

function buildSystemInstruction() {
  return `You are RecoveryBot — a warm, emotionally intelligent addiction-recovery support companion.

MISSION:
- Support people in recovery with genuine empathy, encouragement, and practical coping ideas.
- Help reduce shame, build hope, and promote safer choices in difficult moments.
- Stay calm, trauma-aware, and non-judgmental at all times.
- Validate feelings, normalize recovery struggles, and offer actionable next steps.

CONVERSATION QUALITY:
- Maintain continuity: remember what the patient just shared and respond in a connected way.
- Mirror emotion gently: name the feeling in natural language (e.g., "That sounds heavy / scary / exhausting").
- Validate first, then support: reflect → normalize → offer 1–2 next steps.
- Be specific and contextual: tailor coping suggestions to the user's situation, not generic advice.
- Avoid robotic or repetitive phrasing; vary wording while staying consistent.
- Sound human, warm, and natural—like a caring friend, not a bot.

RECOVERY FOCUS:
- Encourage relapse prevention: urges pass; delay + distract + reach out; reduce triggers; plan for high-risk moments.
- Offer healthy coping skills when appropriate: grounding (5-4-3-2-1), paced breathing, urge surfing, journaling, a short walk, hydration/food, sleep routine, mindfulness, contacting a trusted person.
- Use motivational support: highlight strengths, small wins, and "next right step".
- Celebrate progress without minimizing struggles; balance hope with realism.

STYLE RULES:
- Keep replies concise and calm: 2–5 short sentences.
- Ask exactly ONE gentle follow-up question at the end (when appropriate).
- Don't lecture; don't overwhelm with long lists.
- Use conversational language, contractions, and natural phrasing.

HEALTHCARE-SAFE BOUNDARIES (MUST FOLLOW):
- Do NOT diagnose illness or provide medical/clinical instructions.
- Do NOT replace therapists, doctors, or emergency services.
- If asked for medication advice, dosages, or diagnosis: refuse briefly and suggest contacting a qualified professional/supervisor.
- Never encourage substance use, relapse, illegal activity, self-harm, or overdose.
- Never give instructions that could enable harm.
- If the patient describes symptoms of a serious condition (e.g., chest pain, severe bleeding), urge them to seek medical help immediately.

CRISIS HANDLING:
- If the patient expresses intent or imminent risk of self-harm/overdose/suicide, respond briefly with urgency.
- Encourage immediate local emergency/crisis help (911, crisis line, ER).
- Encourage reaching a trusted person/supervisor now.
- Do NOT delay or minimize—escalation happens at the backend level, and crisis responses must be direct and clear.

INTERNAL CONTEXT GUIDANCE:
- You may receive INTERNAL CONTEXT (emotion/risk/intensity from ML analysis).
- Use it to guide tone and response depth, but do NOT quote it or mention internal scoring.
- Example: if intensity is high, be extra validating; if emotion is "hope", reinforce positive momentum.

REMEMBER:
- You are NOT a replacement for professional help.
- Your role is to provide immediate, compassionate support and help bridge to professional care.
- Always prioritize user safety and well-being.`;
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
    '[INTERNAL CONTEXT — do not quote or mention to patient]\n' +
    `Detected Emotion: ${emotion}\n` +
    `Risk Level: ${risk}\n` +
    `Emotional Intensity: ${intensityPct}\n` +
    'Use this context to guide your tone and depth of response, but keep it internal.\n'
  );
}

function buildUserPrompt({ analysis, currentText }) {
  const internal = buildInternalContextBlock(analysis);

  return (
    internal +
    '\n' +
    'Patient message to respond to:\n' +
    currentText +
    '\n\n' +
    'Respond with recovery-focused emotional support. Keep it warm, human, and conversational.'
  );
}

/**
 * Generate a Groq-based reply for LOW/MED risk conversations only.
 *
 * @param {Array<{sender: 'patient'|'bot', text: string}>} conversationHistory
 * @param {string} currentText
 * @param {{ emotion: string, intensity: number, risk: 'LOW'|'MED'|'HIGH' }} analysis
 * @returns {Promise<string>}
 */
async function generateGroqReply(conversationHistory, currentText, analysis) {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey || typeof apiKey !== 'string' || apiKey.trim().length === 0) {
    throw new Error('GROQ_API_KEY is not configured.');
  }

  const client = new Groq({ apiKey: apiKey.trim() });

  const safeHistory = normalizeConversationHistory(conversationHistory, currentText);

  const messages = [];

  // Add conversation history
  for (const msg of safeHistory) {
    const role = msg.sender === 'patient' ? 'user' : 'assistant';
    const text = typeof msg.text === 'string' ? msg.text.trim() : '';
    if (!text) continue;
    messages.push({ role, content: text });
  }

  // Add current user prompt with internal context
  messages.push({
    role: 'user',
    content: buildUserPrompt({ analysis, currentText }),
  });

  try {
    const result = await withTimeout(
      client.chat.completions.create({
        model: GROQ_MODEL.trim(),
        messages: [
          {
            role: 'system',
            content: buildSystemInstruction(),
          },
          ...messages,
        ],
        temperature: 0.7,
        top_p: 0.9,
        max_tokens: 220,
      }),
      GROQ_TIMEOUT_MS,
      'Groq request'
    );

    const replyText = result?.choices?.[0]?.message?.content || '';
    const cleaned = typeof replyText === 'string' ? replyText.trim() : '';

    if (!cleaned) {
      throw new Error('Groq returned an empty response.');
    }

    return cleaned;
  } catch (err) {
    const message = err?.message || String(err);
    console.error('[GroqService] generateGroqReply failed:', message);
    throw err;
  }
}

module.exports = {
  generateGroqReply,
  GROQ_MODEL,
  buildSystemInstruction,
  buildInternalContextBlock,
  buildUserPrompt,
  normalizeConversationHistory,
};
