import os
import time
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# 🔐 ENV
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- 프롬프트 ---
STYLE_SYSTEM = (
    "너는 따뜻한 심리상담사이자, 재테크/창업/수익화 전문가야.\n"
    "답변 규칙:\n"
    "1) 핵심은 명확하게, 문장은 자연스럽게.\n"
    "2) 문단은 짧게 끊어 가독성 높이기.\n"
    "3) 항상 지금 당장 할 수 있는 행동 3가지를 제시.\n"
)

def stream_reply(user_input: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.6,
        max_tokens=600,
        stream=True,   # 🚀 스트리밍 모드
        messages=[
            {"role": "system", "content": STYLE_SYSTEM},
            {"role": "user", "content": user_input}
        ]
    )
    return response

# --- CSS ---
st.markdown(
    """
    <style>
    .chat-message {
        font-size: 22px;   
        line-height: 1.7;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Streamlit UI ---
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 메인 로직 ---
user_input = st.chat_input("마음편히 얘기해봐")
if user_input:
    # 사용자 입력 표시
    st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)

    # 답변 스트리밍 표시
    placeholder = st.empty()
    streamed_text = ""
    for chunk in stream_reply(user_input):
        if chunk.choices[0].delta.get("content"):
            streamed_text += chunk.choices[0].delta.content
            placeholder.markdown(f"<div class='chat-message'>{streamed_text}</div>", unsafe_allow_html=True)

    # 기록 저장
    st.session_state.chat_history.append((user_input, streamed_text))

# --- 사이드바 ---
st.sidebar.header("📜 대화 기록")
for i, (q, a) in enumerate(st.session_state.chat_history):
    st.sidebar.markdown(f"**Q{i+1}:** {q[:20]}...")

