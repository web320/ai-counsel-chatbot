# ==========================================
# 💙 EOERWAY AI Therapy v5.2-Optimized
# (No External Graph Modules, GitHub Deploy)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="💙 EOERWAY AI Therapy", layout="wide")
load_dotenv()

APP_VERSION = "v5.2-Optimized"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 4
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
ADMIN_KEYS = ["4321"]

# ---------------------------
# FIREBASE INIT
# ---------------------------
def _firebase_config():
    raw = st.secrets.get("firebase")
    if isinstance(raw, str): return json.loads(raw)
    return dict(raw)

if not firebase_admin._apps:
    cred = credentials.Certificate(_firebase_config())
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------------------
# OPENAI INIT
# ---------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# USER IDENTIFICATION
# ---------------------------
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ---------------------------
# ads.txt ENDPOINT
# ---------------------------
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ---------------------------
# CSS STYLE
# ---------------------------
st.markdown("""
<style>
html, body, [class*="css"] { font-size:18px; }
.user-bubble { background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;
margin:8px 0;display:inline-block;box-shadow:0 0 10px rgba(255,0,0,0.3);}
.bot-bubble { font-size:20px;line-height:1.8;border-radius:16px;padding:16px 20px;
background:rgba(15,15,30,.85);color:#fff;border:2px solid transparent;
border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
box-shadow:0 0 12px #ffaa00;animation:neon 1.6s ease-in-out infinite alternate;
white-space:pre-wrap;word-break:break-word;}
@keyframes neon { from{box-shadow:0 0 8px #ffaa00;} to{box-shadow:0 0 22px #ffcc33;} }
.status { font-size:15px;padding:8px 12px;border-radius:10px;display:inline-block;
margin-bottom:8px;background:rgba(255,255,255,.06);}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# FIRESTORE DEFAULTS
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
# HELPER FUNCTIONS
# ---------------------------
def detect_language(text):
    if any(k in text for k in ["요", "안녕", "사랑해", "입니다"]):
        return "ko"
    return "en"

def analyze_emotion(text):
    sad = sum(text.lower().count(k) for k in ["sad","lonely","tired","무기력","외로","슬퍼"])
    happy = sum(text.lower().count(k) for k in ["happy","love","기뻐","감사","좋아"])
    score = max(0, min(100, 50 + (happy - sad) * 10))
    emoji = "😢" if score < 40 else "🙂" if score < 70 else "😊"
    color = "linear-gradient(90deg,#ff3366,#ffaa00)" if score < 40 else "linear-gradient(90deg,#66ccff,#33cc33)"
    return score, emoji, color

def show_emotion_bar(score, emoji, color):
    st.markdown(
        f"<div style='background:{color};border-radius:10px;padding:8px 14px;width:{score}%;color:#fff'>{emoji} Emotion Score: {score}</div>",
        unsafe_allow_html=True
    )

# ---------------------------
# PAGE TITLE
# ---------------------------
st.title("💙 EOERWAY AI Therapy v5.2")
st.caption("🌍 Optimized Emotional AI Friend – Fast, Warm, and Reliable")

# ---------------------------
# STATUS BAR
# ---------------------------
if st.session_state.get("is_paid"):
    plan = "💎 Premium User"
    left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
else:
    plan = "🌱 Free Trial"
    left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
st.markdown(f"<div class='status'>{plan} — Remaining {max(left,0)} chats</div>", unsafe_allow_html=True)

# ---------------------------
# RESET COUNTER
# ---------------------------
now = datetime.utcnow()
last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
    persist_user({"usage_count": 0, "last_reset": now.isoformat()})
    st.info("⏰ Free sessions reset every 4 hours!")

# ---------------------------
# CHAT
# ---------------------------
user_input = st.chat_input("How are you feeling right now? / 지금 어떤 기분이세요? 💬")
if not user_input:
    st.stop()

st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

lang = detect_language(user_input)
emotion_score, emoji, color = analyze_emotion(user_input)
show_emotion_bar(emotion_score, emoji, color)

# ---------------------------
# AI RESPONSE
# ---------------------------
system_prompt = (
    "You are EOERWAY, a compassionate AI counselor. "
    "Respond warmly in 6–9 sentences, use gentle tone, avoid medical advice."
)

try:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_input}
        ],
        temperature=0.8,
        max_tokens=500
    )
    answer = resp.choices[0].message.content
except:
    answer = "I'm here with you. Let's breathe slowly together 💙"

st.markdown(f"<div class='bot-bubble'>{answer}💫</div>", unsafe_allow_html=True)

# ---------------------------
# FIRESTORE SAVE
# ---------------------------
db.collection("chats").add({
    "uid": USER_ID,
    "input": user_input,
    "reply": answer,
    "lang": lang,
    "emotion_score": emotion_score,
    "created_at": datetime.utcnow().isoformat()
})

if st.session_state.get("is_paid"):
    persist_user({"remaining_paid_uses": max(0, st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1)})
else:
    persist_user({"usage_count": st.session_state["usage_count"] + 1})

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align:center;opacity:0.9'>
    <p>💎 Upgrade: <a href="{PAYPAL_URL}" target="_blank">PayPal $3</a><br>
    Send screenshot to <b style='color:#FFD966;'>mwiby91@gmail.com</b> or KakaoTalk ID <b>jeuspo</b></p>
    <p>🌐 Version {APP_VERSION} • Built with 💙 Streamlit + OpenAI</p>
    </div>
    """,
    unsafe_allow_html=True
)
