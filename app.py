# app.py — AI 심리상담 챗봇 (채팅 ↔ 결제/FAQ)
# - 무료 4회 정확히 차감
# - 4회 소진 시 자동 결제/FAQ 페이지 이동
# - 콜백 내부 rerun 경고 제거

import os, uuid, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# ===== OpenAI =====
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== Firebase =====
import firebase_admin
from firebase_admin import credentials, firestore

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

# ===== 스타일 =====
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
h1 { font-size: 40px !important; } h2 { font-size: 28px !important; } h3 { font-size: 22px !important; }
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

st.title("💙 AI 심리상담 챗봇")
st.caption("마음편히 얘기해")

# ===== 유틸 =====
def build_url(page: str) -> str:
    uid = st.query_params.get("uid") or str(uuid.uuid4())
    return f"?uid={uid}&page={page}"

def get_payment_url(plan_key: str) -> str:
    default_url = "https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4"
    pay = st.secrets.get("payments", {})
    if isinstance(pay, dict):
        return pay.get(f"{plan_key}_url", default_url)
    return default_url

# ===== UID & PAGE =====
USER_ID = st.query_params.get("uid") or str(uuid.uuid4())
PAGE = st.query_params.get("page") or "chat"

# ===== 세션 기본값 =====
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
    data = snap.to_dict()
    for k, v in defaults.items():
        st.session_state[k] = data.get(k, v)
else:
    user_ref.set(defaults)

# ===== 키워드 기반 모드 결정 =====
DANGEROUS = ["자살","죽고","죽고싶","해치","폭력","때리","살해","범죄","불법","마약","음란","노골적"]
COACH_KW  = ["어떻게","방법","계획","추천","정리","수익","창업","투자","마케팅","습관","루틴","해결"]
VENT_KW   = ["힘들","불안","우울","외롭","걱정","짜증","화나","무기력","멘탈","지쳤"]
KEYWORD_HINTS = {"불안":"네가 불안하다고 말한 부분","외로움":"외로움이 마음을 꽉 채우는 느낌",
                 "돈":"돈에 대한 걱정","미래":"미래가 흐릿하게 느껴지는 점"}

def decide_mode(text: str) -> str:
    if any(k in text for k in DANGEROUS): return "safety"
    if any(k in text for k in COACH_KW):  return "coach"
    if any(k in text for k in VENT_KW):   return "support"
    return "coach"

def build_prompt(user_input: str):
    mode = decide_mode(user_input)
    hint = next((v for k, v in KEYWORD_HINTS.items() if k in user_input), "")
    base = """
너는 따뜻하고 다정하지만 과장하지 않는 상담사이자, 현실적인 재테크/수익화 코치다.
원칙:
- 답변은 4~7문장 정도로 조금 길게.
- 사용자가 방금 쓴 표현/키워드 1개 이상을 자연스럽게 포함.
- 상투적 위로는 줄이고, 맥락 맞는 공감+제안.
- 확인 질문은 최대 1개.
"""
    if mode == "safety":
        sys = base + """
[안전 모드]
- 자/타해·불법·폭력·노골적 성적 내용엔 '경계+안전안내' 우선.
- 위기대응 불가 고지 + 즉시 도움 연결(1393/112, 응급실/보호자).
- 미화 금지, 구체적 탈출 행동 제시.
"""
    elif mode == "support":
        sys = base + """
[감정 지지 모드]
- 짧은 공감으로 시작, 현실적 관점 전환과 작게 시도할 제안.
"""
    else:
        sys = base + """
[코칭 모드]
- 목표/옵션/우선순위를 분명히, 바로 적용 팁 중심.
"""
    usr = f"[사용자 입력]\n{user_input}\n\n[참고 힌트]\n{hint}\n\n위 지침에 맞춰 답해줘."
    return sys, usr

def stream_reply(user_input: str):
    sys, usr = build_prompt(user_input)
    return client.chat.completions.create(
        model="gpt-4o-mini", temperature=0.35, top_p=0.9,
        frequency_penalty=0.2, presence_penalty=0.0,
        max_tokens=900, stream=True,
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
    )

# ===== 무료/환불 =====
def remaining_free() -> int:
    return max(int(st.session_state.limit) - int(st.session_state.usage_count), 0)

def refund_eligible():
    if not st.session_state.is_paid or not st.session_state.purchase_ts:
        return False, "유료 결제 내역이 없습니다."
    if st.session_state.refund_requested:
        return False, "환불 요청이 이미 접수되었습니다."
    if st.session_state.refund_count >= 1:
        return False, "환불은 계정당 1회 가능합니다."
    try:
        until = (datetime.fromisoformat(st.session_state.refund_until_ts)
                 if isinstance(st.session_state.refund_until_ts, str)
                 else st.session_state.refund_until_ts)
    except Exception:
        until = None
    now = datetime.utcnow()
    if not until or now > until:
        return False, "환불 가능 기간(구매 후 7일)이 지났습니다."
    if st.session_state.sessions_since_purchase > 20:
        return False, "구매 후 20회 초과 사용 시 환불 제한."
    return True, "환불 가능"

# ===== 페이지: 채팅 =====
def render_chat_page():
    if not st.session_state.is_paid and remaining_free() == 0:
        st.info("🚫 무료 4회가 모두 사용되었습니다.")
        st.button("💳 결제/FAQ 열기", on_click=lambda: st.experimental_set_query_params(uid=USER_ID, page="plans"))
        return

    user_input = st.chat_input("마음편히 얘기해봐")
    if not user_input:
        return

    st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)
    placeholder, streamed = st.empty(), ""
    for chunk in stream_reply(user_input):
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            streamed += delta.content
            placeholder.markdown(f"<div class='chat-message'>{streamed}</div>", unsafe_allow_html=True)

    st.session_state.chat_history.append((user_input, streamed))

    if not st.session_state.is_paid:
        st.session_state.usage_count += 1
        user_ref.update({"usage_count": st.session_state.usage_count})
        if st.session_state.usage_count >= st.session_state.limit:
            st.success("무료 4회 체험이 종료되었습니다. 결제/FAQ로 이동합니다.")
            st.experimental_set_query_params(uid=USER_ID, page="plans")
            st.rerun()
    else:
        st.session_state.sessions_since_purchase += 1
        user_ref.update({"sessions_since_purchase": st.session_state.sessions_since_purchase})

# ===== 페이지: 결제/FAQ/문의 =====
def render_plans_page():
    st.markdown("""
### AI 고민상담, 4회 무료 체험 이후 유료 플랜
- **⭐ 베이직** — 60회 / $3 (7일 전액 환불)
- **💎 프로** — 140회 / $6 (7일 전액 환불)
""")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("PayPal 결제 (60회)"):
            st.write("결제 페이지 이동")
        if st.button("✅ 임시 적용(테스트 60회)"):
            now = datetime.utcnow()
            st.session_state.update({
                "is_paid": True, "limit": 60, "usage_count": 0, "plan": "p60",
                "purchase_ts": now, "refund_until_ts": now + timedelta(days=7),
                "sessions_since_purchase": 0
            })
            user_ref.update(st.session_state)
            st.success("베이직 60회 적용!")

        if st.button("PayPal 결제 (140회)"):
            st.write("결제 페이지 이동")
        if st.button("✅ 임시 적용(테스트 140회)"):
            now = datetime.utcnow()
            st.session_state.update({
                "is_paid": True, "limit": 140, "usage_count": 0, "plan": "p140",
                "purchase_ts": now, "refund_until_ts": now + timedelta(days=7),
                "sessions_since_purchase": 0
            })
            user_ref.update(st.session_state)
            st.success("프로 140회 적용!")

    st.markdown("---")
    st.markdown("### 💡 개선 의견 남기기")
    with st.form("feedback_form", clear_on_submit=True):
        fb = st.text_area("앱 개선 의견", height=120)
        submitted_fb = st.form_submit_button("보내기")
        if submitted_fb:
            if fb.strip():
                db.collection("feedback").add({
                    "user_id": USER_ID,
                    "feedback": fb.strip(),
                    "page": PAGE,
                    "app_version": "v1.0.0",
                    "ts": datetime.utcnow()
                })
                st.success("💌 의견 저장 완료")
            else:
                st.warning("내용을 입력해주세요.")

    st.button("⬅ 채팅으로 돌아가기", on_click=lambda: st.experimental_set_query_params(uid=USER_ID, page="chat"))

# ===== 사이드바 =====
st.sidebar.header("📜 대화 기록")
st.sidebar.text_input("UID", value=USER_ID, disabled=True, label_visibility="collapsed")
if st.session_state.is_paid:
    st.sidebar.markdown("**유료 상태:** 예")
else:
    st.sidebar.markdown(f"**남은 무료:** {remaining_free()} / 4회 · **유료:** 아니오")

if st.session_state.chat_history:
    st.sidebar.markdown("---")
    for i, (q, _) in enumerate(st.session_state.chat_history[::-1][:30], 1):
        st.sidebar.markdown(f"**Q{len(st.session_state.chat_history)-i+1}:** {q[:20]}...")

st.sidebar.markdown("---")
if PAGE == "chat":
    st.sidebar.button("💳 결제/FAQ 열기", on_click=lambda: st.experimental_set_query_params(uid=USER_ID, page="plans"))
else:
    st.sidebar.button("⬅ 채팅으로 돌아가기", on_click=lambda: st.experimental_set_query_params(uid=USER_ID, page="chat"))

# ===== 관리자 =====
st.sidebar.subheader("🔧 관리자")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
if admin_pw == "4321":
    if st.sidebar.button("유료모드(60회) 적용"):
        now = datetime.utcnow()
        st.session_state.update({
            "is_paid": True, "limit": 60, "usage_count": 0, "plan": "p60",
            "purchase_ts": now, "refund_until_ts": now + timedelta(days=7),
            "sessions_since_purchase": 0
        })
        user_ref.update(st.session_state)
        st.sidebar.success("적용 완료")
else:
    st.sidebar.caption("관리자 전용")

# ===== 페이지 렌더링 =====
if PAGE == "chat":
    render_chat_page()
else:
    render_plans_page()
