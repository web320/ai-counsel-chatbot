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
st.set_page_config(page_title="AI 심리상담 챗봇", layout="wide")
def apply_style(page: str):
    if page == "chat":
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
st.title("💙 AI 심리상담 챗봇")

# ===== SESSION =====
defaults = {
    "chat_history": [], "is_paid": False, "limit": 4, "usage_count": 0,
    "plan": None, "purchase_ts": None, "refund_until_ts": None,
    "sessions_since_purchase": 0, "refund_count": 0, "refund_requested": False,
    "mood_score": 0, "chat_days": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        st.session_state[k] = data.get(k, v)
else:
    user_ref.set(defaults)

# ===== UTIL =====
def analyze_mood(text: str) -> int:
    positive = ["좋다", "괜찮", "행복", "감사", "기대", "사랑", "희망", "편안"]
    negative = ["힘들", "슬프", "우울", "불안", "짜증", "화나", "지치", "외롭"]
    pos_count = sum(w in text for w in positive)
    neg_count = sum(w in text for w in negative)
    score = 50 + (pos_count - neg_count) * 10
    return max(0, min(100, score))

def get_quote():
    quotes = [
        "🌿 마음이 무거울 땐, 잠시 멈춰 숨을 고르세요.",
        "🌙 완벽하지 않아도 괜찮아요. 꾸준히 걷고 있으니까요.",
        "☕ 작은 평온이 쌓이면 큰 행복이 됩니다.",
        "💫 오늘의 당신은 어제보다 단단해졌어요.",
        "🌸 마음이 힘들면, 그건 당신이 열심히 살아온 증거예요."
    ]
    return random.choice(quotes)

def get_random_prompt():
    prompts = [
        "요즘 마음이 복잡한가요?",
        "최근에 잠은 잘 자고 있어요?",
        "오늘 하루는 어땠어요?",
        "지금 당신의 기분을 표현한다면?",
        "최근에 마음에 남은 일이 있나요?"
    ]
    return random.choice(prompts)

# ===== GPT STREAM =====
def stream_reply(user_input: str):
    sys_prompt = """너는 다정하고 현실적인 심리상담사야.
    - 감정 공감 → 원인 분석 → 구체 조언 → 실천 제안 순으로 4~7문단 구성.
    - 각 문단은 명확히 구분되며, 너무 짧지 않게 작성.
    - 각 섹션 앞에 이모지를 붙여 구분할 것.
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

    # 무료 제한 확인
    if not st.session_state.is_paid and st.session_state.usage_count >= st.session_state.limit:
        st.warning("🚫 무료 4회가 모두 사용되었습니다.")
        if st.button("💳 결제/FAQ로 이동"):
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()
        return

    # 질문 입력
    user_input = st.chat_input(get_random_prompt())
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

    # === 감정 분석 & 통계 ===
    mood_score = analyze_mood(user_input + streamed)
    st.session_state.mood_score = (st.session_state.mood_score + mood_score) / 2
    today = datetime.now().strftime("%Y-%m-%d")

    # 🔧 리스트/셋 혼용 대응
    if isinstance(st.session_state.chat_days, list):
        if today not in st.session_state.chat_days:
            st.session_state.chat_days.append(today)
    else:
        st.session_state.chat_days.add(today)

    user_ref.update({
        "usage_count": st.session_state.usage_count + 1,
        "mood_score": st.session_state.mood_score,
        "chat_days": list(st.session_state.chat_days)
    })

    # === 통계 카드 ===
    st.markdown("---")
    st.markdown(f"🌤 **오늘까지 {len(st.session_state.chat_days)}일째 마음을 기록했어요.**")
    st.markdown(f"💖 **당신의 평균 마음 안정도:** {int(st.session_state.mood_score)}점 / 100점")
    st.markdown(f"🪞 오늘의 메시지: _{get_quote()}_")

    # === 사용 제한 처리 ===
    if not st.session_state.is_paid:
        st.session_state.usage_count += 1
        if st.session_state.usage_count >= st.session_state.limit:
            st.success("무료 체험이 끝났어요. 결제 페이지로 이동합니다.")
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.rerun()

# ===== PLANS PAGE =====
def render_plans_page():
    st.markdown("""
    <div class='hero'>
      <h3>AI 고민상담, <b>4회 무료 체험</b> 이후 유료 플랜 (예시)</h3>
      <div class='small'>
        <span class='badge'>60회 $3</span>
        <span class='badge'>140회 $6</span>
        <span class='badge'>7일 전액 환불</span>
      </div>
      <p style='opacity:0.8;'>💡 현재는 테스트 예시 모드입니다. 결제 버튼을 눌러도 실제 결제로 연결되지 않습니다.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💳 가격 / 결제 (예시)")
        st.markdown("**⭐ 베이직 — 60회 / $3**\n\n7일 환불 · 언제든 해지")
        st.button("💰 예시 결제 버튼 (동작 안 함)", key="fake60")
        st.markdown("---")
        st.markdown("**💎 프로 — 140회 / $6**\n\n7일 환불 · 언제든 해지")
        st.button("💰 예시 결제 버튼 (동작 안 함)", key="fake140")

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
