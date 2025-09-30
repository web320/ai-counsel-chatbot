import os
import uuid
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# ========== OpenAI ==========
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ========== Firebase ==========
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ========== Cookie (브라우저 고정 ID) ==========
from streamlit_cookies_manager import EncryptedCookieManager

cookies = EncryptedCookieManager(
    prefix="ai_counsel_",
    password=st.secrets["cookie_password"]  # Secrets에 넣은 비밀키
)
if not cookies.ready():
    st.stop()

if "uid" not in cookies or not cookies["uid"]:
    cookies["uid"] = str(uuid.uuid4())
    cookies.save()
USER_ID = cookies["uid"]  # 브라우저별 고정 ID

# ========== 스타일/프롬프트 ==========
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

keyword_map = {
    "불안": "네가 불안하다고 한 부분, 그게 무겁게 느껴질 수 있어.",
    "외로움": "외로움이 마음을 꽉 채우면 정말 숨이 막히지.",
    "돈": "돈에 대한 불안은 누구에게나 가장 큰 무게야.",
    "미래": "미래가 안 보일 때 지금 한 발자국이 더 힘들지."
}

def build_prompt(user_input, style_choice):
    style = style_options[style_choice]
    empathy = "네가 말한 걸 듣고 나니까, 네 마음이 많이 힘들었을 것 같아."
    keyword_reply = next((r for k, r in keyword_map.items() if k in user_input), "네 말 속에 네 진심이 보여.")
    hope = style["ending"]

    system_prompt = f"""
    너는 {style['tone']} 상담사이자 재테크/수익화 전문가야.
    반드시 (공감 → 맞춤형 되돌려주기 → 희망 멘트)을 지켜서 답해.
    각 답변은 짧고 명확하게, 문단은 2~3문장.
    그리고 항상 지금 당장 할 수 있는 행동 3가지를 제시해.
    """
    user_prompt = f"""
    사용자 입력: {user_input}
    상담사 흐름:
    1. 공감: {empathy}
    2. 맞춤형 되돌려주기: {keyword_reply}
    3. 희망 멘트: {hope}
    """
    return system_prompt, user_prompt

def stream_reply(user_input: str, style_choice: str):
    system_prompt, user_prompt = build_prompt(user_input, style_choice)
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=700,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

# ========== UI ==========
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# CSS
st.markdown("""
<style>
.chat-message { font-size:22px; line-height:1.7; word-wrap:break-word; white-space:pre-wrap; }
</style>
""", unsafe_allow_html=True)

# 결제화면
def show_payment_screen():
    st.subheader("🚫 무료 체험이 끝났습니다")
    st.markdown("월 **3,900원** 결제 후 계속 이용할 수 있습니다.")
    st.markdown("---")
    st.markdown("### 🔗 결제 방법")
    st.markdown("[👉 페이팔 결제하기](https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4)")
    st.info("💡 결제 후 카톡(ID: jeuspo) 또는 이메일(mwiby91@gmail.com)로 닉네임/결제 스크린샷을 보내주시면 바로 이용 권한을 열어드립니다.")

# 스타일 선택
style_choice = st.sidebar.radio("오늘은 어떤 톤으로 위로받고 싶나요?", list(style_options.keys()))

# ========== Firestore 사용자 로딩 ==========
user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()

if snap.exists:
    data = snap.to_dict()
else:
    data = {"usage_count": 0, "limit": 4, "is_paid": False}
    user_ref.set(data)

# 세션 동기화(최초 1회만)
if "usage_count" not in st.session_state: st.session_state.usage_count = data.get("usage_count", 0)
if "limit" not in st.session_state:       st.session_state.limit = data.get("limit", 4)
if "is_paid" not in st.session_state:     st.session_state.is_paid = data.get("is_paid", False)
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# 게이트(결제 전환) 조건: 유료이거나, 무료잔여가 남아있으면 채팅 가능
can_chat = st.session_state.is_paid or (st.session_state.usage_count < st.session_state.limit)

# ========== 본문 ==========
if can_chat:
    user_input = st.chat_input("마음편히 얘기해봐")
    if user_input:
        st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)

        placeholder = st.empty()
        streamed = ""
        for chunk in stream_reply(user_input, style_choice):
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                streamed += delta.content
                placeholder.markdown(f"<div class='chat-message'>{streamed}</div>", unsafe_allow_html=True)

        st.session_state.chat_history.append((user_input, streamed))

        # 무료 유저만 카운트 증가
        if not st.session_state.is_paid:
            st.session_state.usage_count += 1
            user_ref.update({"usage_count": st.session_state.usage_count})

else:
    show_payment_screen()

# ========== 사이드바 ==========
st.sidebar.header("📜 대화 기록")
if st.session_state.chat_history:
    st.sidebar.markdown(f"**현재 사용 횟수:** {st.session_state.usage_count}/{st.session_state.limit} (유료:{st.session_state.is_paid})")
    for i, (q, a) in enumerate(st.session_state.chat_history):
        st.sidebar.markdown(f"**Q{i+1}:** {q[:20]}...")

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 관리자 메뉴")

admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
if admin_pw == "4321":
    col1, col2 = st.sidebar.columns(2)
    if col1.button("🔑 관리자(60회)"):
        st.session_state.limit = 60
        st.session_state.is_paid = True
        st.session_state.usage_count = 0
        user_ref.update({"limit": 60, "is_paid": True, "usage_count": 0})
        st.sidebar.success("관리자 모드 적용")
    if col2.button("🧹 쿠키초기화(테스트)"):
        # 브라우저에서 계정 초기화용(테스트용)
        del cookies["uid"]
        cookies.save()
        st.rerun()
else:
    st.sidebar.caption("관리자 전용 기능입니다.")
