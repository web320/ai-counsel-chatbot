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
    "규칙:\n"
    "1) 심리 고민 → 상담사처럼 공감, 위로, 구체적인 조언 제공.\n"
    "2) 돈/수익 질문 → 전문가처럼 실행 가능한 플랜을 단계별로 제시.\n"
    "3) 답변은 최소 10문장 이상, 필요하면 bullet point, 표, 예시 포함.\n"
    "4) 항상 사용자가 지금 당장 할 수 있는 행동 3가지를 명확히 제시.\n"
    "5) 같은 질문이어도 새로운 인사이트를 추가해 반복 피하기."
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
    st.markdown(
        "[👉 카카오페이 결제하기](https://qr.kakaopay.com/yourlink)",
        unsafe_allow_html=True
    )
    st.info("결제가 완료되면 이용 권한이 다시 열립니다!")

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
        answer = get_reply(user_input)

        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            st.markdown(f"<p style='font-size:18px;'>{answer}</p>", unsafe_allow_html=True)

        st.session_state.chat_history.append((user_input, answer))
        st.session_state.usage_count += 1
else:
    show_payment_screen()

# --- 사이드바: 대화 기록 & 남은 횟수 ---
if st.session_state.chat_history:
    st.sidebar.header("📜 대화 기록")
    st.sidebar.markdown(f"**현재 사용 횟수:** {st.session_state.usage_count}/4")
    for i, (q, a) in enumerate(st.session_state.chat_history):
        st.sidebar.markdown(f"**Q{i+1}:** {q[:20]}...")


