/**
 * Chat Controller — Phase 2
 *
 * Handles patient chatbot interactions:
 *   POST /api/chat/send   — send message, get analysis + bot reply (now async LLM-powered)
 *   GET  /api/chat/history — retrieve conversation history for logged-in patient
 */

const ChatMessage = require('../models/ChatMessage');
const ChatAnalysis = require('../models/ChatAnalysis');
const ChatAlert = require('../models/ChatAlert');
const analyzer = require('../services/analyzerService');
const responder = require('../services/responderService');

const SUPERVISOR_ESCALATION_PATTERNS = [
  // Overdose / self-harm / suicide intent (extra safety net; analyzer usually catches these as HIGH)
  /\b(overdos(e|ed|ing)|take\s+too\s+many\s+(pills|tablets|meds))\b/i,
  /\b(kill\s*(my)?self|suicid(e|al)|want\s+to\s+die|end\s+(my\s+)?life)\b/i,
  /\b(self[- ]?harm|cut(ting)?\s*(my)?self|hurt(ing)?\s*(my)?self)\b/i,

  // Relapse planning / imminent use (may still be MED by classifier)
  /\b(plan\s+to\s+(use|get\s+high|drink|smoke)|about\s+to\s+(use|get\s+high|drink|smoke)|going\s+to\s+(use|get\s+high|drink|smoke))\b/i,
  /\b(buy(ing)?\s+drugs?|score(ing)?|meet(ing)?\s+(my\s+)?dealer)\b/i,

  // Severe crisis language
  /\b(can'?t\s+cope|unbearable|falling\s+apart|out\s+of\s+control|i\s+can'?t\s+do\s+this)\b/i,
];

function shouldEscalateToSupervisor(text) {
  if (!text || typeof text !== 'string') return false;
  return SUPERVISOR_ESCALATION_PATTERNS.some((p) => p.test(text));
}

/**
 * POST /api/chat/send
 * Body: { text: string }
 * Auth: Patient only
 */
const sendMessage = async (req, res) => {
  try {
    // Derive patientId from auth (supports both middleware patterns)
    const patientId = req.user?.userId || req.user?._id;
    if (!patientId) {
      return res.status(401).json({ error: 'Authentication required.' });
    }

    // ── 1. Validate input ──
    const rawText = req.body?.text;
    if (!rawText || typeof rawText !== 'string') {
      return res.status(400).json({ error: 'Message text is required.' });
    }

    const text = rawText.trim();
    if (text.length === 0) {
      return res.status(400).json({ error: 'Message cannot be empty.' });
    }
    if (text.length > 1000) {
      return res.status(400).json({ error: 'Message is too long (max 1000 characters).' });
    }

    // ── 2. Save patient message ──
    const patientMessage = await ChatMessage.create({
      patientId,
      sender: 'patient',
      text,
    });

    // ── 3. Run analyzer ──
    const analysisResult = await analyzer.analyze(text);

    // ── 4. Save analysis ──
    const analysis = await ChatAnalysis.create({
      patientId,
      messageId: patientMessage._id,
      emotion: analysisResult.emotion,
      intensity: analysisResult.intensity,
      risk: analysisResult.risk,
      summary: analysisResult.summary,
      reasons: analysisResult.reasons,
    });

    // ── 5. HIGH risk or escalation patterns → create alert + push to supervisors ──
    let alert = null;
    const escalationMatch = shouldEscalateToSupervisor(text);
    const shouldAlertSupervisor = analysisResult.risk === 'HIGH' || escalationMatch;

    if (shouldAlertSupervisor) {
      alert = await ChatAlert.create({
        patientId,
        analysisId: analysis._id,
        messageId: patientMessage._id,
        risk: analysisResult.risk,
        topEmotion: analysisResult.emotion,
        intensity: analysisResult.intensity,
        summary: analysisResult.summary,
        triggerText: text.substring(0, 300),
      });

      // Emit real-time alert to supervisors via Socket.io
      const io = req.app.get('io') || global.io;
      if (io) {
        // Populate patient name for supervisor display
        const User = require('../models/User');
        const patient = await User.findById(patientId).select('firstName lastName email').lean();

        const alertPayload = {
          _id: alert._id,
          patientId,
          patientName: patient ? `${patient.firstName || ''} ${patient.lastName || ''}`.trim() : 'Unknown',
          patientEmail: patient?.email || '',
          risk: alert.risk,
          topEmotion: alert.topEmotion,
          intensity: alert.intensity,
          summary: alert.summary,
          triggerText: alert.triggerText,
          status: alert.status,
          createdAt: alert.createdAt,
        };

        // Broadcast to all connected supervisors
        io.emit('new_alert', alertPayload);

        // Also try sending to the specific supervisor assigned to this patient
        if (patient) {
          const fullPatient = await User.findById(patientId).select('assignedSupervisor').lean();
          if (fullPatient?.assignedSupervisor) {
            io.to(`user:${fullPatient.assignedSupervisor}`).emit('new_alert', alertPayload);
          }
        }
      }
    }

    // ── 6. Fetch recent conversation history for LLM context (last 10 messages) ──
    const recentHistory = await ChatMessage.find({ patientId })
      .sort({ timestamp: -1 })
      .limit(4)
      .lean();
    // Reverse to oldest-first for chronological context
    recentHistory.reverse();

    // ── 7. Generate bot reply ──
    const replyContext = {
      ...analysisResult,
      // If the controller triggered a supervisor alert for a non-HIGH message,
      // bypass Groq and return a safer escalation template.
      escalateToSupervisor: analysisResult.risk !== 'HIGH' && shouldAlertSupervisor,
    };

    const replyText = await responder.generateReply(replyContext, text, recentHistory);

    // ChatMessage schema max length 1000 — truncate so Mongoose save never fails silently upstream
    const botText =
      typeof replyText === 'string' && replyText.length > 1000
        ? `${replyText.slice(0, 997)}...`
        : replyText || 'I’m here with you. Could you say a bit more about what’s on your mind?';

    // ── 8. Save bot message ──
    const botMessage = await ChatMessage.create({
      patientId,
      sender: 'bot',
      text: botText,
    });

    // ── 9. Return response ──
    return res.status(200).json({
      patientMessage,
      analysis,
      botMessage,
      alert: alert || undefined,
    });
  } catch (err) {
    console.error('[ChatController] sendMessage error:', err);
    return res.status(500).json({ error: 'Something went wrong. Please try again.' });
  }
};

/**
 * GET /api/chat/history
 * Returns all chat messages for the logged-in patient, sorted by timestamp asc.
 */
const getHistory = async (req, res) => {
  try {
    const patientId = req.user?.userId || req.user?._id;
    if (!patientId) {
      return res.status(401).json({ error: 'Authentication required.' });
    }

    const messages = await ChatMessage.find({ patientId })
      .sort({ timestamp: 1 })
      .lean();

    return res.status(200).json({ messages });
  } catch (err) {
    console.error('[ChatController] getHistory error:', err);
    return res.status(500).json({ error: 'Could not load chat history.' });
  }
};

module.exports = { sendMessage, getHistory };
