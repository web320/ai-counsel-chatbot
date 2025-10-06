import os, uuid, json, random
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
st.set_page_config(page_title="당신을 위한 AI 친구", layout="wide")
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
.badge {
    display:inline-block; padding:4px 10px; border-radius:10px;
    background:#0f172a; color:#fff; margin-right:6px;
}
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# ===== SESSION =====
defaults = {
    "chat_history": [], "is_paid": False, "limit": 4, "usage_count": 0,
    "plan": None, "purchase_ts": None, "refund_until_ts": None,
    "sessions_since_purchase": 0, "refund_count": 0, "refund_requested": False,
    "tone": "따뜻하게", "reply_length": "짧게", "last_bot": ""
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

# ===== SIDEBAR: Settings & Progress =====
st.sidebar.header("🎛️ 대화 설정")
st.session_state.tone = st.sidebar.selectbox(
    "톤", ["따뜻하게", "담백하게", "유쾌하게"], index=["따뜻하게","담백하게","유쾌하게"].index(st.session_state.tone)
)
st.session_state.reply_length = st.sidebar.radio(
    "길이", ["짧게", "보통"], index=["짧게","보통"].index(st.session_state.reply_length), horizontal=True
)

if not st.session_state.is_paid:
    used = st.session_state.usage_count
    limit = st.session_state.limit
    remain = max(0, limit - used)
    st.sidebar.caption(f"무료 남은 회수: {remain}회 / {limit}회")
    try:
        st.sidebar.progress(min(1.0, used / max(1, limit)))
    except Exception:
        pass

# ===== Helper: Quick Actions (post-processing) =====
def _complete_once(sys, usr, max_tokens=200, temp=0.3):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=temp,
        max_tokens=max_tokens,
        messages=[{"role":"system","content":sys}, {"role":"user","content":usr}]
    )
    return r.choices[0].message.content.strip()

def action_summary(text: str) -> str:
    sys = "아래 내용을 한국어로 한 문장으로 아주 짧게 요약해줘. 군더더기 없이."
    return _complete_once(sys, text, max_tokens=80, temp=0.2)

def action_checklist(text: str) -> str:
    sys = "아래 조언을 근거로 오늘 실행할 체크리스트 3가지만 한국어 불릿(-)으로 간단히 써줘."
    return _complete_once(sys, text, max_tokens=120, temp=0.3)

def action_shorter(text: str) -> str:
    sys = "아래 내용을 핵심만 남기고 2문단 이내로 더 짧게, 따뜻한 톤으로 다시 써줘."
    return _complete_once(sys, text, max_tokens=220, temp=0.3)

# ===== GPT STREAM =====
def stream_reply(user_input: str):
    tone = st.session_state.get("tone", "따뜻하게")
    length = st.session_state.get("reply_length", "짧게")
    len_hint = "전체 3~5문장, 핵심만" if length == "짧게" else "문단 2~3개, 각 2~3문장"
    sys_prompt = f"""너는 다정하고 현실적인 심리상담사야.
- 구조: 공감 → 구체 조언 → 실천 제안 (원인분석 없음)
- 대화 톤: {tone}
- 길이 가이드: {len_hint}
- 쉬운 말로 짧게. 장황한 이론 설명 금지.
"""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=700 if length=="보통" else 520,
        stream=True,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input}
        ]
    )

# ===== CHAT PAGE =====
def render_chat_page():
    st.caption("마음 편히 얘기해 💬")

    # 무료 제한
    if not st.session_state.is_paid and st.session_state.usage_count >= st.session_state.limit:
        st.warning("🚫 무료 4회가 모두 사용되었습니다.")
        if st.button("💳 결제/FAQ로 이동"):
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()
        return

    # 빠른 시작 버튼 (입력 없이도 시작)
    with st.container():
        st.markdown(
            "<span class='badge'>빠른 시작</span> 원하는 걸 눌러서 바로 시작해요 👇",
            unsafe_allow_html=True
        )
        quicks = ["불안해요", "무기력해요", "잠이 안 와요", "관계가 힘들어요"]
        qcols = st.columns(len(quicks))
        quick_clicked = None
        for i, label in enumerate(quicks):
            if qcols[i].button(label):
                quick_clicked = label
        if quick_clicked:
            user_input = quick_clicked
        else:
            user_input = st.chat_input("지금 어떤 기분이야?")

    if not user_input:
        return

    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    placeholder, streamed = st.empty(), ""

    # 스트리밍 응답
    for chunk in stream_reply(user_input):
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            streamed += delta.content
            safe_stream = streamed.replace("\n\n", "<br><br>")
            placeholder.markdown(f"<div class='bot-bubble'>🧡 {safe_stream}</div>", unsafe_allow_html=True)

    st.session_state.last_bot = streamed
    st.session_state.chat_history.append((user_input, streamed))

    # 사용량 처리
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

    # ===== 답변 후 액션 버튼 =====
    st.markdown("---")
    a1, a2, a3, a4 = st.columns([1,1,1,1])
    if a1.button("📝 한줄요약"):
        st.info(action_summary(st.session_state.last_bot))
    if a2.button("📌 체크리스트"):
        st.success(action_checklist(st.session_state.last_bot))
    if a3.button("🔄 더 짧게"):
        st.warning(action_shorter(st.session_state.last_bot))
    if a4.download_button(
        "💾 대화 저장", data=st.session_state.last_bot, file_name=f"advice-{datetime.now().strftime('%Y%m%d-%H%M')}.txt"
    ):
        pass

    # ===== 피드백 저장 =====
    f1, f2 = st.columns(2)
    if f1.button("👍 도움됐어요"):
        try:
            db.collection("feedback").add({
                "uid": USER_ID, "ts": firestore.SERVER_TIMESTAMP,
                "rating": "up", "page": "chat"
            })
        except Exception:
            pass
        st.success("고마워요! 더 잘 도와볼게요.")
    if f2.button("👎 별로였어요"):
        try:
            db.collection("feedback").add({
                "uid": USER_ID, "ts": firestore.SERVER_TIMESTAMP,
                "rating": "down", "page": "chat"
            })
        except Exception:
            pass
        st.info("어떤 점이 아쉬웠을까요? 다음엔 더 부드럽게 도와볼게요.")

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

# ===== SIDEBAR NAV =====
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
