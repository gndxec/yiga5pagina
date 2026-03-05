import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request, g, Response
from twilio.rest import Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "conversations.db")

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_id TEXT UNIQUE NOT NULL,
            contact_name TEXT,
            last_message TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            body TEXT NOT NULL,
            twilio_sid TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()
    db.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_wa_id(wa_identifier: str) -> str:
    if not wa_identifier:
        return ""
    normalized = wa_identifier.replace("whatsapp:", "").strip()
    return normalized


def upsert_conversation(wa_id: str, contact_name: str, last_message: str) -> None:
    db = get_db()
    timestamp = now_iso()
    db.execute(
        """
        INSERT INTO conversations (wa_id, contact_name, last_message, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(wa_id) DO UPDATE SET
          contact_name = COALESCE(excluded.contact_name, conversations.contact_name),
          last_message = excluded.last_message,
          updated_at = excluded.updated_at
        """,
        (wa_id, contact_name, last_message, timestamp),
    )
    db.commit()


def save_message(wa_id: str, direction: str, body: str, twilio_sid: str | None) -> None:
    db = get_db()
    db.execute(
        """
        INSERT INTO messages (wa_id, direction, body, twilio_sid, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (wa_id, direction, body, twilio_sid, now_iso()),
    )
    db.commit()


def twilio_client() -> Client:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not account_sid or not auth_token:
        raise RuntimeError("Faltan TWILIO_ACCOUNT_SID y/o TWILIO_AUTH_TOKEN")
    return Client(account_sid, auth_token)


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/webhook/twilio/whatsapp")
def inbound_whatsapp_webhook():
    sender = normalize_wa_id(request.form.get("From", ""))
    profile_name = request.form.get("ProfileName", "Cliente")
    body = (request.form.get("Body") or "").strip()
    message_sid = request.form.get("MessageSid")

    if sender and body:
        save_message(sender, "inbound", body, message_sid)
        upsert_conversation(sender, profile_name, body)

    twiml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>"""
    return Response(twiml, mimetype="application/xml")


@app.get("/api/conversations")
def list_conversations():
    db = get_db()
    rows = db.execute(
        """
        SELECT wa_id, contact_name, last_message, updated_at
        FROM conversations
        ORDER BY updated_at DESC
        """
    ).fetchall()
    return jsonify([
        {
            "wa_id": row["wa_id"],
            "contact_name": row["contact_name"] or "Cliente",
            "last_message": row["last_message"] or "",
            "updated_at": row["updated_at"],
        }
        for row in rows
    ])


@app.get("/api/conversations/<wa_id>/messages")
def get_messages(wa_id: str):
    normalized_wa_id = normalize_wa_id(wa_id)
    db = get_db()
    rows = db.execute(
        """
        SELECT id, wa_id, direction, body, twilio_sid, created_at
        FROM messages
        WHERE wa_id = ?
        ORDER BY created_at ASC
        """,
        (normalized_wa_id,),
    ).fetchall()

    return jsonify([
        {
            "id": row["id"],
            "wa_id": row["wa_id"],
            "direction": row["direction"],
            "body": row["body"],
            "twilio_sid": row["twilio_sid"],
            "created_at": row["created_at"],
        }
        for row in rows
    ])


@app.post("/api/conversations/<wa_id>/reply")
def reply_to_conversation(wa_id: str):
    normalized_wa_id = normalize_wa_id(wa_id)
    payload = request.get_json(silent=True) or {}
    message_text = (payload.get("message") or "").strip()

    if not message_text:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400

    from_whatsapp = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")
    if not from_whatsapp:
        return jsonify({"error": "Falta TWILIO_WHATSAPP_NUMBER"}), 500

    try:
        client = twilio_client()
        sent = client.messages.create(
            body=message_text,
            from_=from_whatsapp,
            to=f"whatsapp:{normalized_wa_id}",
        )
    except Exception as error:
        return jsonify({"error": f"No se pudo enviar mensaje: {error}"}), 500

    save_message(normalized_wa_id, "outbound", message_text, sent.sid)
    upsert_conversation(normalized_wa_id, "Cliente", message_text)

    return jsonify({"ok": True, "sid": sent.sid})


@app.get("/inbox")
def inbox_page():
    return """
<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Bandeja WhatsApp</title>
  <style>
    body { margin: 0; font-family: Inter, Arial, sans-serif; background: #0f0b1f; color: #f5f2ff; }
    .layout { display: grid; grid-template-columns: 320px 1fr; min-height: 100vh; }
    .sidebar { border-right: 1px solid #2b2148; padding: 16px; }
    .chat { padding: 16px; display: flex; flex-direction: column; }
    .title { margin: 0 0 12px; font-size: 1.1rem; }
    .contact { background: #1a1430; border: 1px solid #322559; border-radius: 10px; padding: 10px; margin-bottom: 8px; cursor: pointer; }
    .contact small { color: #b9a9e8; display: block; margin-top: 6px; }
    .messages { flex: 1; overflow: auto; border: 1px solid #322559; border-radius: 12px; padding: 12px; background: #130f25; }
    .msg { margin: 8px 0; max-width: 78%; padding: 10px 12px; border-radius: 12px; }
    .inbound { background: #27204a; }
    .outbound { background: #5b21b6; margin-left: auto; }
    .composer { display: flex; gap: 8px; margin-top: 12px; }
    input { flex: 1; padding: 12px; border-radius: 10px; border: 1px solid #4b3686; background: #1c1635; color: #fff; }
    button { padding: 12px 16px; border: 0; border-radius: 10px; background: #7c3aed; color: #fff; font-weight: 600; cursor: pointer; }
    @media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class=\"layout\">
    <aside class=\"sidebar\">
      <h1 class=\"title\">Conversaciones</h1>
      <div id=\"contacts\"></div>
    </aside>
    <section class=\"chat\">
      <h2 class=\"title\" id=\"active-title\">Selecciona un cliente</h2>
      <div class=\"messages\" id=\"messages\"></div>
      <form class=\"composer\" id=\"reply-form\">
        <input id=\"reply-input\" placeholder=\"Escribe una respuesta...\" />
        <button type=\"submit\">Responder</button>
      </form>
    </section>
  </div>

  <script>
    let activeWaId = "";

    const contactsEl = document.getElementById("contacts");
    const messagesEl = document.getElementById("messages");
    const activeTitleEl = document.getElementById("active-title");
    const replyFormEl = document.getElementById("reply-form");
    const replyInputEl = document.getElementById("reply-input");

    async function loadConversations() {
      const response = await fetch('/api/conversations');
      const conversations = await response.json();
      contactsEl.innerHTML = "";
      conversations.forEach((conversation) => {
        const item = document.createElement('div');
        item.className = 'contact';
        item.innerHTML = `<strong>${conversation.contact_name || 'Cliente'}</strong><small>${conversation.wa_id}</small><small>${conversation.last_message || ''}</small>`;
        item.onclick = () => selectConversation(conversation);
        contactsEl.appendChild(item);
      });
    }

    async function selectConversation(conversation) {
      activeWaId = conversation.wa_id;
      activeTitleEl.textContent = `${conversation.contact_name || 'Cliente'} (${conversation.wa_id})`;
      await loadMessages();
    }

    async function loadMessages() {
      if (!activeWaId) return;
      const response = await fetch(`/api/conversations/${encodeURIComponent(activeWaId)}/messages`);
      const messages = await response.json();
      messagesEl.innerHTML = "";
      messages.forEach((message) => {
        const bubble = document.createElement('div');
        bubble.className = `msg ${message.direction === 'outbound' ? 'outbound' : 'inbound'}`;
        bubble.textContent = message.body;
        messagesEl.appendChild(bubble);
      });
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    replyFormEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const text = replyInputEl.value.trim();
      if (!activeWaId || !text) return;
      await fetch(`/api/conversations/${encodeURIComponent(activeWaId)}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      replyInputEl.value = '';
      await loadMessages();
      await loadConversations();
    });

    setInterval(() => {
      loadConversations();
      loadMessages();
    }, 5000);

    loadConversations();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
