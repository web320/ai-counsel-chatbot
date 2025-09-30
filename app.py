import os
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# 🔐 ENV
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- 시스템 프롬프트 ---
STYLE_SYSTEM = (
    "너는 따뜻한 심리상담사이자, 재테크/창업/수익화 전문가야.\n"
    "답변 규칙:\n"
    "1) 한 문장은 30자 이내로 간결하게.\n"
    "2) 문단은 2~3줄마다 끊어 가독성을 높여라.\n"
    "3) 필요하면 bullet point(-, •) 사용.\n"
    "4) 너무 길게 한 문단에 몰아넣지 말고 짧게 끊어라.\n"
    "5) 같은 질문이어도 새로운 인사이트를 추가해 반복 피하기.\n"
    "6) 항상 사용자가 당장 할 수 있는 행동 3가지를 명확히 제시."
)

def get_reply(user_input: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.8,
        top_p=0.95,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": STYLE_SYSTEM},
            {"role": "user", "content": user_input}
        ]
    )
    return resp.choices[0].message.content

# --- CSS (가독성 높이기) ---
st.markdown(
    """
    <style>
    .chat-message {
        font-size: 20px;
        line-height: 1.6;
        max-width: 35ch;  /* 한 줄 35자 이내 */
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
    st.markdown(
        "<p style='font-size:18px;'>월 <b>3,900원</b> 결제 후 계속 이용할 수 있습니다.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown("### 🔗 결제 방법")

    st.markdown(
        "[👉 페이팔 결제하기](https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4)",
        unsafe_allow_html=True
    )

    st.info(
        "💡 결제 후 카톡(ID: jeuspo) 또는 이메일(mwiby91@gmail.com)로 "
        "닉네임/결제 스크린샷을 보내주시면 바로 이용 권한을 열어드립니다."
    )

# --- Streamlit UI ---
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# 세션 상태
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0

# --- 메인 로직 ---
if st.session_state.usage_count < 4:
    user_input = st.chat_input("마음편히 얘기해봐")
    if user_input:
        with st.chat_message("user"):
            st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)

        with st.chat_message("assistant"):
            thinking_box = st.empty()
            thinking_box.markdown("생각중입니다...")

        answer = get_reply(user_input)
        thinking_box.markdown(f"<div class='chat-message'>{answer}</div>", unsafe_allow_html=True)

        st.session_state.chat_history.append((user_input, answer))
        st.session_state.usage_count += 1
else:
    show_payment_screen()

# --- 사이드바 ---
st.sidebar.header("📜 대화 기록")
if st.session_state.chat_history:
    st.sidebar.markdown(f"**현재 사용 횟수:** {st.session_state.usage_count}/4")
    for i, (q, a) in enumerate(st.session_state.chat_history):
        st.sidebar.markdown(f"**Q{i+1}:** {q[:20]}...")

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 관리자 메뉴")

admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")

if admin_pw == "4321":
    if st.sidebar.button("🔑 사용 횟수 리셋"):
        st.session_state.usage_count = 0
        st.sidebar.success("✅ 사용 횟수가 초기화되었습니다! (관리자 전용)")
        st.rerun()
else:
    st.sidebar.caption("관리자 전용 기능입니다.")
