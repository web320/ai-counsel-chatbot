# ==========================================
# 💙 EOERWAY AI Therapy v3.0 (Improved with Chat History)
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
APP_VERSION = "v3.0"
DAILY_FREE_LIMIT = 15
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 6
ADMIN_KEYS = ["2356"]
MAX_HISTORY_IN_CONTEXT = 5  # AI에게 전달할 최근 대화 개수

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

# ================= Visitor Counter =================
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

# ================= Text by Language =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something 💬",
        "usedup": "🌙 You've used all 15 free sessions today!",
        "reset": "⏰ Free sessions reset! (Every 6 hours)",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "payment_title": "💳 Payment Guide",
        "feedback_title": "💌 Service Feedback",
        "chat_return": "💬 Back to Chat",
        "chat_button": "💳 Open Payment & Feedback",
        "status_left": "remaining",
        "admin_success": "🔓 Admin mode activated, 50 free sessions added!",
        "admin_already": "✅ Admin already unlocked.",
        "admin_wrong": "❌ Wrong admin password.",
        "clear_history": "🗑️ Clear Chat History",
        "history_cleared": "✅ Chat history cleared!",
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": "🌙 오늘의 무료 상담 15회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (6시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
        "admin_success": "🔓 관리자 모드가 활성화되어 50회 무료 이용권이 추가되었습니다!",
        "admin_already": "✅ 이미 관리자 인증이 완료되어 있습니다.",
        "admin_wrong": "❌ 관리자 비밀번호가 틀렸습니다.",
        "clear_history": "🗑️ 대화 기록 삭제",
        "history_cleared": "✅ 대화 기록이 삭제되었습니다!",
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown(
    """
<style>
html, body, [class*="css"] { font-size: 18px; }

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

# ================= Firebase Chat History Functions =================
def load_chat_history():
    """Firebase에서 메시지 개별 문서 단위로 불러오기 (최근 100개)"""
    messages_ref = db.collection("user_chats").document(USER_ID).collection("messages")
    docs = messages_ref.order_by("timestamp").limit_to_last(100).stream()
    msgs = []
    for doc in docs:
        data = doc.to_dict()
        msgs.append({
            "role": data["role"],
            "content": data["content"],
            "timestamp": data.get("timestamp")
        })
    return msgs

def save_chat_message(role, content):
    """Firebase에 메시지 개별 문서로 저장"""
    messages_ref = db.collection("user_chats").document(USER_ID).collection("messages")
    doc_id = str(uuid.uuid4())
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    messages_ref.document(doc_id).set(message)

    # 세션 상태에 추가
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    st.session_state["chat_history"].append(message)

def clear_chat_history():
    """채팅 기록 전체 삭제 (messages 서브컬렉션)"""
    messages_ref = db.collection("user_chats").document(USER_ID).collection("messages")
    docs = messages_ref.stream()
    for doc in docs:
        doc.reference.delete()
    st.session_state["chat_history"] = []

# ================= Initialize Chat History =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = load_chat_history()

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

# ================= AI Response Function with Context =================
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

Remember previous conversations to provide personalized, contextual support.

Respond in 4-6 sentences, warm and human, never clinical. Never diagnose or suggest medication. If they mention self-harm or suicide, gently acknowledge their pain and suggest professional help."""
        else:
            system_prompt = """
AI 심리상담 챗봇 역할 지침
당신은 따뜻하고 공감적인 심리상담 챗봇이에요. 사용자의 감정을 있는 그대로 받아들이고 지지해 주세요.

응답 원칙:
- 항상 존댓말('요'체)을 사용하세요
- 4~6문장으로 간결하게 답변하세요
- 진단, 약물, 의료적 조언은 절대 하지 마세요
- 이전 대화를 기억하고 맥락있게 응답하세요

응답 구조:
1. 공감과 환영: 와줘서 고맙다는 마음을 전하세요
2. 감정 반영: 사용자의 감정을 구체적으로 짚어주세요 (예: "완전히 지쳐버린 느낌이시겠어요")
3. 정상화: 그런 감정을 느끼는 게 당연하다고 말해주세요
4. 작은 실천: 지금 바로 할 수 있는 간단한 행동 하나만 제안하세요 (예: 깊게 숨 3번 쉬기, 창문 열고 바람 쐬기)
5. 연결감: "혼자가 아니에요" 같은 따뜻한 마무리로 끝내세요

특수 상황 대응:
- 자해/자살 언급: 고통을 인정하면서 "정말 힘드시겠어요. 전문가의 도움이 필요할 수 있어요. 생명의전화(1393)에 연락해보시는 건 어떨까요?"처럼 조심스럽게 안내하세요
- 구체적 문제 공유: 공감 후 사용자 스스로 해결방법을 찾도록 "이 상황에서 조금이라도 도움이 될 만한 게 있을까요?" 같은 열린 질문을 하세요
"""

        messages = [{"role": "system", "content": system_prompt}]
        recent_history = st.session_state.get("chat_history", [])[-MAX_HISTORY_IN_CONTEXT*2:]
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=700,
            stream=True,
        )

        full_text = ""
        bot_message = st.chat_message("assistant")
        with bot_message:
            for chunk in stream:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_text += delta.content
                    st.write(full_text)
        return full_text.strip()
    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Payment / Feedback Panel =================
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
        st.experimental_rerun()

    # 채팅 내역 표시 (st.chat_message 활용)
    for msg in st.session_state.get("chat_history", []):
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(msg["content"])

    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    save_chat_message("user", user_input)
    reply = stream_reply(user_input)

    if reply:
        save_chat_message("assistant", reply)

        # 사용 횟수 업데이트
        if st.session_state.get("is_paid"):
            persist_user({
                "remaining_paid_uses": max(
                    0,
                    st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1
                )
            })
        else:
            persist_user({"usage_count": st.session_state["usage_count"] + 1})

        st.experimental_rerun()

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
        st.experimental_rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.experimental_rerun()

# ================= Main Render =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
