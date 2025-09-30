import os
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
    "2) 문단은 짧게 2~3문장.\n"
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

# --- CSS (글씨 크게) ---
st.markdown(
    """
    <style>
    .chat-message {
        font-size: 22px;   /* 글씨 크기 크게 */
        line-height: 1.7;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 결제 화면 ---
def show_payment_screen():
    st.subheader("🚫 무료 체험이 끝났습니다")
    st.markdown("월 **3,900원** 결제 후 계속 이용할 수 있습니다.")
    st.markdown("---")
    st.markdown("### 🔗 결제 방법")
    st.markdown("[👉 페이팔 결제하기](https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4)")
    st.info(
        "💡 결제 후 카톡(ID: jeuspo) 또는 이메일(mwiby91@gmail.com)로 "
        "닉네임/결제 스크린샷을 보내주시면 바로 이용 권한을 열어드립니다."
    )

# --- Streamlit UI ---
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0
if "limit" not in st.session_state:
    st.session_state.limit = 4   # 기본 무료 4회

# --- 메인 로직 ---
if st.session_state.usage_count < st.session_state.limit:
    user_input = st.chat_input("마음편히 얘기해봐")
    if user_input:
        # 사용자 입력 표시
        st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)

        # 답변 스트리밍 표시
        placeholder = st.empty()
        streamed_text = ""
        for chunk in stream_reply(user_input):
            delta = chunk.choices[0].delta
            if delta.content:   # ✅ 속성 접근
                streamed_text += delta.content
                placeholder.markdown(f"<div class='chat-message'>{streamed_text}</div>", unsafe_allow_html=True)

        # 기록 저장 & 카운트 증가
        st.session_state.chat_history.append((user_input, streamed_text))
        st.session_state.usage_count += 1
else:
    show_payment_screen()

# --- 사이드바 ---
st.sidebar.header("📜 대화 기록")
if st.session_state.chat_history:
    st.sidebar.markdown(f"**현재 사용 횟수:** {st.session_state.usage_count}/{st.session_state.limit}")
    for i, (q, a) in enumerate(st.session_state.chat_history):
        st.sidebar.markdown(f"**Q{i+1}:** {q[:20]}...")

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 관리자 메뉴")

admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")

if admin_pw == "4321":  # ✅ 관리자 비밀번호
    if st.sidebar.button("🔑 관리자 모드 활성화 (60회 가능)"):
        st.session_state.usage_count = 0
        st.session_state.limit = 60   # ✅ 관리자 모드에서는 60회 가능
        st.sidebar.success("✅ 관리자 모드 활성화! (60회 사용 가능)")
        st.rerun()
else:
    st.sidebar.caption("관리자 전용 기능입니다.")


