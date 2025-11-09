# ==========================================
# 💙 EOERWAY AI Therapy v2.9 — Quiet Memory + User Chat History
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

# ================= UID =================
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= Quiet Memory Helper =================
def get_recent_context(user_id, limit=5):
    """최근 n개의 대화 가져오기 (AI 참고용, 사용자에게는 표시 안 함)"""
    chats_ref = (
        db.collection("users")
        .document(user_id)
        .collection("chats")
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
    )
    docs = chats_ref.stream()
    context = []
    for doc in reversed(list(docs)):  # 오래된 순으로
        data = doc.to_dict()
        if "role" in data and "content" in data:
            context.append({"role": data["role"], "content": data["content"]})
    return context

def save_chat(user_id, role, content):
    """사용자별 대화 Firestore에 저장"""
    db.collection("users").document(user_id).collection("chats").add({
        "role": role,
        "content": content,
        "created_at": datetime.utcnow().isoformat()
    })

# ================= Stream Reply (Modified) =================
def stream_reply(user_input: str):
    try:
        # 조용한 기억 불러오기
        context = get_recent_context(USER_ID)

        if st.session_state["lang"] == "English 🇺🇸":
            system_prompt = """
You are a warm, empathetic companion who remembers the user's emotional context from past talks — 
but never say you remember or mention previous chats. 
Speak naturally, kindly, and humanly in 4–6 sentences."""
        else:
            system_prompt = """
너는 사용자의 감정과 맥락을 조용히 기억하는 따뜻한 친구야.
하지만 '기억하고 있다'거나 '전에 말했죠' 같은 표현은 절대 하지 마.
항상 다정하고 따뜻하게, 4~6문장 안으로 말해줘."""

        messages = [{"role": "system", "content": system_prompt}]
        messages += context  # 과거 대화 기억 (노출 X)
        messages.append({"role": "user", "content": user_input})

        # Firestore에 사용자 입력 저장
        save_chat(USER_ID, "user", user_input)

        # 스트리밍 응답
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
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

        # Firestore에 AI 답변 저장
        save_chat(USER_ID, "assistant", full_text.strip())

        return full_text.strip()

    except Exception as e:
        st.error(f"AI 응답 오류: {e}")
        return None

# ================= Chat UI (Improved) =================
def render_chat_page():
    st.markdown(f"### 💬 Chat with EOERWAY v2.9")

    # 과거 대화 표시 (유지형 채팅 UI)
    chat_docs = (
        db.collection("users")
        .document(USER_ID)
        .collection("chats")
        .order_by("created_at")
        .limit(20)
        .stream()
    )

    for doc in chat_docs:
        d = doc.to_dict()
        if d["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{d['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>{d['content']}</div>", unsafe_allow_html=True)

    # 새 입력창
    user_input = st.chat_input("💬 지금 어떤 기분이에요?")
    if user_input:
        st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)
        stream_reply(user_input)

# ================= Run =================
render_chat_page()
