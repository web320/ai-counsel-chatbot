# app.py — 네온 효과는 채팅 화면에서만, 결제/FAQ는 단순 스타일
import os, uuid, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ===== OpenAI =====
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== Firebase =====
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

# ===== 페이지 정보 =====
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

# ===== 스타일 =====
def set_style(page: str):
    """페이지별로 다른 스타일 적용"""
    if page == "chat":
        st.markdown("""
        <style>
        html, body, [class*="css"] { font-size: 18px; }
        h1 { font-size: 40px !important; } 
        h2 { font-size: 28px !important; } 
        h3 { font-size: 22px !important; }
        [data-testid="stSidebar"] * { font-size: 18px !important; }

        .chat-message { 
            font-size: 22px; 
            line-height: 1.7; 
            white-space: pre-wrap;
            border-radius: 12px;
            padding: 10px 16px;
            margin: 6px 0;
            background: rgba(15,15,30,0.7);
            color: #fff;
            border: 2px solid transparent;
            border-image: linear-gradient(90deg, #ff00ff, #00ffff, #ff00ff) 1;
            animation: neon-glow 1.8s ease-in-out infinite alternate;
        }
        @keyframes neon-glow {
          from { box-shadow: 0 0 5px #ff00ff, 0 0 10px #00ffff; }
          to { box-shadow: 0 0 15px #ff00ff, 0 0 30px #00ffff, 0 0 45px #ff00ff; }
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        html, body, [class*="css"] { font-size: 18px; }
        h1 { font-size: 40px !important; } 
        h2 { font-size: 28px !important; } 
        h3 { font-size: 22px !important; }
        [data-testid="stSidebar"] * { font-size: 18px !important; }
        .hero { padding:16px; border-radius:14px; background:rgba(80,120,255,0.08); margin-bottom:8px; }
        .badge { display:inline-block; padding:4px 8px; border-radius:8px; margin-right:6px; background:#1e293b; color:#fff; }
        .small { font-size:14px; opacity:.85; }
        </style>
        """, unsafe_allow_html=True)

set_style(PAGE)
st.set_page_config(page_title="AI 심리상담 챗봇", layout="wide")
st.title("💙 AI 심리상담 챗봇")

# ===== 기본 세션 =====
defaults = {
    "chat_history": [], "is_paid": False, "limit": 4, "usage_count": 0,
    "plan": None, "purchase_ts": None, "refund_until_ts": None,
    "sessions_since_purchase": 0, "refund_count": 0, "refund_requested": False
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ===== Firestore 로드 =====
user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        st.session_state[k] = data.get(k, v)
else:
    user_ref.set(defaults)

# ===== 유틸 =====
def remaining_free():
    return max(st.session_state.limit - st.session_state.usage_count, 0)

# ===== Chat =====
def render_chat_page():
    st.caption("마음편히 얘기해봐")
    user_input = st.chat_input("무슨 일이 있었어?")
    if not user_input:
        return

    st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)
    response = f"🤖 {user_input}... (예시 답변)"
    st.markdown(f"<div class='chat-message'>{response}</div>", unsafe_allow_html=True)

    st.session_state.chat_history.append((user_input, response))
    if not st.session_state.is_paid:
        st.session_state.usage_count += 1
        user_ref.update({"usage_count": st.session_state.usage_count})
        if st.session_state.usage_count >= st.session_state.limit:
            st.info("무료 4회가 모두 사용되었습니다. 결제/FAQ로 이동합니다.")
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()

# ===== Plans =====
def render_plans_page():
    st.markdown("""
    <div class='hero'>
      <h3>AI 고민상담, <b>4회 무료 체험</b> 이후 유료 플랜</h3>
      <div class='small'>
        <span class='badge'>60회 $3</span>
        <span class='badge'>140회 $6</span>
        <span class='badge'>7일 전액 환불</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("💳 **베이직** — 60회 / $3\n\n✅ 7일 전액 환불 · 언제든 해지")
    if st.button("임시 적용(테스트)"):
        now = datetime.utcnow()
        st.session_state.update({
            "is_paid": True, "limit": 60, "usage_count": 0,
            "purchase_ts": now, "refund_until_ts": now + timedelta(days=7)
        })
        user_ref.update(st.session_state)
        st.success("적용 완료!")
    st.markdown("---")
    st.write("💡 **FAQ**\n- 무료 4회 제공\n- 7일 내 100% 환불 가능\n- 언제든 해지 가능")
    st.link_button("⬅ 채팅으로 돌아가기", f"?uid={USER_ID}&page=chat", use_container_width=True)

# ===== 사이드바 =====
st.sidebar.header("📜 대화 기록")
st.sidebar.caption("내 UID")
st.sidebar.text_input(" ", value=USER_ID, disabled=True, label_visibility="collapsed")

if PAGE == "chat":
    st.sidebar.link_button("💳 결제/FAQ 열기", f"?uid={USER_ID}&page=plans", use_container_width=True)
else:
    st.sidebar.link_button("⬅ 채팅으로 돌아가기", f"?uid={USER_ID}&page=chat", use_container_width=True)

# ===== 페이지 실행 =====
if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()
