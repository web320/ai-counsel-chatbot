# ==========================================
# 💙 EOERWAY AI Therapy v3.0 (IMPROVED)
# 핵심 개선: 자연스러운 대화 + 맥락 유지 + 공감 강화
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
APP_VERSION = "v3.0"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 4
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
st.query_params = {"uid": uid}
USER_ID = uid

# ================= Visitor Counter =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
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

# ================= Text by Language =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something 💬",
        "usedup": "🌙 You've used all 7 free sessions today!",
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

# ================= 대화 히스토리 초기화 =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ================= 🔥 개선된 AI Response Function =================
def stream_reply(user_input: str):
    try:
        # 🎯 핵심 개선 1: 더 자연스럽고 진솔한 프롬프트
        if language == "English 🇺🇸":
            system_prompt = """You are a warm, empathetic therapist having a genuine conversation.

Your approach:
- Listen deeply to what they're really saying, not just the words
- Validate their feelings without judging ("It makes complete sense you'd feel that way")
- Reflect back what you're hearing to show you understand
- When appropriate, gently help them see things from a new angle
- Offer one small, doable thing they could try if it feels right
- Be human - vary your responses, don't follow a rigid formula

Respond naturally in 4-7 sentences. Let the conversation flow like a real person would talk.

Never give medical advice or diagnose. If they mention self-harm or suicide, gently suggest professional help while staying supportive."""

        else:
            system_prompt = """당신은 따뜻하고 진심 어린 상담사예요. 진짜 사람처럼 자연스럽게 대화하세요.

대화 방식:
- 상대방이 진짜 하고 싶은 말이 뭔지 깊이 들어주세요
- 감정을 있는 그대로 인정해주세요 ("그럴 수 있어요", "힘드셨겠어요")
- 들은 내용을 자연스럽게 다시 말해주면서 이해하고 있다는 걸 보여주세요
- 필요하면 조금 다른 관점을 부드럽게 제시해주세요
- 지금 바로 할 수 있는 작은 행동 하나를 제안해도 좋아요
- 기계적이지 않게, 사람처럼 다양하게 반응하세요

자연스럽게 4-7문장 정도로 답변하세요. 억지로 구조를 따르지 말고 흐름대로 말하세요.
모든 문장은 '요'로 끝나는 존댓말을 사용하세요.

의학적 진단이나 약 조언은 절대 하지 마세요. 
자해나 자살 관련 언급이 있으면 전문가 도움을 부드럽게 권하되 지지는 계속하세요."""

        # 🎯 핵심 개선 2: 대화 히스토리 포함 (최근 3턴만)
        messages = [{"role": "system", "content": system_prompt}]
        
        # 최근 3번의 대화만 컨텍스트로 사용
        recent_history = st.session_state["chat_history"][-6:]  # 유저3+AI3
        for msg in recent_history:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_input})

        # 🎯 핵심 개선 3: Temperature 0.7로 조정 (공감+일관성 균형)
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,  # 0.9 → 0.7 (더 일관되고 신뢰감 있게)
            max_tokens=600,
            stream=True,
        )

        placeholder = st.empty()
        full_text = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                placeholder.markdown(
                    f"<div class='bot-bubble'>{full_text}</div>",
                    unsafe_allow_html=True
                )
                time.sleep(0.03)

        # 대화 히스토리에 추가
        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        st.session_state["chat_history"].append({"role": "assistant", "content": full_text.strip()})

        # Firestore에도 저장
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

# ================= Payment / Feedback Panel =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])

    components.html(
        f"""
    <div style="text-align:center">
      <a href="{PAYPAL_URL}" target="_blank">
        <button style="background:#ffaa00;color:black;padding:12px 20px;border:none;border-radius:10px;font-size:18px;cursor:pointer;">
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
    """,
        height=320
    )

    st.subheader("🔑 관리자 비밀번호 입력")
    pw = st.text_input(" ", type="password", placeholder="관리자 전용 비밀번호 입력")

    if pw:
        if pw.strip() in ADMIN_KEYS:
            persist_user({
                "is_paid": True,
                "remaining_paid_uses": BASIC_LIMIT
            })
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
                "uid": USER_ID,
                "feedback": fb,
                "lang": language,
                "created_at": datetime.utcnow().isoformat()
            })
            st.success(TEXT["feedback_sent"])

# ================= Chat Main Page =================
def render_chat_page():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]

    st.markdown(
        f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>",
        unsafe_allow_html=True
    )

    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))

    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({
            "usage_count": 0,
            "last_reset": now.isoformat()
        })
        st.info(TEXT["reset"])

    usage = st.session_state["usage_count"]
    if not st.session_state.get("is_paid") and usage >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state["show_payment"] = True
        st.rerun()

    # 🎯 대화 히스토리 표시
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(
                f"<div class='user-bubble'>{msg['content']}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='bot-bubble'>{msg['content']}</div>",
                unsafe_allow_html=True
            )

    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True
    )

    reply = stream_reply(user_input)

    if reply:
        if st.session_state.get("is_paid"):
            persist_user({
                "remaining_paid_uses": max(
                    0,
                    st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1
                )
            })
        else:
            persist_user({"usage_count": usage + 1})

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(
    f"""
    <div style="
        margin-top: 12px;
        margin-bottom: 16px;
        padding: 8px 10px;
        border-radius: 10px;
        background: rgba(255,255,255,0.03);
        font-size: 13px;
        color: rgba(255,255,255,0.85);
    ">
        🌍 <b>Total {total_visits:,}명</b><br>
        ☀️ <b>Today {daily_visits:,}명</b>
    </div>
    """,
    unsafe_allow_html=True
)

if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.rerun()

# 🆕 대화 초기화 버튼 추가
if st.sidebar.button("🔄 새 대화 시작"):
    st.session_state["chat_history"] = []
    st.rerun()

# ================= Main Render =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
