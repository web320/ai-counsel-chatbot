# ==========================================
# 💙 EOERWAY AI Therapy v2.8 (Quiet Memory Edition)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.8-QM"   # Quiet Memory
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
    return json.loads(raw) if isinstance(raw, str) else dict(raw)

if not firebase_admin._apps:
    cred = credentials.Certificate(_firebase_config())
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ================= User ID =================
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= 방문자 통계 =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_visit_ref = db.collection("user_visits").document(USER_ID)

    if user_visit_ref.get().exists:
        return

    user_visit_ref.set({
        "uid": USER_ID,
        "first_visit": datetime.utcnow().isoformat(),
        "day": today,
    })

    total_ref = db.collection("stats").document("total")
    daily_ref = db.collection("stats").document(today)

    for ref in [total_ref, daily_ref]:
        if ref.get().exists:
            ref.update({"count": firestore.Increment(1)})
        else:
            ref.set({"count": 1})

def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_doc = db.collection("stats").document("total").get()
    daily_doc = db.collection("stats").document(today).get()
    total = total_doc.to_dict().get("count", 0) if total_doc.exists else 0
    daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
    return total, daily

if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

# ================= 언어 설정 =================
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

# ================= 언어별 텍스트 =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "input": "How are you feeling right now?",
        "reply_error": "AI response error",
        "usedup": "🌙 You’ve used all 7 free sessions today!",
        "reset": "⏰ Free sessions reset! (Every 4 hours)",
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "input": "지금 어떤 기분이예요?",
        "reply_error": "AI 응답 오류",
        "usedup": "🌙 오늘의 무료 상담 7회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (4시간마다 복구)",
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
.user-bubble {
  background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;
  margin:8px 0;display:inline-block;
}
.bot-bubble {
  font-size:20px;border-radius:14px;padding:14px 20px;margin:10px 0;
  background:rgba(15,15,30,.85);color:#fff;
  border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;white-space:pre-wrap;
}
</style>
""", unsafe_allow_html=True)

# ================= Firestore Defaults =================
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

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# =======================================================
# 💫 Quiet Memory Functions (새로 추가된 핵심 부분)
# =======================================================
def save_chat_to_firestore(user_id, role, message):
    """대화 저장: /users/{uid}/chats/{chat_id}"""
    db.collection("users").document(user_id).collection("chats").add({
        "role": role,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    })

def get_recent_context(user_id, limit=5):
    """최근 대화 몇 개 불러와서 기억으로 참고"""
    chats_ref = (
        db.collection("users").document(user_id)
        .collection("chats")
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
    )
    docs = chats_ref.stream()
    context = []
    for doc in reversed(list(docs)):
        data = doc.to_dict()
        context.append({"role": data["role"], "content": data["message"]})
    return context

# =======================================================
# 💬 AI Response with Quiet Memory
# =======================================================
def stream_reply(user_input: str):
    try:
        # 1️⃣ 이전 대화 가져오기
        context = get_recent_context(USER_ID)
        context.append({"role": "user", "content": user_input})

        # 2️⃣ 언어별 시스템 프롬프트
        if language == "English 🇺🇸":
            system_prompt = """
You're a warm, caring AI friend. Remember what this user has said before, 
but never mention remembering. Just use it naturally to connect your replies.
Respond kindly and like a real person who cares.
"""
        else:
            system_prompt = """
너는 따뜻하고 공감적인 AI 친구야. 사용자가 전에 한 말을 참고하지만, 
'기억하고 있다'는 말은 절대 하지 말고, 자연스럽게 이어서 대화해 줘.
"""

        # 3️⃣ AI 응답 생성
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, *context],
            stream=True,
            temperature=0.7,
            max_tokens=700,
        )

        placeholder = st.empty()
        full_text = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
                time.sleep(0.03)

        # 4️⃣ Firestore에 저장 (사용자별)
        save_chat_to_firestore(USER_ID, "user", user_input)
        save_chat_to_firestore(USER_ID, "assistant", full_text.strip())

        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# =======================================================
# 💬 메인 대화 영역
# =======================================================
user_input = st.chat_input(TEXT["input"])
if user_input:
    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)
    stream_reply(user_input)
