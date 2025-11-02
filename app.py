# ==========================================
# 💙 EOERWAY AI Therapy v3.0-global
# (Chatbot Only + Auto Language + Emotion Log)
# ==========================================

import os, uuid, json, time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from deep_translator import GoogleTranslator
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import matplotlib.pyplot as plt

# ---------------------------
# Streamlit Config
# ---------------------------
st.set_page_config(page_title="💙 EOERWAY AI Therapy", layout="wide")

load_dotenv()
APP_VERSION = "v3.0-global"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 4
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
ADMIN_KEYS = ["4321"]

# ---------------------------
# AdSense endpoint
# ---------------------------
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

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
# Global Session
# ---------------------------
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ---------------------------
# CSS
# ---------------------------
st.markdown("""
<style>
html, body, [class*="css"] { font-size:18px; }
.user-bubble {
  background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;margin:8px 0;
  display:inline-block;box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble {
  font-size:20px;line-height:1.8;border-radius:16px;padding:16px 20px;margin:10px 0;
  background:rgba(15,15,30,.85);color:#fff;
  border:2px solid transparent;border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;animation:neon 1.6s ease-in-out infinite alternate;
  white-space:pre-wrap;
}
@keyframes neon { from{box-shadow:0 0 8px #ffaa00;} to{box-shadow:0 0 22px #ffcc33;} }
.status {
  font-size:15px;padding:8px 12px;border-radius:10px;display:inline-block;margin-bottom:8px;
  background:rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# User Defaults
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
    st.session_state.update({k: snap.to_dict().get(k, v) for k, v in defaults.items()})
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ---------------------------
# Helper: Translation + Emotion
# ---------------------------
def detect_language(text):
    try:
        return GoogleTranslator(source='auto', target='en').detect(text)
    except:
        return "en"

def translate_to_en(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except:
        return text

def translate_from_en(text, lang):
    try:
        return GoogleTranslator(source='en', target=lang).translate(text)
    except:
        return text

def analyze_emotion(text):
    sad = sum(text.lower().count(k) for k in ["sad", "tired", "lonely", "무기력", "슬퍼", "외로"])
    happy = sum(text.lower().count(k) for k in ["happy", "love", "기뻐", "좋아", "감사"])
    return max(0, min(100, 50 + (happy - sad) * 10))

# ---------------------------
# Emotion Graph
# ---------------------------
def draw_emotion_graph(uid):
    docs = db.collection("emotions").where("uid", "==", uid).order_by("time").limit(15).stream()
    times, scores = [], []
    for d in docs:
        data = d.to_dict()
        times.append(data["time"][-8:])
        scores.append(data["score"])
    if scores:
        fig, ax = plt.subplots(figsize=(6,3))
        ax.plot(times, scores, marker="o")
        ax.set_ylim(0,100)
        ax.set_title("💗 Emotion History")
        st.pyplot(fig)
    else:
        st.info("No emotion data yet 💫")

# ---------------------------
# Title
# ---------------------------
st.title("💙 EOERWAY AI Therapy v3.0")
st.caption("🌍 Global AI Friend that listens with warmth")

# ---------------------------
# Status
# ---------------------------
if st.session_state.get("is_paid"):
    plan = "💎 Premium User"
    left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
else:
    plan = "🌱 Free Trial"
    left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
st.markdown(f"<div class='status'>{plan} — Remaining {max(left,0)} chats</div>", unsafe_allow_html=True)

# ---------------------------
# Reset Counter
# ---------------------------
now = datetime.utcnow()
last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
    persist_user({"usage_count": 0, "last_reset": now.isoformat()})
    st.info("⏰ Free sessions reset every 4 hours!")

# ---------------------------
# Chat Input
# ---------------------------
user_input = st.chat_input("Type how you feel... / 지금 기분을 말해보세요 💬")
if not user_input:
    st.stop()

st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

# ---------------------------
# Detect Language + Emotion
# ---------------------------
lang_code = detect_language(user_input)
emotion_score = analyze_emotion(user_input)
db.collection("emotions").add({
    "uid": USER_ID,
    "text": user_input,
    "score": emotion_score,
    "time": datetime.utcnow().isoformat()
})

# ---------------------------
# AI Reply (with auto translation)
# ---------------------------
system_prompt = (
    "You are a warm, empathetic counselor. "
    "Comfort users in 6–9 sentences with gentle empathy. "
    "Encourage small self-care actions and avoid medical advice."
)
translated_input = translate_to_en(user_input)

try:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": translated_input}
        ],
        temperature=0.8,
        max_tokens=500
    )
    answer = resp.choices[0].message.content
except:
    answer = "I'm here with you. Let's take a slow breath together."

translated_output = translate_from_en(answer, lang_code)

# ---------------------------
# Show Bot Message
# ---------------------------
st.markdown(f"<div class='bot-bubble'>{translated_output}💫</div>", unsafe_allow_html=True)

# Save Chat
db.collection("chats").add({
    "uid": USER_ID,
    "input": user_input,
    "reply": translated_output,
    "lang": lang_code,
    "created_at": datetime.utcnow().isoformat()
})

# ---------------------------
# Usage Update
# ---------------------------
if st.session_state.get("is_paid"):
    persist_user({"remaining_paid_uses": max(0, st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1)})
else:
    persist_user({"usage_count": st.session_state["usage_count"] + 1})

# ---------------------------
# Emotion History
# ---------------------------
with st.expander("💗 감정 히스토리 보기 / View Emotion History"):
    draw_emotion_graph(USER_ID)

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align:center; opacity:0.9'>
    <p>💌 For premium activation, send your payment screenshot to <b style='color:#FFD966;'>mwiby91@gmail.com</b> or KakaoTalk ID <b>jeuspo</b></p>
    <p>🌍 Version {APP_VERSION} • Built with 💙 Streamlit + OpenAI</p>
    </div>
    """,
    unsafe_allow_html=True
)
