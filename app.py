import os, uuid, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ===== OPENAI =====
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== FIREBASE =====
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

# ===== QUERY PARAM =====
def _qp_get(name: str, default=None):
    val = st.query_params.get(name)
    if isinstance(val, list): return val[0] if val else default
    return val or default

uid = _qp_get("uid")
page = _qp_get("page", "chat")
if not uid:
    uid = str(uuid.uuid4())
    st.query_params = {"uid": uid, "page": page}

USER_ID = uid
PAGE = page

# ===== STYLE =====
st.set_page_config(page_title="AI 심리상담 챗봇", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
.user-bubble {
    background: #b91c1c; color: white;
    border-radius: 12px; padding: 10px 16px;
    margin: 8px 0; display: inline-block;
}
.bot-bubble {
    font-size: 21px; line-height: 1.8;
    border-radius: 14px; padding: 14px 18px;
    margin: 10px 0; background: rgba(15,15,30,0.85);
    color: #fff; border: 2px solid transparent;
    border-image: linear-gradient(90deg, #ff8800, #ffaa00, #ff8800) 1;
    animation: neon-glow 1.8s ease-in-out infinite alternate;
}
@keyframes neon-glow {
  from { box-shadow: 0 0 5px #ff8800, 0 0 10px #ffaa00; }
  to { box-shadow: 0 0 20px #ff8800, 0 0 40px #ffaa00, 0 0 60px #ff8800; }
}
</style>
""", unsafe_allow_html=True)
st.title("💙 AI 심리상담 챗봇")

# ===== SESSION =====
defaults = {
    "chat_history": [], "is_paid": False, "limit": 4, "usage_count": 0,
    "plan": None, "purchase_ts": None, "refund_until_ts": None,
    "sessions_since_purchase": 0, "refund_count": 0, "refund_requested": False
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        st.session_state[k] = data.get(k, v)
else:
    user_ref.set(defaults)

# ===== GPT STREAM =====
def stream_reply(user_input: str):
    sys_prompt = """너는 다정하고 마음 아픈이들을 위로해주는 전문 심리 상담사야.
    - 감정을 어루만져주고 → 실천 제안 으로 구성.
    - 문단마다 공백 줄로 구분."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=900,
        stream=True,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input}
        ]
    )

# ===== CHAT PAGE =====
def render_chat_page():
    st.caption("마음 편히 얘기해 💬")

    if not st.session_state.is_paid and st.session_state.usage_count >= st.session_state.limit:
        st.warning("🚫 무료 4회가 모두 사용되었습니다.")
        if st.button("💳 결제/FAQ로 이동"):
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()
        return

    user_input = st.chat_input("지금 어떤 기분이야?")
    if not user_input:
        return

    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    placeholder, streamed = st.empty(), ""

    for chunk in stream_reply(user_input):
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            streamed += delta.content
            safe_stream = streamed.replace("\n\n", "<br><br>")
            placeholder.markdown(f"<div class='bot-bubble'>🧡 {safe_stream}</div>", unsafe_allow_html=True)

    st.session_state.chat_history.append((user_input, streamed))

    if not st.session_state.is_paid:
        st.session_state.usage_count += 1
        user_ref.update({"usage_count": st.session_state.usage_count})
        if st.session_state.usage_count >= st.session_state.limit:
            st.success("무료 체험이 끝났어요. 결제 페이지로 이동합니다.")
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()
    else:
        st.session_state.sessions_since_purchase += 1
        user_ref.update({"sessions_since_purchase": st.session_state.sessions_since_purchase})

# ===== PLANS PAGE =====
def render_plans_page():
    st.markdown("""
    ### 💳 결제 안내 (예시)
    **⭐ 베이직 60회 — $3**
    **💎 프로 140회 — $6**
    <p style='opacity:0.7;'>현재는 예시 모드이며 실제 결제는 진행되지 않습니다.</p>
    """, unsafe_allow_html=True)

    admin_pw = st.text_input("관리자 비밀번호", type="password")
    if admin_pw == "4321":
        st.success("관리자 인증 완료 ✅")
        if st.button("✅ 베이직 60회 적용"):
            st.session_state.update({"is_paid": True, "limit": 60, "usage_count": 0})
            user_ref.update(st.session_state)
            st.success("베이직 60회 적용 완료!")
        if st.button("✅ 프로 140회 적용"):
            st.session_state.update({"is_paid": True, "limit": 140, "usage_count": 0})
            user_ref.update(st.session_state)
            st.success("프로 140회 적용 완료!")

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ===== SIDEBAR =====
st.sidebar.header("📜 대화 기록")
st.sidebar.text_input(" ", value=USER_ID, disabled=True, label_visibility="collapsed")

if PAGE == "chat":
    if st.sidebar.button("💳 결제/FAQ 열기"):
        st.query_params = {"uid": USER_ID, "page": "plans"}
        st.rerun()
else:
    if st.sidebar.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ===== MAIN =====
if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()
