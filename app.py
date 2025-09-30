import os
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# 🔐 ENV
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- 상담사 스타일 옵션 ---
style_options = {
    "따뜻한 상담사": {
        "tone": "따뜻하고 부드럽게, 이해와 공감을 최우선으로 표현",
        "ending": "넌 지금도 충분히 잘하고 있어 🌷"
    },
    "친구처럼 솔직하게": {
        "tone": "친근하고 솔직하게, 친구가 옆에서 말해주는 듯",
        "ending": "네가 힘든 건 너무 당연해. 그래도 난 네 편이야 🤝"
    },
    "연예인처럼 다정하게": {
        "tone": "부드럽고 다정한 여성 연예인 말투",
        "ending": "오늘도 너 정말 멋지게 버텨줬어 ✨"
    }
}

# --- 감정 키워드 매핑 ---
keyword_map = {
    "불안": "네가 불안하다고 한 부분, 그게 무겁게 느껴질 수 있어.",
    "외로움": "외로움이 마음을 꽉 채우면 정말 숨이 막히지.",
    "돈": "돈에 대한 불안은 누구에게나 가장 큰 무게야.",
    "미래": "미래가 안 보일 때 지금 한 발자국이 더 힘들지."
}

# --- 프롬프트 생성 함수 ---
def build_prompt(user_input, style_choice):
    style = style_options[style_choice]

    empathy_line = "네가 말한 걸 듣고 나니까, 네 마음이 많이 힘들었을 것 같아."

    # 키워드 맞춤 답변 찾기
    keyword_reply = ""
    for keyword, reply in keyword_map.items():
        if keyword in user_input:
            keyword_reply = reply
            break
    if not keyword_reply:
        keyword_reply = "네 말 속에 네 진심이 보여."

    hope_line = style["ending"]

    system_prompt = f"""
    너는 {style['tone']} 상담사이자 재테크/수익화 전문가야.
    반드시 (공감 → 맞춤형 되돌려주기 → 희망 멘트)을 지켜서 답해.
    각 답변은 짧고 명확하게, 문단은 2~3문장.
    그리고 항상 지금 당장 할 수 있는 행동 3가지를 제시해.
    """

    user_prompt = f"""
    사용자 입력: {user_input}
    상담사 흐름:
    1. 공감: {empathy_line}
    2. 맞춤형 되돌려주기: {keyword_reply}
    3. 희망 멘트: {hope_line}
    """

    return system_prompt, user_prompt

# --- 답변 스트리밍 함수 ---
def stream_reply(user_input: str, style_choice: str):
    system_prompt, user_prompt = build_prompt(user_input, style_choice)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=700,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response

# --- CSS (글씨 크게) ---
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

# 상담 스타일 선택 (사이드바)
style_choice = st.sidebar.radio("오늘은 어떤 톤으로 위로받고 싶나요?", list(style_options.keys()))

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0
if "limit" not in st.session_state:
    st.session_state.limit = 4

# --- 메인 로직 ---
if st.session_state.usage_count < st.session_state.limit:
    user_input = st.chat_input("마음편히 얘기해봐")
    if user_input:
        st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)

        placeholder = st.empty()
        streamed_text = ""
        for chunk in stream_reply(user_input, style_choice):
            delta = chunk.choices[0].delta
            if delta.content:
                streamed_text += delta.content
                placeholder.markdown(f"<div class='chat-message'>{streamed_text}</div>", unsafe_allow_html=True)

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

if admin_pw == "4321":
    if st.sidebar.button("🔑 관리자 모드 활성화 (60회 가능)"):
        st.session_state.usage_count = 0
        st.session_state.limit = 60
        st.sidebar.success("✅ 관리자 모드 활성화! (60회 사용 가능)")
        st.rerun()
else:
    st.sidebar.caption("관리자 전용 기능입니다.")

