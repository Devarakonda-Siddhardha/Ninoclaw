const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");
const { URL } = require("url");
const QRCode = require("qrcode");
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require("@whiskeysockets/baileys");

const PORT = Number(process.env.WHATSAPP_BAILEYS_PORT || process.env.WHATSAPP_BRIDGE_PORT || 3001);
const TOKEN = (process.env.WHATSAPP_BRIDGE_TOKEN || "").trim();
const ROOT_DIR = __dirname;
const DATA_DIR = path.join(ROOT_DIR, "data");

fs.mkdirSync(DATA_DIR, { recursive: true });

const sessions = new Map();

function sessionDir(name) {
  return path.join(DATA_DIR, name);
}

function configPath(name) {
  return path.join(sessionDir(name), "config.json");
}

function authDir(name) {
  return path.join(sessionDir(name), "auth");
}

function ensureSessionState(name) {
  if (!sessions.has(name)) {
    sessions.set(name, {
      name,
      status: "idle",
      sock: null,
      qrText: "",
      qrBase64: "",
      qrPath: path.join(sessionDir(name), "qr.png"),
      config: loadSessionConfig(name) || {
        name,
        config: { webhooks: [] },
      },
      desired: false,
      reconnectTimer: null,
    });
  }
  return sessions.get(name);
}

function loadSessionConfig(name) {
  try {
    const raw = fs.readFileSync(configPath(name), "utf8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveSessionConfig(name, cfg) {
  fs.mkdirSync(sessionDir(name), { recursive: true });
  fs.writeFileSync(configPath(name), JSON.stringify(cfg, null, 2));
}

function listKnownSessions() {
  const names = new Set(sessions.keys());
  for (const entry of fs.readdirSync(DATA_DIR, { withFileTypes: true })) {
    if (entry.isDirectory() && fs.existsSync(configPath(entry.name))) {
      names.add(entry.name);
    }
  }
  return Array.from(names).sort();
}

function sessionSummary(name) {
  const state = ensureSessionState(name);
  return {
    name,
    status: state.status,
    connected: state.status === "working",
    webhooks: state.config?.config?.webhooks || [],
  };
}

function getTextFromMessage(message) {
  if (!message) return "";
  return (
    message.conversation ||
    message.extendedTextMessage?.text ||
    message.imageMessage?.caption ||
    message.videoMessage?.caption ||
    message.documentMessage?.caption ||
    ""
  );
}

function authOk(req) {
  if (!TOKEN) return true;
  const headerToken =
    req.headers["x-api-key"] ||
    (req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  return String(headerToken || "").trim() === TOKEN;
}

function sendJson(res, code, payload) {
  res.writeHead(code, { "Content-Type": "application/json" });
  res.end(JSON.stringify(payload));
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf8") || "{}";
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

async function postWebhook(target, payload, customHeaders = []) {
  if (!target) return;
  const url = new URL(target);
  const headers = { "Content-Type": "application/json" };
  for (const item of customHeaders || []) {
    if (item?.name) headers[item.name] = item.value || "";
  }
  const body = JSON.stringify(payload);
  const client = url.protocol === "https:" ? https : http;
  await new Promise((resolve) => {
    const req = client.request(
      {
        method: "POST",
        hostname: url.hostname,
        port: url.port || (url.protocol === "https:" ? 443 : 80),
        path: `${url.pathname}${url.search}`,
        headers: {
          ...headers,
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        res.resume();
        res.on("end", resolve);
      }
    );
    req.on("error", resolve);
    req.write(body);
    req.end();
  });
}

async function emitWebhook(name, payload) {
  const state = ensureSessionState(name);
  const webhooks = state.config?.config?.webhooks || [];
  for (const hook of webhooks) {
    await postWebhook(hook.url, payload, hook.customHeaders);
  }
}

async function updateQr(state, qrText) {
  state.qrText = qrText || "";
  if (!qrText) {
    state.qrBase64 = "";
    try {
      fs.unlinkSync(state.qrPath);
    } catch {}
    return;
  }
  const dataUrl = await QRCode.toDataURL(qrText, { margin: 1, width: 512 });
  state.qrBase64 = dataUrl.replace(/^data:image\/png;base64,/, "");
  fs.mkdirSync(path.dirname(state.qrPath), { recursive: true });
  fs.writeFileSync(state.qrPath, Buffer.from(state.qrBase64, "base64"));
}

async function connectSession(name, isReconnect = false) {
  const state = ensureSessionState(name);
  if (state.sock && state.status === "working") {
    return state;
  }
  if (state.reconnectTimer) {
    clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }

  state.desired = true;
  state.status = isReconnect ? "reconnecting" : "starting";
  fs.mkdirSync(authDir(name), { recursive: true });
  const auth = await useMultiFileAuthState(authDir(name));
  const sock = makeWASocket({
    auth: auth.state,
    printQRInTerminal: true,
    browser: ["Ninoclaw", "Desktop", "1.0.0"],
  });
  state.sock = sock;

  sock.ev.on("creds.update", auth.saveCreds);
  sock.ev.on("connection.update", async (update) => {
    if (update.qr) {
      state.status = "qr";
      await updateQr(state, update.qr);
      await emitWebhook(name, {
        event: "session.status",
        payload: { status: "qr", session: name },
      });
    }

    if (update.connection === "open") {
      state.status = "working";
      await updateQr(state, "");
      await emitWebhook(name, {
        event: "session.status",
        payload: { status: "working", session: name },
      });
    }

    if (update.connection === "close") {
      state.sock = null;
      const code = update.lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      state.status = loggedOut ? "logged_out" : "disconnected";
      await emitWebhook(name, {
        event: "session.status",
        payload: { status: state.status, session: name },
      });
      if (state.desired && !loggedOut) {
        state.reconnectTimer = setTimeout(() => {
          connectSession(name, true).catch(() => {});
        }, 3000);
      }
    }
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages || []) {
      if (!msg?.message || msg.key?.fromMe) continue;
      const body = getTextFromMessage(msg.message);
      if (!body) continue;
      await emitWebhook(name, {
        event: "message",
        payload: {
          from: msg.key.remoteJid || "",
          body,
          id: {
            _serialized: msg.key.id || "",
            id: msg.key.id || "",
          },
          fromMe: false,
        },
      });
    }
  });

  return state;
}

async function stopSession(name) {
  const state = ensureSessionState(name);
  state.desired = false;
  if (state.reconnectTimer) {
    clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }
  if (state.sock) {
    try {
      await state.sock.end();
    } catch {}
    try {
      state.sock.ws.close();
    } catch {}
  }
  state.sock = null;
  state.status = "stopped";
  return state;
}

async function sendText(name, chatId, text) {
  const state = ensureSessionState(name);
  if (!state.sock || state.status !== "working") {
    throw new Error("Session is not connected yet.");
  }
  await state.sock.sendMessage(chatId, { text });
}

function routeParts(url) {
  return url.pathname.split("/").filter(Boolean);
}

const server = http.createServer(async (req, res) => {
  if (!authOk(req)) {
    return sendJson(res, 401, { error: "Unauthorized" });
  }

  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  const parts = routeParts(url);

  try {
    if (req.method === "GET" && url.pathname === "/health") {
      return sendJson(res, 200, { status: "ok", service: "ninoclaw-baileys-bridge" });
    }

    if (req.method === "GET" && url.pathname === "/api/sessions") {
      return sendJson(res, 200, listKnownSessions().map(sessionSummary));
    }

    if (req.method === "POST" && url.pathname === "/api/sessions") {
      const body = await readJson(req);
      const name = String(body.name || "ninoclaw").trim() || "ninoclaw";
      saveSessionConfig(name, body);
      const state = ensureSessionState(name);
      state.config = body;
      return sendJson(res, 200, sessionSummary(name));
    }

    if (req.method === "PUT" && parts[0] === "api" && parts[1] === "sessions" && parts[2]) {
      const name = decodeURIComponent(parts[2]);
      const body = await readJson(req);
      const payload = { ...body, name };
      saveSessionConfig(name, payload);
      const state = ensureSessionState(name);
      state.config = payload;
      return sendJson(res, 200, sessionSummary(name));
    }

    if (req.method === "POST" && parts[0] === "api" && parts[1] === "sessions" && parts[2] && parts[3] === "start") {
      const name = decodeURIComponent(parts[2]);
      if (!loadSessionConfig(name)) {
        const payload = { name, config: { webhooks: [] } };
        saveSessionConfig(name, payload);
        ensureSessionState(name).config = payload;
      }
      await connectSession(name);
      return sendJson(res, 200, sessionSummary(name));
    }

    if (req.method === "POST" && parts[0] === "api" && parts[1] === "sessions" && parts[2] && parts[3] === "stop") {
      const name = decodeURIComponent(parts[2]);
      await stopSession(name);
      return sendJson(res, 200, sessionSummary(name));
    }

    if (req.method === "GET" && url.pathname === "/api/screenshot") {
      const name = String(url.searchParams.get("session") || "ninoclaw").trim() || "ninoclaw";
      const state = ensureSessionState(name);
      if (!state.qrBase64) {
        return sendJson(res, 404, { error: "QR not ready yet" });
      }
      return sendJson(res, 200, { data: state.qrBase64 });
    }

    if (req.method === "POST" && url.pathname === "/api/sendText") {
      const body = await readJson(req);
      const name = String(body.session || "ninoclaw").trim() || "ninoclaw";
      const chatId = String(body.chatId || "").trim();
      const text = String(body.text || "").trim();
      if (!chatId || !text) {
        return sendJson(res, 400, { error: "chatId and text are required" });
      }
      await sendText(name, chatId, text);
      return sendJson(res, 200, { ok: true });
    }

    return sendJson(res, 404, { error: "Not found" });
  } catch (error) {
    return sendJson(res, 500, { error: error.message || String(error) });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Ninoclaw Baileys bridge listening on http://127.0.0.1:${PORT}`);
});
