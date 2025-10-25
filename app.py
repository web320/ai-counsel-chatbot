# ==========================================
# 💙 EOERWAY AI Therapy v2.8
# (Default: English, Small Language Toggle Button)
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

# ================= Config =================
APP_VERSION = "v2.8"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50
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

# ================= UI Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# --- 작은 언어 전환 버튼 (기본 영어) ---
if "lang" not in st.session_state:
    st.session_state["lang"] = "English 🇺🇸"

col1, col2 = st.columns([5,1])
with col2:
    lang_choice = st.radio(" ", ["English 🇺🇸", "한국어 🇰🇷"], horizontal=True, label_visibility="collapsed",
                           index=0 if st.session_state["lang"] == "English 🇺🇸" else 1)
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

# ================= AI Response =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = (
                "You are a warm and empathetic professional counselor. "
                "Comfort the user’s heart with gentle, moving words in 6–9 sentences."
            )
        else:
            system_prompt = (
                "너는 마음이 무척 따뜻하고 공감력 있는 심리 전문상담사예요. "
                "이용자의 마음을 토닥여주고 따뜻하게 감동을 주는 말을 6~9문장 정도로 이야기해줘요. "
                "모든 문장은 반드시 ‘요’로 끝나야 하고, 존댓말을 사용해요. "
                "먼저 이렇게 용기 내어 이야기해줘서 정말 고마워요. "
                "이용자의 상황을 이해하고 따뜻하게 공감하며 위로의 말을 건네주세요."
            )

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
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
            "lang": language,
            "created_at": datetime.utcnow().isoformat()
        })
        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Payment =================
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
      <p style="opacity:0.9;margin-top:14px;line-height:1.6;font-size:17px;">
      After payment, please send a screenshot to  
      <b style="color:#FFD966;">mwiby91@gmail.com</b> or KakaoTalk ID <b>jeuspo</b> 💌<br>
      🔒 <b>Once the message is read</b>, your 50-use access will be activated within 1 hour.  
      <br><br>
      🇰🇷 결제 후 <b style="color:#FFD966;">mwiby91@gmail.com</b> 또는  
      <b>카톡 ID: jeuspo</b> 로 스크린샷을 보내주세요.<br>
      메시지를 확인한 후 1시간 이내에 50회 이용권이 활성화됩니다. 🌸
      </p>
    </div>
    """, height=320)

    st.subheader("🔑 관리자 비밀번호 입력")
    pw = st.text_input(" ", type="password", placeholder="관리자 전용 비밀번호 입력")
    if pw:
        if pw.strip() in ADMIN_KEYS:
            persist_user({"is_paid": True, "remaining_paid_uses": BASIC_LIMIT})
            st.success("✅ 인증 성공! 50회 이용권이 활성화되었습니다.")
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")

    st.markdown("---")
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

# ================= Chat =================
def render_chat_page():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]
    st.markdown(f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>", unsafe_allow_html=True)

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

    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return
    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)
    reply = stream_reply(user_input)
    if reply:
        if st.session_state.get("is_paid"):
            persist_user({"remaining_paid_uses": st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1})
        else:
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

# ================= Run =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
