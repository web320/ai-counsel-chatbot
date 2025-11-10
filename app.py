# ==========================================
# EOERWAY AI Therapy v2.9 (Chat History + Persistent Chat)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.9"
DAILY_FREE_LIMIT = 15
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 6
ADMIN_KEYS = ["2356"]

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

# ================= UID =================
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
    total = total_doc.to_dict().get("count",  arb) if total_doc.exists else 0
    daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
    return total, daily

if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

# ================= Language =================
if "lang" not in st.session_state:
    st.session_state["lang"] = "English"

col1, col2 = st.columns([5, 1])
with col2:
    lang_choice = st.radio(
        " ",
        ["English", "한국어"],
        horizontal=True,
        label_visibility="collapsed",
        index=0 if st.session_state["lang"] == "English" else 1
    )
st.session_state["lang"] = lang_choice
language = st.session_state["lang"]

# ================= Text Dictionary =================
if language == "English":
    TEXT = {
        "title": "A Warm AI Friend You Can Lean On",
        "free": "Free Trial",
        "paid": "Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something",
        "usedup": "You’ve used all free sessions today!",
        "reset": "Free sessions reset! (Every 6 hours)",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., The AI felt really comforting",
        "feedback_sent": "Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something",
        "payment_title": "Payment Guide",
        "feedback_title": "Service Feedback",
        "chat_return": "Back to Chat",
        "chat_button": "Payment & Feedback",
        "status_left": "remaining",
        "admin_success": "Admin mode activated – 50 free uses added!",
        "admin_already": "Admin already authenticated.",
        "admin_wrong": "Wrong admin password.",
        "history_title": "Chat History",
        "no_history": "No chat history yet.",
    }
else:
    TEXT = {
        "title": "마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "무료 체험중",
        "paid": "유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요",
        "usedup": "오늘의 무료 상담을 모두 사용했어요!",
        "reset": "무료 상담이 다시 가능해졌어요! (6시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요",
        "feedback_sent": "피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요",
        "payment_title": "결제 안내",
        "feedback_title": "서비스 피드백",
        "chat_return": "대화창으로 돌아가기",
        "chat_button": "결제 및 피드백 열기",
        "status_left": "남은",
        "admin_success": "관리자 모드 활성화 – 50회 무료 이용권 추가!",
        "admin_already": "이미 관리자 인증 완료",
        "admin_wrong": "관리자 비밀번호가 틀렸습니다.",
        "history_title": "대화 기록",
        "no_history": "아직 대화 기록이 없습니다.",
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown(
    """
<style>
html, body, [class*="css"] { font-size: 18px; }
.stChatMessage { margin-bottom: 12px; }
.user-bubble {
  background:#b91c1c; color:#fff; border-radius:14px;
  padding:10px 18px; display:inline-block; box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble {
  font-size:21px; line-height:1.8; border-radius:16px;
  padding:16px 20px; background:rgba(15,15,30,.85); color:#fff;
  border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;
  animation:neon 1.6s ease-in-out infinite alternate;
  word-break:break-word; white-space:pre-wrap;
}
@keyframes neon {
  from { box-shadow:0 0 8px #ffaa00; }
  to   { box-shadow:0 0 22px #ffcc33; }
}
.status { font-size:15px; padding:8px 12px; border-radius:10px;
  display:inline-block; margin-bottom:8px; background:rgba(255,255,255,.06);
}
</style>
""",
    unsafe_allow_html=True,
)

# ================= Session State Init =================
if "messages" not in st.session_state:
    st.session_state.messages = []           # 현재 세션 대화
if "show_payment" not in st.session_state:
    st.session_state.show_payment = False
if "show_history" not in st.session_state:
    st.session_state.show_history = False

# ================= Firestore User State =================
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

# ================= AI Stream Reply =================
def stream_reply(user_input: str):
    try:
        system_prompt = (
            "You're a warm, empathetic friend..." if language == "English"
            else
            """AI 심리상담 챗봇 역할 지침..."""  # 기존 한국어 프롬프트 유지
        )
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
            if chunk.choices[0].delta.content:
                full_text += chunk.choices[0].delta.content
                placeholder.markdown(f"<div class='bot-bubble'>{full_text}✨</div>", unsafe_allow_html=True)
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

# ================= Payment & Feedback Panel =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])
    # ... (기존 결제 의사, 피드백, 관리자 패널 그대로 유지)
    # (생략 – 기존 코드 복사)

# ================= Chat History Panel =================
def render_chat_history():
    st.subheader(TEXT["history_title"])
    chats = db.collection("chats").where("uid", "==", USER_ID).order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    history = list(chats)
    if not history:
        st.info(TEXT["no_history"])
        return
    for chat in reversed(history):
        data = chat.to_dict()
        with st.chat_message("user"):
            st.markdown(f"<div class='user-bubble'>{data['input']}</div>", unsafe_allow_html=True)
        with st.chat_message("assistant"):
            st.markdown(f"<div class='bot-bubble'>{data['reply']}</div>", unsafe_allow_html=True)

# ================= Main Chat Page =================
def render_chat_page():
    # 사용량 표시
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]
    st.markdown(f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>", unsafe_allow_html=True)

    # 리셋 로직
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.success(TEXT["reset"])

    # 무료 초과
    if not st.session_state.get("is_paid") and st.session_state["usage_count"] >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state.show_payment = True
        st.rerun()

    # === 대화 기록 표시 ===
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

    # === 입력 ===
    if prompt := st.chat_input(TEXT["input"]):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(f"<div class='user-bubble'>{prompt}</div>", unsafe_allow_html=True)

        # AI 응답
        with st.chat_message("assistant"):
            reply = stream_reply(prompt)
            if reply:
                st.session_state.messages.append({"role": "assistant", "content": reply})

        # 사용량 차감
        if st.session_state.get("is_paid"):
            persist_user({
                "remaining_paid_uses": max(0, st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1)
            })
        else:
            persist_user({"usage_count": st.session_state["usage_count"] + 1})

        st.rerun()

# ================= Sidebar =================
st.sidebar.header("History / 대화 기록")
total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(
    f"""
    <div style="margin:12px 0; padding:8px 10px; border-radius:10px; background:rgba(255,255,255,0.03); font-size:13px;">
        <b>Total {total_visits:,}명</b><br>
        <b>Today {daily_visits:,}명</b>
    </div>
    """,
    unsafe_allow_html=True,
)

# 사이드바 버튼들
if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state.show_payment = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state.show_payment = True
        st.rerun()

if st.sidebar.button(TEXT["history_title"]):
    st.session_state.show_history = True
    st.rerun()

# ================= Main Render =================
if st.session_state.get("show_history"):
    render_chat_history()
    if st.button("← " + TEXT["chat_return"]):
        st.session_state.show_history = False
        st.rerun()
elif st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
