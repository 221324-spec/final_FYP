/**
 * Responder Service — Phase 2
 *
 * Abstraction layer for generating bot replies.
 *
 * Routing logic:
 *   HIGH risk  → crisis template
 *   Medical Q  → medical deflection template
 *   Escalation → supervisor escalation template (no LLM)
 *   LOW / MED  → supportive templates keyed by emotion
 */

const { generateGroqReply } = require('./groqService');
const { generateLmStudioReply } = require('./lmStudioService');

function hasGroqKey() {
  return !!(process.env.GROQ_API_KEY && String(process.env.GROQ_API_KEY).trim().length > 0);
}

/**
 * GROQ | LMSTUDIO | TEMPLATE (explicit), or auto: Groq if key else template.
 */
function resolveChatProvider() {
  const env = (process.env.CHAT_PROVIDER || '').trim().toUpperCase();
  if (env === 'TEMPLATE') return 'TEMPLATE';
  if (env === 'GROQ') return hasGroqKey() ? 'GROQ' : 'TEMPLATE';
  if (env === 'LMSTUDIO') return 'LMSTUDIO';
  if (env) {
    console.warn(`[ResponderService] Unknown CHAT_PROVIDER="${env}" — using TEMPLATE`);
    return 'TEMPLATE';
  }
  return hasGroqKey() ? 'GROQ' : 'TEMPLATE';
}

// ── Crisis template (HIGH risk) ──
function crisisTemplate() {
  return (
    "I'm really concerned about your safety right now. " +
    "If you are in immediate danger, please contact local emergency services or a crisis helpline immediately. " +
    "I'm alerting your supervisor and care team so someone can reach out to support you right away. " +
    "You are not alone — help is available. Are you safe right now?"
  );
}

// ── Supportive reply templates keyed by emotion ──
const SUPPORTIVE_TEMPLATES = {
  anxiety: [
    "It sounds like you're feeling really anxious right now, and that's completely valid. " +
    "Anxiety can feel overwhelming, but it will pass. " +
    "Try taking a slow, deep breath — inhale for 4 counts, hold for 4, exhale for 4. " +
    "Grounding exercises can also help: name 5 things you can see around you. " +
    "If the anxiety continues or feels unmanageable, please reach out to your supervisor or care team — they're here to help.",

    "I hear you — anxiety is tough, and it takes courage to talk about it. " +
    "One small step you can try right now is placing your feet flat on the floor and focusing on the sensation for a moment. " +
    "Remind yourself: you've gotten through difficult moments before, and you can do it again. " +
    "Your care team is always available if you need extra support.",
  ],

  sadness: [
    "I'm sorry you're going through a hard time. Your feelings are real and they matter. " +
    "Recovery isn't always a straight line — it's okay to have tough days. " +
    "One small thing that might help: try writing down one thing you're grateful for today, even if it feels small. " +
    "If the sadness feels heavy or persistent, please talk to your supervisor or a trusted person. You don't have to carry this alone.",

    "It sounds like you're carrying a lot right now. Thank you for sharing that with me. " +
    "Feeling sad doesn't mean you're failing — it means you're human. " +
    "Try doing one small comforting thing for yourself today, like a warm drink or a short walk. " +
    "Your care team is here whenever you need someone to talk to.",
  ],

  anger: [
    "It sounds like you're feeling frustrated or angry, and that's a completely normal emotion. " +
    "Anger often signals that something important to you feels threatened or unfair. " +
    "Before acting on it, try stepping away for a few minutes — even a short pause can help. " +
    "Physical movement like a walk or stretching can also release some of that tension. " +
    "If you want to talk through what's bothering you, your supervisor is available to listen.",

    "I can hear that you're feeling really frustrated right now. Your feelings are valid. " +
    "One thing that can help in the moment: try clenching your fists tightly for 5 seconds, then slowly releasing. " +
    "It can help your body let go of some of that tension. " +
    "Remember, it's okay to ask for help — your care team is here for exactly these moments.",
  ],

  hope: [
    "That's wonderful to hear! Every step forward in your recovery is worth celebrating. " +
    "Keep recognizing these positive moments — they're proof of your strength and commitment. " +
    "Consider writing down what helped you feel this way so you can revisit it on harder days. " +
    "You're doing great — keep going!",

    "I'm so glad to hear things are looking up! You should be really proud of yourself. " +
    "Progress in recovery, no matter how small, is a big deal. " +
    "Keep leaning into the habits and people that support your growth. " +
    "Your journey is inspiring — keep it up!",
  ],

  neutral: [
    "Thanks for sharing. I'm here to listen and support you through your recovery journey. " +
    "If there's anything specific on your mind — feelings, challenges, wins — feel free to share. " +
    "Remember, your care team is also available whenever you need to talk.",

    "I'm here for you. Whether you want to vent, celebrate a win, or just chat, this is a safe space. " +
    "If anything comes up that feels difficult, don't hesitate to reach out to your supervisor or care team. " +
    "You're doing the work, and that matters.",
  ],
};

// ── Medical advice deflection ──
const MEDICAL_ADVICE_PATTERNS = [
  /\b(what\s+medication|which\s+drug|prescri(be|ption)|dosage|dose|should\s+i\s+take)\b/i,
  /\b(diagnos(e|is)|what('?s| is)\s+wrong\s+with\s+me)\b/i,
  /\b(medical\s+advice|am\s+i\s+(sick|ill))\b/i,
  /\b(stop\s+taking\s+(my\s+)?meds|quit\s+(my\s+)?medication)\b/i,
];

function isMedicalAdviceRequest(text) {
  return MEDICAL_ADVICE_PATTERNS.some((p) => p.test(text));
}

function medicalDeflection() {
  return (
    "I appreciate you trusting me with that question, but I'm not able to provide medical advice or guidance on medications. " +
    "For anything medical, please reach out to your supervisor, doctor, or healthcare provider — they can give you the right guidance. " +
    "Is there anything else I can support you with today?"
  );
}

function supervisorEscalationTemplate() {
  return (
    "I'm really glad you told me — it sounds like things feel urgent right now. " +
    "I'm alerting your supervisor/care team so someone can reach out and support you. " +
    "For the next few minutes, try a small grounding step: slow breathing (inhale 4, hold 4, exhale 6) and move to a safer, calmer space if you can. " +
    "You don't have to handle this alone. Are you somewhere safe right now?"
  );
}

/**
 * Generate a template-based reply (Phase 1 fallback).
 * @param {{ emotion: string, intensity: number, risk: string }} analysis
 * @param {string} originalText
 * @returns {string}
 */
function generateTemplateReply(analysis, originalText = '') {
  if (analysis.risk === 'HIGH') return crisisTemplate();
  if (isMedicalAdviceRequest(originalText)) return medicalDeflection();

  const templates = SUPPORTIVE_TEMPLATES[analysis.emotion] || SUPPORTIVE_TEMPLATES.neutral;
  const idx = Math.floor(Math.random() * templates.length);
  return templates[idx];
}

/**
 * Generate a bot reply based on the analysis result.
 *
 * Phase 2: async — template-driven.
 *
 * @param {{ emotion: string, intensity: number, risk: string }} analysis
 * @param {string} originalText — the patient's original message
 * @param {Array<{sender: string, text: string}>} [conversationHistory] — retained for backward compatibility
 * @returns {Promise<string>} bot reply text
 */
async function generateReply(analysis, originalText = '', conversationHistory = []) {
  // 1. HIGH risk → crisis template (always, no LLM)
  if (analysis.risk === 'HIGH') {
    return crisisTemplate();
  }

  // 2. Medical advice check (always template, no LLM)
  if (isMedicalAdviceRequest(originalText)) {
    return medicalDeflection();
  }

  // 2b. Escalation flag from controller (bypass Groq)
  if (analysis.escalateToSupervisor) {
    return supervisorEscalationTemplate();
  }

  // 3. LLM / template routing
  const provider = resolveChatProvider();
  if (provider === 'GROQ') {
    try {
      return await generateGroqReply(conversationHistory, originalText, analysis);
    } catch (err) {
      console.error('[ResponderService] Groq call failed, falling back to TEMPLATE:', err?.message || err);
      return generateTemplateReply(analysis, originalText);
    }
  }

  if (provider === 'LMSTUDIO') {
    try {
      return await generateLmStudioReply(conversationHistory, originalText, analysis);
    } catch (err) {
      console.error('[ResponderService] LM Studio call failed:', err?.message || err);
      const fb = (process.env.CHAT_FALLBACK_PROVIDER || 'TEMPLATE').trim().toUpperCase();
      if (fb === 'GROQ' && hasGroqKey()) {
        try {
          return await generateGroqReply(conversationHistory, originalText, analysis);
        } catch (gErr) {
          console.error('[ResponderService] Groq fallback failed:', gErr?.message || gErr);
        }
      }
      return generateTemplateReply(analysis, originalText);
    }
  }

  if ((process.env.CHAT_PROVIDER || '').trim().toUpperCase() === 'GROQ' && !hasGroqKey()) {
    console.warn('[ResponderService] CHAT_PROVIDER=GROQ but GROQ_API_KEY is missing — using templates.');
  }

  return generateTemplateReply(analysis, originalText);
}

module.exports = {
  generateReply,
  generateTemplateReply,
  crisisTemplate,
  medicalDeflection,
  supervisorEscalationTemplate,
};
