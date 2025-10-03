# app.py — 안정화 전체 버전
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

# ===== 앱 메타 =====
APP_VERSION = "v1.0.2"

# ===== 스타일 =====
st.set_page_config(page_title="AI 심리상담 챗봇", layout="wide")
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

# ===== UID & PAGE =====
uid_list = st.query_params.get("uid")
USER_ID = uid_list[0] if uid_list else str(uuid.uuid4())

page_list = st.query_params.get("page")
PAGE = page_list[0] if page_list else "chat"

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

# ===== 프롬프트 =====
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
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
        temperature=0.35,
        max_tokens=900
    )
    # 안전하게 응답 가져오기
    choice = resp.choices[0]
    if hasattr(choice, "message") and choice.message is not None:
        return choice.message.content
    elif hasattr(choice, "text"):
        return choice.text
    else:
        return "죄송해요, 답변을 가져오지 못했어요."

# ===== 무료/환불 유틸 =====
def remaining_free() -> int:
    return max(int(st.session_state.limit) - int(st.session_state.usage_count), 0)

def refund_eligible():
    if not st.session_state.is_paid or not st.session_state.purchase_ts: return False, "유료 결제 내역이 없습니다."
    if st.session_state.refund_requested: return False, "환불 요청이 이미 접수되었습니다."
    if st.session_state.refund_count >= 1: return False, "환불은 계정당 1회 가능합니다."
    try:
        until = datetime.fromisoformat(st.session_state.refund_until_ts) \
                if isinstance(st.session_state.refund_until_ts, str) else st.session_state.refund_until_ts
    except: until = None
    now = datetime.utcnow()
    if not until or now > until: return False, "환불 가능 기간(구매 후 7일)이 지났습니다."
    if st.session_state.sessions_since_purchase > 20: return False, "구매 후 20회 초과 사용 시 환불 제한."
    return True, "환불 가능"

# ===== 페이지 렌더링 =====
def render_chat_page():
    if not st.session_state.is_paid and remaining_free() == 0:
        st.info("🚫 무료 4회가 모두 사용되었습니다.")
        if st.button("💳 결제/FAQ 열기"):
            st.query_params["page"] = "plans"
            st.query_params["uid"] = USER_ID
            st.experimental_rerun()
        return

    user_input = st.chat_input("마음편히 얘기해봐")
    if not user_input: return

    st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)
    reply = stream_reply(user_input)
    st.markdown(f"<div class='chat-message'>{reply}</div>", unsafe_allow_html=True)

    st.session_state.chat_history.append((user_input, reply))

    if not st.session_state.is_paid:
        st.session_state.usage_count += 1
        user_ref.update({"usage_count": st.session_state.usage_count})
        if st.session_state.usage_count >= st.session_state.limit:
            st.success("무료 4회 체험 종료. 결제/FAQ로 이동합니다.")
            st.query_params["page"] = "plans"
            st.query_params["uid"] = USER_ID
            st.experimental_rerun()
    else:
        st.session_state.sessions_since_purchase += 1
        user_ref.update({"sessions_since_purchase": st.session_state.sessions_since_purchase})

# ===== 라우팅 =====
if PAGE == "plans":
    st.write("⚡ 결제/FAQ 페이지 구현")
else:
    render_chat_page()
