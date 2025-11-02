# ==========================================
# 💙 EOERWAY AI Therapy v2.9-chat-only
# (Chatbot Only Version)
# ==========================================

import os, uuid, json, time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------
# Streamlit Page Config
# ---------------------------
st.set_page_config(page_title="💙 EOERWAY AI Therapy", layout="wide")

load_dotenv()
APP_VERSION = "v2.9-chat"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
ADMIN_KEYS = ["4321"]
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50

# ---------------------------
# Firebase Setup
# ---------------------------
def _firebase_config():
    raw = st.secrets.get("firebase")
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw)

if not firebase_admin._apps:
    cred = credentials.Certificate(_firebase_config())
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------------------
# OpenAI
# ---------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# Global User Session
# ---------------------------
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ---------------------------
# AdSense txt endpoint
# ---------------------------
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ---------------------------
# CSS
# ---------------------------
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }

.user-bubble {
  background:#b91c1c;
  color:#fff;
  border-radius:14px;
  padding:10px 18px;
  margin:8px 0;
  display:inline-block;
  box-shadow:0 0 10px rgba(255,0,0,0.3);
}

.bot-bubble {
  font-size:20px;
  line-height:1.8;
  border-radius:16px;
  padding:16px 20px;
  margin:10px 0;
  background:rgba(15,15,30,.85);
  color:#fff;
  border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;
  animation:neon 1.6s ease-in-out infinite alternate;
  word-break:break-word;
  white-space:pre-wrap;
}

@keyframes neon {
  from { box-shadow:0 0 8px #ffaa00; }
  to   { box-shadow:0 0 22px #ffcc33; }
}

.status {
  font-size:15px;
  padding:8px 12px;
  border-radius:10px;
  display:inline-block;
  margin-bottom:8px;
  background:rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Default User Data
# ---------------------------
defaults = {
    "is_paid": False,
    "usage_count": 0,
    "remaining_paid_uses": 0,
    "last_reset": datetime.utcnow().isoformat()
}

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()

if snap.exists:
    data = snap.to_dict() or {}
    st.session_state.update({k: data.get(k, v) for k, v in defaults.items()})
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ---------------------------
# PAGE: Chatbot Only
# ---------------------------
st.title("💙 EOERWAY AI Therapy")
st.caption("A warm AI friend that listens and comforts your heart 🌷")

# 상태 표시 (무료 / 유료)
if st.session_state.get("is_paid"):
    plan = "💎 Premium User"
    left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
else:
    plan = "🌱 Free Trial"
    left = DAILY_FREE_LIMIT - st.session_state["usage_count"]

st.markdown(f"<div class='status'>{plan} — remaining {max(left,0)} chats</div>", unsafe_allow_html=True)

# 무료 횟수 리셋
now = datetime.utcnow()
last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
if (now - last_reset).total_seconds() / 3600 >= 4:
    persist_user({"usage_count": 0, "last_reset": now.isoformat()})
    st.info("⏰ Free sessions have been reset (every 4 hours).")

# 입력
user_input = st.chat_input("How are you feeling right now?")
if not user_input:
    st.stop()

# 사용자 버블 출력
st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

# AI 응답
try:
    system_prompt = (
        "You are a warm, empathetic counselor. "
        "Respond in 6–9 gentle sentences with care, empathy, and calm tone. "
        "Avoid medical or diagnostic advice."
    )

    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.9,
        max_tokens=700,
        stream=True,
    )

    placeholder = st.empty()
    full_text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta
        if hasattr(delta, "content") and delta.content:
            full_text += delta.content
            placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
            time.sleep(0.03)

    db.collection("chats").add({
        "uid": USER_ID,
        "input": user_input,
        "reply": full_text.strip(),
        "created_at": datetime.utcnow().isoformat()
    })

    # 사용량 차감
    if st.session_state.get("is_paid"):
        persist_user({
            "remaining_paid_uses": max(0, st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1)
        })
    else:
        persist_user({"usage_count": st.session_state["usage_count"] + 1})

except Exception as e:
    st.error("AI connection failed 💔 Please try again later.")
    st.write(e)

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align:center; opacity:0.9'>
    <p>💌 For premium activation, send your payment screenshot to <b style='color:#FFD966;'>mwiby91@gmail.com</b> or KakaoTalk ID <b>jeuspo</b></p>
    <p>🌐 Version {APP_VERSION} • Built with 💙 Streamlit + OpenAI</p>
    </div>
    """,
    unsafe_allow_html=True
)
