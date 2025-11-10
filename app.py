# ==========================================
# 💙 EOERWAY AI Therapy v2.8 (modified for chat history streaming)
# ==========================================

import os, uuid, json, time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.8"
DAILY_FREE_LIMIT = 15
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 6
ADMIN_KEYS = ["2356"]

# ================= OpenAI Setup =================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ================= Firebase Setup =================
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

# ================= User ID =================
uid = st.experimental_get_query_params().get("uid", [str(uuid.uuid4())])[0]
st.experimental_set_query_params(uid=uid)
USER_ID = uid

# ================= Text / Language =================
if "lang" not in st.session_state:
    st.session_state["lang"] = "English 🇺🇸"

lang_choice = st.radio(
    " ",
    ["English 🇺🇸", "한국어 🇰🇷"],
    horizontal=True,
    index=0 if st.session_state["lang"] == "English 🇺🇸" else 1,
    label_visibility="collapsed"
)
st.session_state["lang"] = lang_choice
language = lang_choice

TEXT = {
    "English 🇺🇸": {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "input": "How are you feeling right now?",
        "reply_error": "AI response error",
        "usedup": "🌙 You’ve used all free sessions today!",
        "reset": "⏰ Free sessions reset! (Every 6 hours)",
        "status_left": "remaining",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "chat_button": "💳 Open Payment & Feedback",
        "chat_return": "💬 Back to Chat",
        "payment_title": "💳 Payment Guide",
        "feedback_title": "💌 Service Feedback",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "admin_success": "🔓 Admin mode activated with 50 extra uses!",
        "admin_already": "✅ Admin already unlocked.",
        "admin_wrong": "❌ Wrong admin password."
    },
    "한국어 🇰🇷": {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "input": "지금 어떤 기분이예요?",
        "reply_error": "AI 응답 오류",
        "usedup": "🌙 오늘의 무료 상담 7회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (6시간마다 복구)",
        "status_left": "남은",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "chat_button": "💳 결제 및 피드백 열기",
        "chat_return": "💬 대화창으로 돌아가기",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "admin_success": "🔓 관리자 모드가 활성화되어 50회 무료 이용권이 추가되었습니다!",
        "admin_already": "✅ 이미 관리자 인증이 완료되어 있습니다.",
        "admin_wrong": "❌ 관리자 비밀번호가 틀렸습니다.",
    }
}[language]

# ================= CSS for bubbles =================
st.markdown("""
<style>
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
  line-height:1.6;
  border-radius:16px;
  padding:16px 20px;
  margin:10px 0;
  background:rgba(15,15,30,.85);
  color:#fff;
  border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;
  word-break:break-word;
  white-space:pre-wrap;
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

# ================= User State & Firestore =================
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

# ================= Chat History in session =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def add_chat_to_history(user_msg, bot_msg):
    st.session_state["chat_history"].append(("user", user_msg))
    st.session_state["chat_history"].append(("bot", bot_msg))

# ================= AI 답변 스트리밍 =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = """
You're talking to someone who came here because they're hurting. Not as a "therapist" - as a real person who genuinely cares.

1. Listen first. Don't rush to fix or advise.
2. Name the feeling very specifically.
3. Tell them it makes sense to feel that way.
4. If it feels natural, gently offer one tiny thing they could try right now (like 3 slow breaths), but don't force it.
5. End with warm, human words, not formal advice.

Respond in 4-6 sentences, warm and human, never clinical. Never diagnose or suggest medication. If they mention self-harm or suicide, gently acknowledge their pain and suggest professional help."""
        else:
            system_prompt = """
상처받고 힘들어서 여기 오신 분이에요. ‘전문가’처럼 딱딱하게 말하지 말고, 진심으로 걱정하는 친구처럼 다정하고 따뜻하게 이야기해 주세요.

1. 먼저, 와줘서 고맙다고 아주 부드럽고 진심으로 공감해 주세요.
2. 그 사람이 느끼는 감정을 구체적이고 세심하게 표현해 주세요. 예를 들어 “완전히 지쳐버린 느낌이시겠어요”처럼요.
3. 이런 감정을 느끼는 게 얼마나 자연스럽고 당연한 일인지 꼭 말씀해 주세요.
4. 가능하다면 지금 바로 할 수 있는 아주 작은 행동을 하나만 부드럽게 제안해 주세요. (예: “깊게 숨을 천천히 3번 쉬어보시는 건 어떨까요?”)
5. 답변은 4~6문장 안으로 정리해 주시고, 모두 ‘요’로 끝나는 존댓말을 사용해 주세요.
6. 진단, 약, 치료 권유는 절대 하지 말아 주세요.
7. 자해나 자살 같은 말이 나오면, 그 고통을 조심스럽게 인정하면서 전문가나 상담전화(예: 1393)를 안내해 주세요.
8. 마지막 문장은 혼자가 아니라고 느낄 수 있도록 따뜻하게 마무리해 주세요.

항상 상대방 마음을 따뜻하게 보듬는 진심 어린 말투로 답변해 주세요."""

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.7,
            max_tokens=700,
            stream=True,
        )

        placeholder = st.empty()
        full_text = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                placeholder.markdown(
                    f"<div class='bot-bubble'>{full_text}💫</div>",
                    unsafe_allow_html=True
                )
                time.sleep(0.03)

        # Firestore에 대화 저장
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": full_text.strip(),
            "lang": language,
            "created_at": datetime.utcnow().isoformat()
        })

        # 세션 대화 기록에 추가
        add_chat_to_history(user_input, full_text.strip())

        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= 대화 페이지 렌더링 =================
def render_chat_page():
    # 사용량 제한 처리
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({
            "usage_count": 0,
            "last_reset": now.isoformat()
        })
        st.info(TEXT["reset"])

    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]

    st.markdown(f"<div class='status'>{plan} — {TEXT['status_left']} {max(left, 0)}회</div>", unsafe_allow_html=True)

    if not st.session_state.get("is_paid") and st.session_state["usage_count"] >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state["show_payment"] = True
        st.experimental_rerun()

    # 전체 대화 기록 보여주기
    for role, msg in st.session_state["chat_history"]:
        css_class = "user-bubble" if role == "user" else "bot-bubble"
        st.markdown(f"<div class='{css_class}'>{msg}</div>", unsafe_allow_html=True)

    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    # 유저 메시지 바로 표시
    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

    reply = stream_reply(user_input)
    if reply:
        if st.session_state.get("is_paid"):
            persist_user({
                "remaining_paid_uses": max(0, st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1)
            })
        else:
            persist_user({"usage_count": st.session_state["usage_count"] + 1})

# ================= 사이드바 및 결제/피드백 =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])

    intent_ref = db.collection("purchase_intent").document(USER_ID)
    intent_doc = intent_ref.get()
    clicked = intent_doc.exists
    total_intents = len(list(db.collection("purchase_intent").stream()))

    st.markdown("#### 50회 이용권 3,000원 결제 의사 확인")

    if clicked:
        st.info("💙 이미 결제 의사를 눌러주셨어요. 정말 감사합니다.")
    else:
        if st.button("💳 3,000원에 50회 이용권, 결제 의사가 있으신가요?"):
            intent_ref.set({
                "uid": USER_ID,
                "plan": "50회_3000원",
                "created_at": datetime.utcnow().isoformat(),
            })
            st.success("결제 기능이 열리면 가장 먼저 알려드릴게요 💖")
            st.experimental_rerun()

    st.caption(f"지금까지 {total_intents}명이 결제 의사를 눌러주셨어요.")

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader(TEXT["feedback_title"])
        fb = st.text_area(" ", placeholder=TEXT["feedback_placeholder"])

        if st.button("📩 보내기"):
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

    with col2:
        admin_input = st.text_input("🔑 관리자 비밀번호 입력", type="password", key="admin_pw_input")

        if admin_input:
            if admin_input in ADMIN_KEYS:
                if not st.session_state.get("admin_unlocked"):
                    new_remaining = st.session_state.get("remaining_paid_uses", 0) + 50
                    persist_user({
                        "is_paid": True,
                        "remaining_paid_uses": new_remaining
                    })
                    st.session_state["admin_unlocked"] = True
                    st.success(TEXT["admin_success"])
                else:
                    st.info(TEXT["admin_already"])
            else:
                st.error(TEXT["admin_wrong"])

# ================= 사이드바 대화 기록 및 결제 버튼 =================
st.sidebar.header("📜 History / 대화 기록")

def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_doc = db.collection("stats").document("total").get()
    daily_doc = db.collection("stats").document(today).get()
    total = total_doc.to_dict().get("count", 0) if total_doc.exists else 0
    daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
    return total, daily

total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(f"""
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
""", unsafe_allow_html=True)

if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.experimental_rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.experimental_rerun()

# ================= 메인 실행 =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
