# ==========================================
# 💙 EOERWAY AI Therapy v2.4 (KOR/ENG toggle)
# ==========================================
import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= ads.txt =================
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ================= App Config =================
APP_VERSION = "v2.4"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 30
RESET_INTERVAL_HOURS = 4
ADMIN_KEYS = ["4321"]

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

# ================= Query Params =================
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= Language Toggle =================
st.set_page_config(page_title="💙 EOERWAY AI Therapy", layout="wide")

language = st.radio("🌐 Language / 언어 선택", ["English 🇺🇸", "한국어 🇰🇷"], horizontal=True, index=0)

if language == "English 🇺🇸":
    TEXT = {
        "title": "💙 A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "feeling": "How are you feeling today?",
        "thinking": "Thinking...",
        "warn_empty": "Please enter something.",
        "usedup": "🌙 You've used all 7 free sessions for today!",
        "reset": "⏰ Your free sessions have been reset! (Every 4 hours)",
        "reply_error": "AI Response Error",
        "feedback_placeholder": "e.g. The AI felt really comforting 💕",
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
        "title": "💙 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "feeling": "지금 어떤 기분이예요?",
        "thinking": "생각 중이에요...",
        "warn_empty": "내용을 입력해주세요.",
        "usedup": "🌙 오늘의 무료 상담 7회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (4시간마다 자동 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 안전하게 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
.user-bubble {
  background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;margin:8px 0;
  display:inline-block;box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble {
  font-size:21px;line-height:1.8;border-radius:16px;padding:16px 20px;margin:10px 0;
  background:rgba(15,15,30,.85);color:#fff;border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;animation:neon 1.6s ease-in-out infinite alternate;
}
@keyframes neon {from{box-shadow:0 0 8px #ffaa00;}to{box-shadow:0 0 22px #ffcc33;} }
.status {
  font-size:15px;padding:8px 12px;border-radius:10px;
  display:inline-block;margin-bottom:8px;background:rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)

# ================= Firestore 기본값 =================
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

# ================= 감정 프롬프트 =================
def get_emotion_prompt(msg: str):
    msg = msg.lower()
    if language == "English 🇺🇸":
        return "User expressed feelings. Respond warmly and empathetically like a real counselor."
    if any(w in msg for w in ["불안", "걱정", "초조"]):
        return "사용자가 불안을 표현했습니다. 다정하고 안정감을 주는 말로 답해주세요."
    if any(w in msg for w in ["외로워", "혼자", "쓸쓸"]):
        return "사용자가 외로움을 표현했습니다. 따뜻하게 곁에 있어주는 말로 위로해주세요."
    if any(w in msg for w in ["힘들", "귀찮", "지쳤"]):
        return "사용자가 무기력을 표현했습니다. 존재를 인정하며 다정하게 공감해주세요."
    return "일상 대화입니다. 공감하며 따뜻하게 대화를 이어가주세요."

# ================= 스트리밍 응답 =================
def stream_reply(user_input: str):
    try:
        emotion_prompt = get_emotion_prompt(user_input)
        system_prompt = (
            "You are a kind and understanding AI counselor who speaks naturally in English."
            if language == "English 🇺🇸"
            else "너는 공감력 있고 따뜻한 상담사야. 현실적인 위로와 공감을 함께 말해."
        )
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
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
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
                time.sleep(0.03)
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

# ================= 상태 표시 =================
def status_chip():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]
    st.markdown(f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>", unsafe_allow_html=True)

# ================= 결제 및 피드백 =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])
    components.html(f"""
    <div style="text-align:center">
      <a href="{PAYPAL_URL}" target="_blank">
        <button style="background:#ffaa00;color:black;padding:12px 20px;border:none;border-radius:10px;font-size:18px;">
          💳 PayPal ($3)
        </button>
      </a>
    </div>
    """, height=150)

    st.subheader(TEXT["feedback_title"])
    fb = st.text_area(" ", placeholder=TEXT["feedback_placeholder"])
    if st.button("📩 Submit / 보내기"):
        if not fb.strip():
            st.warning(TEXT["feedback_empty"])
        else:
            db.collection("feedbacks").document(str(uuid.uuid4())).set({
                "uid": USER_ID, "feedback": fb, "lang": language,
                "created_at": datetime.utcnow().isoformat()
            })
            st.success(TEXT["feedback_sent"])

# ================= 채팅 =================
def render_chat_page():
    status_chip()
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info(TEXT["reset"])

    usage = st.session_state["usage_count"]
    if not st.session_state.get("is_paid") and usage >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state["show_payment"] = True
        st.rerun()

    user_input = st.chat_input(TEXT["feeling"])
    if not user_input:
        return
    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)
    reply = stream_reply(user_input)
    if reply:
        persist_user({"usage_count": usage + 1})

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")
if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.rerun()

# ================= 실행 =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
