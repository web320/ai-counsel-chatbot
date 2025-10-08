import os, json, uuid
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ===== 초기 설정 =====
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== Firebase =====
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

# ===== 앱 정보 =====
APP_VERSION = "v1.6_feedback"
st.title("🌿 따뜻한 AI 상담 (v1.6)")
st.caption("오늘의 마음을 들려주세요 💬")

# ===== 세션 상태 =====
if "messages" not in st.session_state:
    st.session_state.messages = []

# ===== 대화창 =====
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("오늘은 어떤 하루였나요?")
if user_input:
    # 사용자 메시지 저장
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # AI 응답
    with st.chat_message("assistant"):
        with st.spinner("AI가 당신의 마음을 듣는 중이에요..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "따뜻하고 다정한 상담사처럼 대화하세요."},
                    *st.session_state.messages,
                ],
            )
            ai_reply = response.choices[0].message.content
            st.markdown(ai_reply)

    st.session_state.messages.append({"role": "assistant", "content": ai_reply})

    # ===== 🌟 피드백 영역 =====
    st.divider()
    st.markdown("### 🩵 오늘의 상담은 어땠나요?")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("👍 좋았어요"):
            db.collection("feedbacks").add({
                "uid": str(uuid.uuid4()),
                "type": "positive",
                "timestamp": datetime.now().isoformat(),
                "message": user_input,
                "response": ai_reply
            })
            st.success("감사해요 💙 당신의 마음이 저에게 큰 힘이 돼요.")

    with col2:
        if st.button("👎 별로였어요"):
            db.collection("feedbacks").add({
                "uid": str(uuid.uuid4()),
                "type": "negative",
                "timestamp": datetime.now().isoformat(),
                "message": user_input,
                "response": ai_reply
            })
            st.warning("소중한 피드백, 더 따뜻하게 노력할게요 🕊️")

    with col3:
        feedback_text = st.text_input("💬 직접 피드백 남기기 (선택)")
        if st.button("보내기"):
            if feedback_text.strip():
                db.collection("feedbacks").add({
                    "uid": str(uuid.uuid4()),
                    "type": "text",
                    "feedback": feedback_text,
                    "timestamp": datetime.now().isoformat(),
                    "message": user_input,
                    "response": ai_reply
                })
                st.success("정성스러운 피드백 고마워요 🌸")
