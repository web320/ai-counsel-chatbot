# app.py — 최종(다정+영리, 3가지 행동 강제 없음)
import os, uuid, json
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# ========= OpenAI =========
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========= Firebase (Secrets robust) =========
import firebase_admin
from firebase_admin import credentials, firestore

def _firebase_config():
    """st.secrets['firebase']가 dict이든 JSON 문자열이든 지원"""
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

# ========= 전역 스타일 =========
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
h1 { font-size: 40px !important; } h2 { font-size: 28px !important; } h3 { font-size: 22px !important; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
div[role="radiogroup"] label { font-size: 18px !important; }
.chat-message { font-size: 22px; line-height: 1.7; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# ========= UID — URL에 저장(신규 API) =========
uid = st.query_params.get("uid")
if uid:
    USER_ID = uid
else:
    USER_ID = str(uuid.uuid4())
    st.query_params["uid"] = USER_ID

# ========= 상담 톤 옵션 =========
style_options = {
    "따뜻한 상담사": {"tone":"따뜻하고 부드럽게, 이해와 공감 최우선", "ending":"넌 지금도 충분히 잘하고 있어 🌷"},
    "친구처럼 솔직하게": {"tone":"친근하고 솔직하게, 친구가 옆에서 말해주는 듯", "ending":"네가 힘든 건 너무 당연해. 그래도 난 네 편이야 🤝"},
    "연예인처럼 다정하게": {"tone":"부드럽고 다정한 여성 연예인 말투", "ending":"오늘도 너 정말 멋지게 버텨줬어 ✨"},
}

# ========= 안전/의도 간단 감지 (위로 과잉 방지) =========
DANGEROUS = ["자살","죽고","죽고싶","해치","폭력","때리","살해","범죄","불법","마약","음란","노골적"]
COACH_KW = ["어떻게","방법","계획","추천","정리","수익","창업","투자","마케팅","습관","루틴","해결"]
VENT_KW  = ["힘들","불안","우울","외롭","걱정","짜증","화나","무기력","멘탈","지쳤"]

def decide_mode(text: str) -> str:
    if any(k in text for k in DANGEROUS): return "safety"
    if any(k in text for k in COACH_KW):  return "coach"
    if any(k in text for k in VENT_KW):   return "support"
    return "coach"  # 애매하면 실행 중심

# ========= 프롬프트(가벼운 규칙, 다정+영리) =========
def build_prompt(user_input, style_choice):
    style = style_options[style_choice]
    mode  = decide_mode(user_input)

    base = f"""
너는 {style['tone']}의 말투를 쓰는 상담사이자 재테크/수익화 코치다.
원칙: 사용자의 의도에 맞춰 '정확하고 현실적인 도움'을 준다.
- 문장은 자연스럽고 간결하게(2~5문장).
- 필요할 때만 다음 단계/선택지를 제안한다(강제 아님).
- 상투적 위로나 과장 금지. 애매하면 짧게 확인 질문 1개만.
- 마지막엔 {style['ending']} 같은 짧은 한 줄 희망 멘트 '선택적으로' 붙여라(상황에 어울릴 때만).
"""

    if mode == "safety":
        sys = base + """
[안전 모드]
- 자/타해·불법·폭력·노골적 성적 내용엔 경계와 안전 안내를 우선한다.
- 위기대응 불가 고지 + 즉시 도움 연결 제안(국번없이 1393/112, 가까운 응급실/신뢰할 보호자).
- 미화/정당화 금지. 위로는 절제.
"""
    elif mode == "support":
        sys = base + """
[감정 지지 모드]
- 짧은 공감 → 현실적인 시선/관점 전환 → 필요시 가벼운 제안.
"""
    else:  # coach
        sys = base + """
[코칭 모드]
- 방법/옵션/우선순위를 명확히 제시하되, 과도한 과제는 피한다.
"""

    user = f"""[사용자 입력]
{user_input}

위 지침에 맞춰 답해줘.
"""
    return sys, user

# ========= 생성(차분·집중) =========
def stream_reply(user_input: str, style_choice: str):
    sys, usr = build_prompt(user_input, style_choice)
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3, top_p=0.9,
        frequency_penalty=0.2, presence_penalty=0.0,
        max_tokens=700, stream=True,
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
    )

# ========= 사이드바 =========
style_choice = st.sidebar.radio("오늘 위로 톤", list(style_options.keys()))
st.sidebar.caption("내 UID (URL에 저장됨)")
st.sidebar.text_input(" ", value=USER_ID, disabled=True, label_visibility="collapsed")

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

# ========= 결제 화면 =========
def show_payment_screen():
    st.subheader("🚫 무료 체험이 끝났습니다")
    st.markdown("월 **3,900원** 결제 후 계속 이용할 수 있습니다.")
    st.markdown("[👉 페이팔 결제하기](https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4)")
    st.info("결제 후 카톡(ID: jeuspo) 또는 이메일(mwiby91@gmail.com)로 스크린샷을 보내주시면 바로 권한 열어드려요.")

# ========= 본문 =========
can_chat = st.session_state.is_paid or (st.session_state.usage_count < st.session_state.limit)

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
        if not st.session_state.is_paid:  # 무료일 때만 카운트
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
        st.query_params["uid"] = new_uid
        st.rerun()
else:
    st.sidebar.caption("관리자 전용")
