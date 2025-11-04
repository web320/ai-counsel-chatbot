# ==========================================
# 💙 EOERWAY AI Therapy v2.8
# (Default: English, Small Language Toggle Button + Visitor Counter)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.8"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 4
ADMIN_KEYS = ["4321"]

# ================= ads.txt (for AdSense) =================
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ================= OpenAI (LLM) =================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ================= Firebase =================
def _firebase_config():
    raw = st.secrets.get("firebase")
    if raw is None:
        raise RuntimeError("Secrets에 [firebase] 설정이 없습니다.")
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw)

if not firebase_admin._apps:
    cred = credentials.Certificate(_firebase_config())
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ================= Query Params / UID =================
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= Language State =================
if "lang" not in st.session_state:
    st.session_state["lang"] = "English 🇺🇸"

col1, col2 = st.columns([5, 1])
with col2:
    lang_choice = st.radio(
        " ",
        ["English 🇺🇸", "한국어 🇰🇷"],
        horizontal=True,
        label_visibility="collapsed",
        index=0 if st.session_state["lang"] == "English 🇺🇸" else 1
    )
st.session_state["lang"] = lang_choice
language = st.session_state["lang"]

# ================= Text by Language =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something 💬",
        "usedup": "🌙 You’ve used all 7 free sessions today!",
        "reset": "⏰ Free sessions reset! (Every 4 hours)",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "payment_title": "💳 Payment Guide",
        "feedback_title": "💌 Service Feedback",
        "chat_return": "💬 Back to Chat",
        "chat_button": "💳 Open Payment & Feedback",
        "status_left": "remaining",
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": "🌙 오늘의 무료 상담 7회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (4시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown(
    """
<style>
html, body, [class*="css"] { font-size: 18px; }
.user-bubble {
  background:#b91c1c; color:#fff; border-radius:14px;
  padding:10px 18px; margin:8px 0; display:inline-block;
  box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble {
  font-size:21px; line-height:1.8; border-radius:16px;
  padding:16px 20px; margin:10px 0; background:rgba(15,15,30,.85);
  color:#fff; border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00; animation:neon 1.6s ease-in-out infinite alternate;
  word-break:break-word; white-space:pre-wrap;
}
@keyframes neon { from { box-shadow:0 0 8px #ffaa00; } to { box-shadow:0 0 22px #ffcc33; } }
.status {
  font-size:15px; padding:8px 12px; border-radius:10px;
  display:inline-block; margin-bottom:8px; background:rgba(255,255,255,.06);
}
</style>
""",
    unsafe_allow_html=True
)

# ================= Firestore Defaults / User State =================
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

# ================= Visitor Counter =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_ref = db.collection("stats").document("total")
    daily_ref = db.collection("stats").document(today)

    # 총 방문자 수 증가
    total_doc = total_ref.get()
    if total_doc.exists:
        total_ref.update({"count": firestore.Increment(1)})
    else:
        total_ref.set({"count": 1})

    # 하루 방문자 수 증가
    daily_doc = daily_ref.get()
    if daily_doc.exists:
        daily_ref.update({"count": firestore.Increment(1)})
    else:
        daily_ref.set({"count": 1})

def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_doc = db.collection("stats").document("total").get()
    daily_doc = db.collection("stats").document(today).get()
    total = total_doc.to_dict().get("count", 0) if total_doc.exists else 0
    daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
    return total, daily

# 🔹 모든 사용자(너 포함) 방문 시 1회 증가
# 세션마다 최초 1회만 카운트되도록 설정
if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

# 🔹 방문자 수 가져오기
total_visits, daily_visits = get_visit_counts()

# 🔹 방문자 통계창 항상 표시 (관리자 포함)
st.markdown(
    f"""
    <div style="padding:14px;margin-bottom:14px;border-radius:12px;
                background:rgba(255,255,255,.07);
                color:#fff;font-size:18px;line-height:1.6;">
        🌍 <b>Total Visitors:</b> {total_visits:,}명<br>
        ☀️ <b>Today's Visitors:</b> {daily_visits:,}명
    </div>
    """,
    unsafe_allow_html=True
)


# ================= AI / Chat / Payment Functions =================
# (기존 코드 전부 동일하게 아래 유지)
# --- 이후 부분 그대로 기존 코드 복사 ---
# render_chat_page(), render_payment_and_feedback(), stream_reply() 등 유지
# ================= Sidebar =================
# ...
# ================= Main Render =================
# ...


