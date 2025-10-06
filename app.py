# app.py — 💙 AI 심리상담 챗봇 (관리자 모드 포함 완성판)
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
def apply_style(page: str):
    if page == "chat":
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
            white-space: pre-wrap;
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
    else:
        st.markdown("""
        <style>
        html, body, [class*="css"] { font-size: 18px; }
        .hero { padding:16px; border-radius:14px; background:rgba(80,120,255,0.08); margin-bottom:8px; }
        .badge { display:inline-block; padding:4px 8px; border-radius:8px; margin-right:6px; background:#1e293b; color:#fff; }
        .small { font-size:14px; opacity:.85; }
        </style>
        """, unsafe_allow_html=True)

apply_style(PAGE)
st.set_page_config(page_title="AI 심리상담 챗봇", layout="wide")
st.title("💙 ai심리상담 챗봇")

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
    sys_prompt = """너는 다정하고 현실적인 심리상담사야.
    - 감정 공감 → 원인 분석 → 구체 조언 → 실천 제안 순으로 4~7문단 구성.
    - 각 문단은 <p>로 구분.
    - 너무 짧지 않게, 진심이 느껴지게 써.
    - 필요시 전문상담 안내도 덧붙여.
    """
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.35,
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
            formatted = streamed.replace("\n\n", "</p><p>")
            placeholder.markdown(f"<div class='bot-bubble'>🧡 <p>{formatted}</p></div>", unsafe_allow_html=True)

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
    <div class='hero'>
      <h3>AI 고민상담, <b>4회 무료 체험</b> 이후 유료 플랜</h3>
      <div class='small'>
        <span class='badge'>60회 $3</span>
        <span class='badge'>140회 $6</span>
        <span class='badge'>4일내 환불 10회이하 사용시 </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💳 가격 / 결제")
        st.markdown("**⭐ 베이직 — 60회 / $3**\n\n4일내 환불 10회이하 사용시 언제든 해지")
        st.link_button("PayPal 결제 (60회)", "https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4", use_container_width=True)

        st.markdown("---")
        st.markdown("**💎 프로 — 140회 / $6**\n\n4일내 환불 10회이하 사용시 언제든 해지")
        st.link_button("PayPal 결제 (140회)", "https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4", use_container_width=True)

        # 관리자 비밀번호 확인
        st.markdown("---")
        st.markdown("#### 🔐 관리자 전용 테스트 적용")
        admin_pw = st.text_input("관리자 비밀번호", type="password", key="admin_pw")
        if admin_pw == "4321":
            st.success("관리자 인증 완료 ✅")
            if st.button("✅ 베이직 60회 적용"):
                now = datetime.utcnow()
                st.session_state.update({
                    "is_paid": True, "limit": 60, "usage_count": 0,
                    "purchase_ts": now, "refund_until_ts": now + timedelta(days=7)
                })
                user_ref.update(st.session_state)
                st.success("베이직 60회 적용 완료!")
            if st.button("✅ 프로 140회 적용"):
                now = datetime.utcnow()
                st.session_state.update({
                    "is_paid": True, "limit": 140, "usage_count": 0,
                    "purchase_ts": now, "refund_until_ts": now + timedelta(days=7)
                })
                user_ref.update(st.session_state)
                st.success("프로 140회 적용 완료!")
        elif admin_pw:
            st.error("❌ 비밀번호가 틀렸습니다.")

    with col2:
        st.markdown("### ❓ FAQ")
        with st.expander("사람 상담사가 보나요?"):
            st.write("아니요. 오직 AI만 응답하며, 데이터는 외부에 공유되지 않습니다.")
        with st.expander("무료 체험은 몇 회인가요?"):
            st.write("4회입니다. 결제 전 충분히 사용해보세요.")
        with st.expander("환불 규정은?"):
            st.write("첫 결제 후 7일 이내 100% 환불 가능합니다. (20회 이하 사용 시)")

    st.markdown("---")
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

