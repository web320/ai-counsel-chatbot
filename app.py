import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 환경변수 불러오기
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 기본 화면
st.title("💙 AI 상담 챗봇")
st.write("따뜻하고 다정한 심리 상담사처럼 답변해드려요 💕")

# 대화 기록 저장
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 이전 대화 보여주기
for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

# 사용자 입력
if prompt := st.chat_input("무엇이든 편하게 물어보세요."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # GPT 응답
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "너는 다정한 상담사야."}] + st.session_state["messages"]
    )
    reply = response.choices[0].message.content
    st.session_state["messages"].append({"role": "assistant", "content": reply})
    st.chat_message("assistant").write(reply)
