# ==========================================
# 💙 EOERWAY AI Therapy v3.8 (COMPLETE MVP)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

APP_VERSION = "v3.8"
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
    return json.loads(raw) if isinstance(raw, str) else dict(raw)

if not firebase_admin._apps:
    cred = credentials.Certificate(_firebase_config())
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ================= User ID =================
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= UNIQUE VISITOR TRACKER =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_ref = db.collection("user_visits").document(USER_ID)
    if user_ref.get().exists:
        return
    user_ref.set({"uid": USER_ID, "first_visit": datetime.utcnow().isoformat(), "day": today})

    total_ref = db.collection("stats").document("total")
    daily_ref = db.collection("stats").document(today)
    for ref in [total_ref, daily_ref]:
        if ref.get().exists:
            ref.update({"count": firestore.Increment(1)})
        else:
            ref.set({"count": 1})

def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total = db.collection("stats").document("total").get().to_dict() or {"count": 0}
    daily = db.collection("stats").document(today).get().to_dict() or {"count": 0}
    return total["count"], daily["count"]

if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

# ================= Language =================
if "lang" not in st.session_state:
    st.session_state["lang"] = "한국어 🇰🇷"
lang = st.radio(" ", ["English 🇺🇸", "한국어 🇰🇷"], horizontal=True, label_visibility="collapsed")
st.session_state["lang"] = lang

TEXT = {
    "title_en": "❤️ A Warm AI Friend You Can Lean On",
    "title_kr": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
    "chat_input_en": "How are you feeling right now?",
    "chat_input_kr": "지금 어떤 기분이예요?",
    "click_btn": "💳 결제 하실래요? (3,000원 / 50회 이용권)",
    "clicked": "💙 이미 결제 의사를 눌러주셨어요. 감사합니다!",
    "feedback": "💌 서비스 피드백",
}

st.title(TEXT["title_en"] if lang == "English 🇺🇸" else TEXT["title_kr"])

# ================= CSS =================
st.markdown("""
<style>
.user-bubble {background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;margin:8px 0;display:inline-block;box-shadow:0 0 10px rgba(255,0,0,0.3);}
.bot-bubble {font-size:20px;line-height:1.8;border-radius:16px;padding:16px 20px;margin:10px 0;background:rgba(15,15,30,.85);color:#fff;
border:2px solid transparent;border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;box-shadow:0 0 12px #ffaa00;}
.status {font-size:15px;padding:8px 12px;border-radius:10px;margin-bottom:8px;background:rgba(255,255,255,.06);}
</style>
""", unsafe_allow_html=True)

# ================= CHAT =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def stream_reply(prompt):
    try:
        system_prompt = "You're a warm friend who listens deeply and responds with empathy."
        messages = [{"role": "system", "content": system_prompt}] + st.session_state["chat_history"][-4:]
        messages.append({"role": "user", "content": prompt})

        stream = client.chat.completions.create(model="gpt-4o", messages=messages, stream=True)
        placeholder = st.empty()
        full = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full += delta.content
                placeholder.markdown(f"<div class='bot-bubble'>{full}</div>", unsafe_allow_html=True)
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        st.session_state["chat_history"].append({"role": "assistant", "content": full})
        db.collection("chats").add({"uid": USER_ID, "input": prompt, "reply": full, "time": datetime.utcnow().isoformat()})
    except Exception as e:
        st.error(f"AI 오류: {e}")

# ================= PAYMENT PANEL =================
def render_payment():
    st.markdown("---")
    st.subheader("💳 결제 의사 테스트")
    st.write("50회 이용권 — 단 **3,000원** ✨")

    click_ref = db.collection("purchase_intent").document(USER_ID)
    clicked = click_ref.get().exists
    total_clicks = len(list(db.collection("purchase_intent").stream()))

    if clicked:
        st.info(TEXT["clicked"])
    else:
        if st.button(TEXT["click_btn"]):
            click_ref.set({"uid": USER_ID, "clicked_at": datetime.utcnow().isoformat(), "plan": "50회_3000원"})
            st.success("감사합니다 💖 결제 기능이 열리면 가장 먼저 알려드릴게요!")
            st.rerun()

    st.metric("💳 총 결제 의사 클릭 수", f"{total_clicks:,} 명")

    st.markdown("---")
    st.subheader(TEXT["feedback"])
    fb = st.text_area("의견을 남겨주세요 💬")
    if st.button("📩 보내기"):
        if not fb.strip():
            st.warning("내용을 입력해주세요 💬")
        else:
            db.collection("feedbacks").document(str(uuid.uuid4())).set({
                "uid": USER_ID,
                "feedback": fb,
                "time": datetime.utcnow().isoformat()
            })
            st.success("💖 피드백이 저장되었습니다. 감사합니다!")

# ================= SIDEBAR =================
# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

# ✅ 방문자 수 가져오기
def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_doc = db.collection("stats").document("total").get()
    daily_doc = db.collection("stats").document(today).get()
    total = total_doc.to_dict().get("count", 0) if total_doc.exists else 0
    daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
    return total, daily

total_visits, daily_visits = get_visit_counts()

# ✅ 사이드바 표시 (결제의사 제거)
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

# 기존 버튼 유지
if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.rerun()


# ================= MAIN =================
if st.session_state.get("show_payment"):
    render_payment()
else:
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

    user_input = st.chat_input(TEXT["chat_input_kr"] if lang == "한국어 🇰🇷" else TEXT["chat_input_en"])
    if user_input:
        st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)
        stream_reply(user_input)
