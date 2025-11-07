# ==========================================
# 💙 EOERWAY AI Therapy v3.0 (added referrer tracking)
# ==========================================

import os, uuid, json, time, random, hashlib
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v3.0"
DAILY_FREE_LIMIT = 15
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 6
ADMIN_KEYS = ["4321"]

# ================= ads.txt (for AdSense) =================
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ================= OpenAI =================
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

# ================= USER_ID =================
def get_browser_fingerprint():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx and hasattr(ctx, 'session_id'):
            return ctx.session_id
    except:
        pass

    if "browser_fingerprint" not in st.session_state:
        st.session_state["browser_fingerprint"] = str(uuid.uuid4())
    return st.session_state["browser_fingerprint"]

if "USER_ID" not in st.session_state:
    fingerprint = get_browser_fingerprint()
    hashed = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    st.session_state["USER_ID"] = f"user_{hashed}"

USER_ID = st.session_state["USER_ID"]

# ================= Visitor Counter + Referrer Tracking =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_visit_ref = db.collection("user_visits").document(USER_ID)

    try:
        user_doc = user_visit_ref.get()
        if user_doc.exists:
            return
    except:
        pass

    # 유입경로와 기기정보 수집
    referrer = st.query_params.get("ref", None)
    user_agent = st.session_state.get("user_agent", None)

    try:
        user_visit_ref.set({
            "uid": USER_ID,
            "first_visit": datetime.utcnow().isoformat(),
            "day": today,
            "referrer": referrer or "direct",
            "user_agent": user_agent or "unknown"
        })

        total_ref = db.collection("stats").document("total")
        daily_ref = db.collection("stats").document(today)

        if total_ref.get().exists:
            total_ref.update({"count": firestore.Increment(1)})
        else:
            total_ref.set({"count": 1})

        if daily_ref.get().exists:
            daily_ref.update({"count": firestore.Increment(1)})
        else:
            daily_ref.set({"count": 1})
    except:
        pass

# ================= Visit Count Getter =================
def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        total_doc = db.collection("stats").document("total").get()
        daily_doc = db.collection("stats").document(today).get()
        total = total_doc.to_dict().get("count", 0) if total_doc.exists else 0
        daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
        return total, daily
    except:
        return 0, 0

# Streamlit에서 user_agent를 저장 (서버로그가 없으므로 수동)
if "user_agent" not in st.session_state:
    try:
        # 브라우저에서 JavaScript로 가져오려면 아래처럼 iframe src에 붙이는 방식 추천
        st.session_state["user_agent"] = st.request.headers.get("User-Agent", "unknown")
    except:
        st.session_state["user_agent"] = "unknown"

update_visit_stats()

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

# ================= Text =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something 💬",
        "usedup": f"🌙 You've used all {DAILY_FREE_LIMIT} free sessions for now!",
        "reset": f"⏰ Free sessions reset every {RESET_INTERVAL_HOURS} hours.",
        "reply_error": "AI response error",
        "chat_button": "💳 Open Payment & Feedback",
        "chat_return": "💬 Back to Chat",
        "status_left": "remaining",
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": f"🌙 오늘의 무료 상담 {DAILY_FREE_LIMIT}회를 모두 사용했어요!",
        "reset": f"⏰ 무료 상담이 다시 가능해졌어요! ({RESET_INTERVAL_HOURS}시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "chat_button": "💳 결제 및 피드백 열기",
        "chat_return": "💬 대화창으로 돌아가기",
        "status_left": "남은",
    }

st.title(TEXT["title"])

# ================= CSS (same as before) =================
st.markdown(
    """
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
  font-size:21px;
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
""",
    unsafe_allow_html=True
)

# ================= Firestore Defaults / User State =================
defaults = {"is_paid": False, "usage_count": 0, "remaining_paid_uses": 0, "last_reset": datetime.utcnow().isoformat()}
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

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")
total_visits, daily_visits = get_visit_counts()
if language == "English 🇺🇸":
    st.sidebar.markdown(f"🌍 **Total visitors:** {total_visits:,}\n\n☀️ **Today:** {daily_visits:,}")
else:
    st.sidebar.markdown(f"🌍 **총 방문자:** {total_visits:,}명\n\n☀️ **오늘:** {daily_visits:,}명")

# ================= Chat / Payment Logic (기존 유지) =================
# ... (이하 너의 원본 대화/결제 로직 그대로 유지) ...

