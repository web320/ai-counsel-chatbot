import os, uuid, json
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# ========= OpenAI =========
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========= Firebase (Secrets 어떤 형태든 안전 처리) =========
import firebase_admin
from firebase_admin import credentials, firestore

def _load_fb_cred_from_secrets():
    """
    st.secrets["firebase"] 가 dict이든, JSON 문자열이든 모두 지원.
    """
    raw = st.secrets.get("firebase")
    if raw is None:
        raise RuntimeError("Secrets에 [firebase]가 없습니다.")
    if isinstance(raw, str):
        # 사용자가 JSON 문자열로 넣어둔 경우
        return json.loads(raw)
    # TOML의 [firebase] 블록(dict)인 경우
    return dict(raw)

if not firebase_admin._apps:
    fb_conf = _load_fb_cred_from_secrets()
    cred = credentials.Certificate(fb_conf)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ========= UI 공통 =========
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# URL 파라미터로 사용자 ID를 고정 보관(쿠키 대신 → 새로고침/재접속 유지)
params = st.experimental_get_query_params()
if "uid" in params and params["uid"]:
    USER_ID = params["uid"][0]
else:
    USER_ID = str(uuid.uuid4())
    st.experimental_set_query_params(uid=USER_ID)

# ========= 상담 톤/프롬프트 =========
style_options = {
    "따뜻한 상담사": {"tone":"따뜻하고 부드럽게, 이해와 공감 최우선", "ending":"넌 지금도 충분히 잘하고 있어 🌷"},
    "친구처럼 솔직하게": {"tone":"친근하고 솔직하게, 옆자리 친구처럼", "ending":"네가 힘든 건 당연해. 그래도 난 네 편이야 🤝"},
    "연예인처럼 다정하게": {"tone":"부드럽고 다정한 여성 연예인 말투", "ending":"오늘도 정말 멋지게 버텨줬어 ✨"},
}
keyword_map = {
    "불안":"네가 불안하다고 한 부분, 그게 무겁게 느껴질 수 있어.",
    "외로움":"외로움이 마음을 꽉 채우면 정말 숨이 막히지.",
    "돈":"돈에 대한 불안은 누구에게나 큰 무게야.",
    "미래":"미래가 안 보일 때 지금 한 걸음이 더 힘들지.",
}

def build_prompt(user_input, style_choice):
    style = style_options[style_choice]
    empathy = "네가 말한 걸 들으니 마음이 많이 힘들었을 것 같아."
    keyword = next((r for k, r in keyword_map.items() if k in user_input), "네 말 속에 네 진심이 보여.")
    hope = style["ending"]
    sys = f"""
    너는 {style['tone']} 상담사이자 재테크/수익화 전문가야.
    (공감→맞춤형 되돌려주기→희망 멘트) 흐름을 지켜.
    답변은 짧고 명확하게, 문단 2~3문장. 마지막에 지금 당장 할 3가지 제시.
    """
    usr = f"""사용자 입력: {user_input}
1) 공감: {empathy}
2) 되돌려주기: {keyword}
3) 희망: {hope}"""
    return sys, usr

def stream_reply(user_input, style_choice):
    sys, usr = build_prompt(user_input, style_choice)
    return client.chat.completions.create(
        model="gpt-4o-mini", temperature=0.7, max_tokens=700, stream=True,
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}]
    )

# ========= 결제 화면 =========
def show_payment_screen():
    st.subheader("🚫 무료 체험이 끝났습니다")
    st.markdown("월 **3,900원** 결제 후 계속 이용할 수 있습니다.")
    st.markdown("[👉 페이팔 결제하기](https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4)")
    st.info("결제 후 카톡(ID: jeuspo) 또는 이메일(mwiby91@gmail.com)로 스크린샷을 보내주세요. 바로 권한 열어드려요.")

# ========= 사이드바(스타일/관리) =========
style_choice = st.sidebar.radio("오늘 위로 톤", list(style_options.keys()))
st.sidebar.caption(f"내 UID: `{USER_ID}` (URL로 저장됨)")

# ========= Firestore: 사용자 로딩/초기화 =========
user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict()
else:
    data = {"usage_count": 0, "limit": 4, "is_paid": False}
    user_ref.set(data)

# 세션 동기화
st.session_state.setdefault("usage_count", data.get("usage_count", 0))
st.session_state.setdefault("limit",       data.get("limit", 4))
st.session_state.setdefault("is_paid",     data.get("is_paid", False))
st.session_state.setdefault("chat_history", [])

# 결제/무료 게이트
can_chat = st.session_state.is_paid or (st.session_state.usage_count < st.session_state.limit)

# ========= 본문 =========
if can_chat:
    user_input = st.chat_input("마음편히 얘기해봐")
    if user_input:
        st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)
        placeholder, streamed = st.empty(), ""
        for chunk in stream_reply(user_input, style_choice):
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                streamed += delta.content
                placeholder.markdown(f"<div class='chat-message'>{streamed}</div>", unsafe_allow_html=True)

        st.session_state.chat_history.append((user_input, streamed))
        if not st.session_state.is_paid:
            st.session_state.usage_count += 1
            user_ref.update({"usage_count": st.session_state.usage_count})
else:
    show_payment_screen()

# ========= 사이드바: 기록/관리 =========
st.sidebar.header("📜 대화 기록")
if st.session_state.chat_history:
    st.sidebar.markdown(f"**사용 횟수:** {st.session_state.usage_count}/{st.session_state.limit} · 유료:{st.session_state.is_paid}")
    for i, (q, _) in enumerate(st.session_state.chat_history):
        st.sidebar.markdown(f"**Q{i+1}:** {q[:20]}...")

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 관리자 메뉴")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
col1, col2 = st.sidebar.columns(2)
if admin_pw == "4321":
    if col1.button("🔑 유료모드(60회)"):
        st.session_state.is_paid = True
        st.session_state.limit = 60
        st.session_state.usage_count = 0
        user_ref.update({"is_paid": True, "limit": 60, "usage_count": 0})
        st.sidebar.success("유료모드 적용!")
    if col2.button("🆕 새 UID(테스트)"):
        new_uid = str(uuid.uuid4())
        st.experimental_set_query_params(uid=new_uid)
        st.experimental_rerun()
else:
    st.sidebar.caption("관리자 전용")
