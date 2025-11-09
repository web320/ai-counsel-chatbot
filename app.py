# ==========================================
# 💙 EOERWAY AI Therapy v2.9 — with Chat History View
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
APP_VERSION = "v2.9"
DAILY_FREE_LIMIT = 15
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 6
ADMIN_KEYS = ["4321"]

# ================= ads.txt =================
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

# ================= Query Params / UID =================
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.experimental_set_query_params(uid=uid)
USER_ID = uid

# ================= 방문자 카운트 =================
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

    if total_ref.get().exists:
        total_ref.update({"count": firestore.Increment(1)})
    else:
        total_ref.set({"count": 1})

    if daily_ref.get().exists:
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

if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

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
        "usedup": "🌙 You’ve used all free sessions today!",
        "reset": "⏰ Free sessions reset! (Every 4 hours)",
        "reply_error": "AI response error",
        "history_title": "📜 Chat History",
        "no_history": "No previous chats yet 💭",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": "🌙 오늘의 무료 상담을 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (4시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "history_title": "📜 대화 기록",
        "no_history": "아직 저장된 대화가 없어요 💭",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown(
    """
<style>
html, body, [class*="css"] { font-size: 18px; }
.user-bubble {
  background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;margin:8px 0;
  display:inline-block;box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble {
  font-size:21px;line-height:1.8;border-radius:16px;padding:16px 20px;margin:10px 0;
  background:rgba(15,15,30,.85);color:#fff;white-space:pre-wrap;word-break:break-word;
  box-shadow:0 0 12px #ffaa00;
}
.history-box {
  background:rgba(255,255,255,0.05);
  padding:10px 15px;margin-bottom:10px;border-radius:12px;
  font-size:15px;line-height:1.5;
}
</style>
""",
    unsafe_allow_html=True
)

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
    data = snap.to_dict() or {}
    st.session_state.update({k: data.get(k, v) for k, v in defaults.items()})
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ================= Improved AI System Prompt =================
if language == "English 🇺🇸":
    system_prompt = """
You are a warm, kind-hearted AI therapist who listens deeply.
Your tone should feel gentle, human, and emotionally attuned — never robotic or overly clinical.

Rules:
1. When the user says very short things (under 5 words, like "hi", "hello", "thanks"),
   respond briefly but warmly (1–2 short sentences).
2. Otherwise, write 4–7 sentences with emotional warmth and reflection.
3. Reflect the emotion you sense in the user’s message — name it gently.
4. Always validate their feelings. ("It makes sense you feel that way.")
5. Offer gentle, realistic comfort — not advice.
6. Never give medical advice or diagnose.

Example:
User: “I feel like nobody cares.”
AI: “That sounds deeply painful. It must feel so lonely to carry that. 
It makes perfect sense to feel that way when you don’t feel seen. 
I want you to know — even now, you’re not alone in this moment 💙”
"""
else:
    system_prompt = """
당신은 따뜻하고 다정한 마음을 가진 AI 상담사입니다.
말투는 마치 다정한 친구처럼, 진심으로 공감하며 사람의 마음에 온기를 전해야 합니다.

규칙:
1. 사용자가 아주 짧게 말할 경우(예: "안녕", "그래"), 부드럽게 1~2문장으로 짧게 답해 주세요.
2. 그 외엔 4~7문장 정도로 따뜻하고 정성스럽게 대답해 주세요.
3. 사용자의 감정을 구체적으로 짚고, "그럴 수 있다"는 공감을 표현해 주세요.
4. 위로와 안정감을 주되, 강요하거나 조언하지 말고 친구처럼 이야기해 주세요.
5. 자해나 죽음 언급이 있으면 “그만큼 아프셨겠어요”로 시작해 공감한 뒤,
   전문가나 상담기관(예: 1393)을 부드럽게 안내하세요.

예시:
사용자: “아무도 나 신경 안 쓰는 것 같아요.”
AI: “그런 생각이 들면 정말 마음이 시릴 것 같아요. 
그 외로움이 얼마나 오래 쌓였을지도 느껴져요. 
그럴 때 그런 마음이 드는 건 너무나 자연스러워요. 
지금 이 순간만큼은 제가 당신 이야기를 듣고 있어요 💙”
"""

# ================= AI Response Function =================
def stream_reply(user_input: str):
    try:
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            stream=True,
        )

        placeholder = st.empty()
        full_text = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            if "content" in delta and delta.content:
                full_text += delta.content
                placeholder.markdown(f"<div class='bot-bubble'>{full_text}</div>", unsafe_allow_html=True)
                time.sleep(0.03)

        # 저장
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": full_text.strip(),
            "lang": language,
            "created_at": datetime.utcnow().isoformat()
        })

        return full_text.strip()
    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Chat History =================
def render_chat_history():
    st.markdown(f"### {TEXT['history_title']}")
    chats = list(
        db.collection("chats")
        .where("uid", "==", USER_ID)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(20)
        .stream()
    )
    if not chats:
        st.info(TEXT["no_history"])
        return

    for c in chats:
        data = c.to_dict()
        input_text = data.get("input", "(empty)")
        reply_text = data.get("reply", "")
        # 일부 미리보기
        reply_preview = (reply_text[:100] + "...") if len(reply_text) > 100 else reply_text
        st.markdown(
            f"""
            <div class='history-box'>
            <b>🗣 {input_text}</b><br>
            <div style='color:#bbb;margin-top:4px;'>💬 {reply_preview}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ================= Sidebar =================
st.sidebar.header(TEXT["history_title"])
if st.sidebar.button("🔄 Refresh / 새로고침"):
    st.experimental_rerun()

render_chat_history()

# ================= Main Chat =================
user_input = st.chat_input(TEXT["input"])
if user_input:
    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)
    stream_reply(user_input)

