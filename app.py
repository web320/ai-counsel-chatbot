# app.py — 채팅(기본) ↔ 결제/FAQ 화면(사이드바에서 이동)
# - 무료 4회 정확히 차감
# - 4회 소진 즉시 결제/FAQ 화면으로 자동 이동
# - 콜백 내부 rerun 없음(경고 제거)

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

st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# ===== 라우팅 유틸(링크 전용) =====
def build_url(page: str) -> str:
    uid = USER_ID
    st.experimental_set_query_params(uid=uid, page=page)
    return f"?uid={uid}&page={page}"

def get_payment_url(plan_key: str) -> str:
    default_url = "https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4"
    pay = st.secrets.get("payments", {})
    if isinstance(pay, dict):
        return pay.get(f"{plan_key}_url", default_url)
    return default_url

# ===== UID & PAGE =====
uid_param = st.query_params.get("uid", [None])[0]
if uid_param:
    USER_ID = uid_param
else:
    USER_ID = str(uuid.uuid4())
    st.experimental_set_query_params(uid=USER_ID)

page_param = st.query_params.get("page", [None])[0]
PAGE = page_param or "chat"

# ===== 세션 기본 =====
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

# ===== 분류/프롬프트 =====
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

# ===== 무료/환불 유틸 =====
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

# ===== 페이지 렌더링 및 로직 =====
# --- 생략: 이전 코드 그대로 사용, 단 st.query_params["..."]=... 부분 모두 st.experimental_set_query_params로 교체 ---

