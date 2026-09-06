/**
 * POST /api/subscribe  —  Vercel serverless function (Node runtime).
 *
 * Accepts the newsletter form (application/x-www-form-urlencoded, or JSON)
 * and creates a contact in the Resend audience. Single opt-in: Resend's
 * Audiences API has no confirmation step, so the address is added directly.
 *
 * Secrets come only from environment variables set in Vercel:
 *   RESEND_API_KEY, RESEND_AUDIENCE_ID
 * Nothing here is ever sent to the client except ok/code/message.
 */

const RESEND_URL = 'https://api.resend.com/audiences/';
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const MAX_EMAIL_LEN = 254;

// Best-effort rate limit. Serverless instances do not share memory, so this
// bounds abuse per warm instance rather than globally; the honeypot and
// Resend's own duplicate handling do the rest.
const WINDOW_MS = 10 * 60 * 1000;
const MAX_PER_WINDOW = 5;
const hits = new Map();

function clientIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  return (Array.isArray(fwd) ? fwd[0] : (fwd || '')).split(',')[0].trim() || req.socket?.remoteAddress || 'unknown';
}

function rateLimited(ip) {
  const now = Date.now();
  const rec = hits.get(ip) || { start: now, count: 0 };
  if (now - rec.start > WINDOW_MS) { rec.start = now; rec.count = 0; }
  rec.count += 1;
  hits.set(ip, rec);
  if (hits.size > 5000) hits.clear(); // keep the map bounded on long-lived instances
  return rec.count > MAX_PER_WINDOW;
}

function parseBody(req) {
  const b = req.body;
  if (b && typeof b === 'object') return b; // Vercel already parsed form or JSON
  if (typeof b === 'string' && b.length) {
    const ct = String(req.headers['content-type'] || '');
    if (ct.includes('application/json')) { try { return JSON.parse(b); } catch (e) { return {}; } }
    return Object.fromEntries(new URLSearchParams(b));
  }
  return {};
}

function wantsJson(req) {
  const accept = String(req.headers['accept'] || '');
  return accept.includes('application/json') || req.headers['x-requested-with'] === 'fetch';
}

const MESSAGES = {
  ok: 'You are on the list. One email when we publish something worth your time.',
  exists: 'That address is already on the list.',
  invalid: 'That does not look like a valid email address.',
  rate: 'Too many attempts from this connection. Try again in a few minutes.',
  method: 'Use POST.',
  config: 'Signup is not configured on the server.',
  upstream: 'Our email service did not accept the address just now. Try again in a minute.',
};

function finish(req, res, status, code) {
  const ok = code === 'ok' || code === 'exists';
  res.setHeader('Cache-Control', 'no-store');
  if (wantsJson(req)) {
    return res.status(status).json({ ok, code, message: MESSAGES[code] });
  }
  // No-JS path: send the browser to a static page that states the outcome.
  const target = ok ? '/subscribed/' : `/subscribed/problem/?why=${encodeURIComponent(code)}`;
  res.statusCode = 303;
  res.setHeader('Location', target);
  return res.end();
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return finish(req, res, 405, 'method');
  }

  const body = parseBody(req);

  // Honeypot: real users never see or fill this field. Pretend it worked.
  if (typeof body.website === 'string' && body.website.trim() !== '') {
    return finish(req, res, 200, 'ok');
  }

  const email = String(body.email || '').trim().toLowerCase();
  if (!email || email.length > MAX_EMAIL_LEN || !EMAIL_RE.test(email)) {
    return finish(req, res, 400, 'invalid');
  }

  if (rateLimited(clientIp(req))) {
    return finish(req, res, 429, 'rate');
  }

  const key = process.env.RESEND_API_KEY;
  const audience = process.env.RESEND_AUDIENCE_ID;
  if (!key || !audience) {
    console.error('subscribe: RESEND_API_KEY or RESEND_AUDIENCE_ID is not set');
    return finish(req, res, 500, 'config');
  }

  let upstream;
  try {
    upstream = await fetch(RESEND_URL + encodeURIComponent(audience) + '/contacts', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, unsubscribed: false }),
    });
  } catch (err) {
    console.error('subscribe: network error reaching Resend', err && err.message);
    return finish(req, res, 502, 'upstream');
  }

  let data = {};
  try { data = await upstream.json(); } catch (e) { /* non-JSON body */ }

  if (upstream.ok && data && data.id) {
    return finish(req, res, 200, 'ok');
  }
  const text = JSON.stringify(data || {});
  if (upstream.status === 409 || /already|exist|duplicate/i.test(text)) {
    return finish(req, res, 200, 'exists');
  }
  console.error('subscribe: Resend rejected the request', upstream.status, text.slice(0, 300));
  return finish(req, res, 502, 'upstream');
};
