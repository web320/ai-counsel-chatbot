import os, uuid, json
from datetime import datetime
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
st.set_page_config(page_title="당신을 위한 AI 친구", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
[data-testid="stSidebar"] * { font-size: 18px !important; }

.user-bubble {
    background: #b91c1c;
    color: white;
    border-radius: 12px;
    padding: 10px 16px;
    margin: 8px 0;
    display: inline-block;
}

.bot-bubble {
    font-size: 21px;
    line-height: 1.8;
    border-radius: 14px;
    padding: 14px 18px;
    margin: 10px 0;
    background: rgba(15,15,30,0.85);
    color: #fff;
    border: 2px solid transparent;
    border-image: linear-gradient(90deg, #ff8800, #ffaa00, #ff8800) 1;
    animation: neon-glow 1.8s ease-in-out infinite alternate;
}

@keyframes neon-glow {
  from { box-shadow: 0 0 5px #ff8800, 0 0 10px #ffaa00; }
  to { box-shadow: 0 0 20px #ff8800, 0 0 40px #ffaa00, 0 0 60px #ff8800; }
}
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# ===== SESSION =====
defaults = {
    "chat_history": [], "is_paid": False, "limit": 4, "usage_count": 0,
    "plan": None, "tone": "따뜻하게"
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

# ===== GPT HELPER =====
def stream_reply(user_input: str, tone: str):
    sys_prompt = f"""
    너는 {tone} 말투의 심리상담사야.
    - 감정을 공감하고 → 구체적인 조언 → 실천 제안 순으로 3문단 이내로 답해.
    - 따뜻하고 현실적으로, 문장은 짧게 써줘.
    """
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=700,
        stream=True,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input}
        ]
    )

def make_summary(text: str):
    """마음 한 줄 요약 생성"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "사용자의 대화 내용을 요약해서 오늘의 마음 한 줄 명언처럼 만들어줘."},
            {"role": "user", "content": text}
        ]
    )
    return res.choices[0].message.content.strip()

# ===== CHAT PAGE =====
def render_chat_page():
    st.caption("마음 편히 얘기해 💬")

    # 상담 톤 선택
    tone = st.radio(
        "🎭 상담 톤을 선택해주세요:",
        ["따뜻하게", "직설적으로", "철학적으로"],
        horizontal=True,
        index=["따뜻하게", "직설적으로", "철학적으로"].index(st.session_state.tone)
    )
    st.session_state.tone = tone
    user_ref.update({"tone": tone})

    if not st.session_state.is_paid and st.session_state.usage_count >= st.session_state.limit:
        st.warning("🚫 무료 4회가 모두 사용되었습니다.")
        if st.button("💳 결제/FAQ로 이동"):
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()
        return

    user_input = st.chat_input("지금 어떤 기분이야?")
    if not user_input:
        return

    # 간단한 감정 반응 (피드백)
    mood_hint = ""
    if any(k in user_input for k in ["힘들", "피곤", "짜증", "불안", "우울"]):
        mood_hint = "💭 지금 마음이 많이 지쳐 있네요... 그래도 괜찮아요."
    elif any(k in user_input for k in ["행복", "좋아", "괜찮", "고마워"]):
        mood_hint = "🌤️ 그 기분, 참 소중하네요."
    if mood_hint:
        st.markdown(f"<div class='bot-bubble'>{mood_hint}</div>", unsafe_allow_html=True)

    # 사용자 입력 표시
    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    placeholder, streamed = st.empty(), ""

    # GPT 답변 스트리밍
    for chunk in stream_reply(user_input, tone):
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            streamed += delta.content
            safe_stream = streamed.replace("\n\n", "<br><br>")
            placeholder.markdown(f"<div class='bot-bubble'>🧡 {safe_stream}</div>", unsafe_allow_html=True)

    # 한 줄 요약
    summary = make_summary(user_input)
    st.markdown(f"<div class='bot-bubble'>💡 오늘의 마음 노트: <b>{summary}</b></div>", unsafe_allow_html=True)

    # 기록 저장
    st.session_state.chat_history.append((user_input, streamed, summary))

    if not st.session_state.is_paid:
        st.session_state.usage_count += 1
        user_ref.update({"usage_count": st.session_state.usage_count})
        if st.session_state.usage_count >= st.session_state.limit:
            st.success("무료 체험이 끝났어요. 결제 페이지로 이동합니다.")
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()

# ===== PLANS PAGE =====
def render_plans_page():
    st.markdown("""
    ### 💳 결제 안내 (예시)
    **:star: 베이직 60회 — $3**  
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
