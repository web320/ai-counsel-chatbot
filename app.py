import os
import uuid
import json
import hmac
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ========= 앱 설정 =========
APP_VERSION = "v1.2.1"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
FEEDBACK_COLLECTION = "feedback"
FREE_LIMIT = 4
PAID_LIMIT = 30
DEFAULT_TONE = "따뜻하게"
DEFAULT_ADMIN_KEY = "6U4urDCJLr7D0EWa4nST"

# ========= OpenAI =========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ========= Firebase Admin =========
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

# ===== ADMIN KEY =====
ADMIN_KEY = st.secrets.get("ADMIN_KEY") or os.getenv("ADMIN_KEY") or "4321"
def check_admin(pw: str) -> bool:
    return hmac.compare_digest(str(pw or ""), str(ADMIN_KEY))

# ========= URL 파라미터 =========
def _qp_get(name: str, default=None):
    val = st.query_params.get(name)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

uid = _qp_get("uid")
page = _qp_get("page", "chat")
if not uid:
    uid = str(uuid.uuid4())
    st.query_params = {"uid": uid, "page": page}
USER_ID = uid
PAGE = page

# ========= 공통 스타일 =========
st.set_page_config(page_title="당신의 마음을 어루만지는 AI 친구", layout="wide")
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<style>
body { background: linear-gradient(to bottom, #e6f3ff, #f0f9ff); }
.stButton>button { 
    background: #3b82f6; 
    color: white; 
    border-radius: 8px; 
    padding: 12px 24px; 
    font-weight: bold; 
    transition: all 0.3s ease; 
}
.stButton>button:hover { background: #2563eb; transform: scale(1.05); }
.stTextInput>div>input { 
    border: 2px solid #93c5fd; 
    border-radius: 8px; 
    padding: 10px; 
}
.stTextArea textarea { 
    border: 2px solid #93c5fd; 
    border-radius: 8px; 
    padding: 10px; 
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="text-center py-6">
    <h1 class="text-4xl font-bold text-blue-600">💙 당신의 마음을 어루만지는 AI 친구</h1>
    <p class="text-lg text-gray-600 mt-2">언제나 곁에서 따뜻하게 위로하고, 현실적인 조언을 건네는 친구</p>
</div>
""", unsafe_allow_html=True)

# ========= 세션 =========
defaults = {
    "chat_history": [],
    "is_paid": False,
    "limit": FREE_LIMIT,
    "usage_count": 0,
    "plan": None,
    "remaining_paid_uses": 0,
    "is_admin": False,
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

# ========= GPT 스트림 =========
def stream_reply(user_input: str):
    if client is None:
        st.error("OPENAI_API_KEY가 설정되어 있지 않습니다.")
        return
    sys_prompt = f"""
    너는 {DEFAULT_TONE} 말투의 심리상담사야. 
    - 공감 → 구체 조언 → 실천 제안, 3문단 이내.
    - 현실적이고 짧게.
    """
    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            max_tokens=600,
            stream=True,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0], "delta", None)
            if delta and getattr(delta, "content", None):
                yield delta.content
    except Exception as e:
        st.error("OpenAI 응답 오류")
        st.code(str(e))

# ========= 결제 CTA =========
def show_paypal_button(message):
    st.markdown(f"""
    <div class="bg-yellow-100 border-l-4 border-yellow-500 p-4 rounded-lg my-4">
        <p class="text-yellow-700 font-semibold">{message}</p>
        <p class="text-gray-600 mt-2">💙 단 3달러로 30회의 따뜻한 상담을 이어갈 수 있어요!</p>
        <a href="{PAYPAL_URL}" target="_blank">
            <button class="bg-blue-500 text-white px-6 py-3 rounded-lg mt-4 hover:bg-blue-600 transition-all duration-300">
                💳 PayPal로 결제하기 ($3)
            </button>
        </a>
        <p class="text-gray-600 mt-2">결제 후 카카오톡 jeuspo 또는 이메일 mwiby91@gmail.com으로 스크린샷을 보내주세요. 관리자 비밀번호를 바로 알려드립니다!</p>
    </div>
    """, unsafe_allow_html=True)

# ========= 피드백 저장(확정 저장) =========
def save_feedback(uid: str, text: str, page_name: str):
    try:
        content = (text or "").strip()
        if not content:
            st.warning("내용을 입력해주세요 😊")
            return None
        doc = {
            "user_id": uid,
            "feedback": content,
            "app_version": APP_VERSION,
            "page": page_name,
            "ts": datetime.now(timezone.utc).isoformat()
        }
        ref = db.collection(FEEDBACK_COLLECTION).add(doc)[1]
        st.success("피드백이 저장되었어요 💙")
        st.info(f"문서 ID: {ref.id}")
        return ref.id
    except Exception as e:
        st.error("피드백 저장 실패")
        st.code(str(e))
        return None

# ========= 채팅 페이지 =========
def render_chat_page():
    # 이용 제한
    if st.session_state.is_paid:
        remaining = st.session_state.remaining_paid_uses
        st.markdown(f"""
        <div class="text-center bg-blue-50 p-3 rounded-lg">
            <p class="text-blue-600 font-semibold">💎 남은 상담 횟수: {remaining}회 / {st.session_state.limit}회</p>
        </div>
        """, unsafe_allow_html=True)
        if remaining <= 0:
            show_paypal_button("💳 이용권이 모두 소진되었습니다. 새로 결제 후 따뜻한 상담을 이어가세요!")
            return
    else:
        if st.session_state.usage_count >= st.session_state.limit:
            show_paypal_button("🌱 무료 체험이 모두 끝났어요. 유료 이용권으로 더 깊은 대화를 나눠보세요!")
            return
        st.markdown(f"""
        <div class="text-center bg-green-50 p-3 rounded-lg">
            <p class="text-green-600 font-semibold">🌱 무료 체험 남은 횟수: {st.session_state.limit - st.session_state.usage_count}회</p>
        </div>
        """, unsafe_allow_html=True)

    # 입력
    user_input = st.chat_input("지금 어떤 기분이 드시나요? 마음을 나눠주세요 😊")
    if not user_input:
        return

    # 라이트 감정 힌트
    if any(k in user_input for k in ["힘들", "피곤", "짜증", "불안", "우울"]):
        st.markdown("""
        <div class="bg-blue-100 p-3 rounded-lg my-2">
            💭 마음이 많이 무거우시네요... 괜찮아요, 제가 곁에 있을게요.
        </div>
        """, unsafe_allow_html=True)
    elif any(k in user_input for k in ["행복", "좋아", "괜찮", "고마워"]):
        st.markdown("""
        <div class="bg-green-100 p-3 rounded-lg my-2">
            🌤️ 그 기분, 정말 소중해요! 계속 함께 나눠요.
        </div>
        """, unsafe_allow_html=True)

    # 대화 스트림
    st.markdown(f"""
    <div class="bg-gray-100 p-4 rounded-lg my-2">
        <p class="text-gray-700">😔 {user_input}</p>
    </div>
    """, unsafe_allow_html=True)
    placeholder, streamed = st.empty(), ""
    for token in stream_reply(user_input):
        streamed += token
        placeholder.markdown(f"""
        <div class="bg-blue-50 p-4 rounded-lg">
            <p class="text-blue-600">🧡 {streamed.replace('\\n\\n','<br><br>')}</p>
        </div>
        """, unsafe_allow_html=True)

    # 기록/차감
    st.session_state.chat_history.append((user_input, streamed))
    if st.session_state.is_paid:
        st.session_state.remaining_paid_uses -= 1
        user_ref.update({"remaining_paid_uses": st.session_state.remaining_paid_uses})
    else:
        st.session_state.usage_count += 1
        user_ref.update({"usage_count": st.session_state.usage_count})

    # 체험 종료 CTA
    if not st.session_state.is_paid and st.session_state.usage_count >= st.session_state.limit:
        show_paypal_button("🌱 무료 체험이 끝났어요. 단 3달러로 더 깊은 대화를 이어가세요!")

    # 피드백
    st.markdown("<div class='my-6'></div>", unsafe_allow_html=True)
    st.subheader("📝 대화에 대한 피드백을 남겨주세요")
    fb = st.text_area("좋았던 점이나 아쉬운 점을 알려주세요!", placeholder="예: 위로가 정말 따뜻했어요 / 답변이 조금 더 구체적이면 좋겠어요")
    if st.button("📩 피드백 보내기"):
        if fb and fb.strip():
            save_feedback(USER_ID, fb, "chat")
        else:
            st.warning("내용을 입력해주세요 😊")

# ========= 결제/플랜 페이지 =========
def render_plans_page():
    st.markdown("""
    <div class="text-center py-6">
        <h2 class="text-3xl font-bold text-blue-600">💙 당신의 마음을 위한 플랜</h2>
        <p class="text-lg text-gray-600 mt-2">지금 결제하고 더 깊은 대화를 시작하세요!</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 my-6">
        <div class="bg-white p-6 rounded-lg shadow-lg text-center">
            <h3 class="text-2xl font-semibold text-blue-600">⭐ 베이직 플랜</h3>
            <p class="text-4xl font-bold text-gray-800 mt-2">$3</p>
            <p class="text-gray-600 mt-2">30회 상담 이용권</p>
            <p class="text-gray-500 mt-2">필요할 때마다 따뜻한 위로를</p>
            <a href="{PAYPAL_URL}" target="_blank">
                <button class="bg-blue-500 text-white px-6 py-3 rounded-lg mt-4 hover:bg-blue-600 transition-all duration-300">
                    💳 지금 결제하기
                </button>
            </a>
        </div>
        <div class="bg-white p-6 rounded-lg shadow-lg text-center opacity-75">
            <h3 class="text-2xl font-semibold text-blue-600">💎 프로 플랜</h3>
            <p class="text-4xl font-bold text-gray-800 mt-2">$6</p>
            <p class="text-gray-600 mt-2">100회 상담 이용권</p>
            <p class="text-gray-500 mt-2">오랫동안 함께하는 마음 친구</p>
            <button class="bg-gray-400 text-white px-6 py-3 rounded-lg mt-4 cursor-not-allowed">
                준비 중
            </button>
        </div>
    </div>
    <div class="text-center mt-4">
        <p class="text-gray-600">💬 결제 후 인증: 카카오톡 <strong>jeuspo</strong> 또는 이메일 <strong>mwiby91@gmail.com</strong>으로 스크린샷을 보내주세요.</p>
        <p class="text-gray-600">관리자 비밀번호를 바로 알려드립니다!</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- 관리자 로그인/영역 ----
    st.markdown("<div class='my-6'></div>", unsafe_allow_html=True)
    st.subheader("🔐 관리자 모드")
    if not st.session_state.get("is_admin"):
        pw = st.text_input("관리자 비밀번호", type="password", key="admin_pw_input")
        if st.button("🔑 관리자 로그인"):
            if check_admin(pw):
                st.session_state["is_admin"] = True
                st.success("관리자 인증 완료 ✅")
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        return

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("✅ 베이직 30회 적용 ($3)"):
            st.session_state.update({
                "is_paid": True,
                "limit": PAID_LIMIT,
                "usage_count": 0,
                "remaining_paid_uses": PAID_LIMIT,
                "plan": "basic"
            })
            user_ref.update(st.session_state)
            st.success("🎉 베이직 30회 이용권이 적용되었어요!")
    with c2:
        if st.button("✅ 프로 100회 적용 ($6)"):
            st.session_state.update({
                "is_paid": True,
                "limit": 100,
                "usage_count": 0,
                "remaining_paid_uses": 100,
                "plan": "pro"
            })
            user_ref.update(st.session_state)
            st.success("💎 프로 100회 이용권이 적용되었어요!")
    with c3:
        if st.button("🚪 로그아웃"):
            st.session_state["is_admin"] = False
            st.success("로그아웃되었습니다.")

    st.markdown("<hr class='my-4'>", unsafe_allow_html=True)
    st.caption("📥 최근 피드백 10건 (저장 확인용)")
    try:
        docs = db.collection(FEEDBACK_COLLECTION).order_by("ts", direction=firestore.Query.DESCENDING).limit(10).stream()
        for d in docs:
            data = d.to_dict() or {}
            st.write(f"• [{d.id}] {data.get('ts','')} — {data.get('feedback','')}")
    except Exception as e:
        st.code(f"피드백 로드 오류: {e}")

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ========= 사이드바 & 라우팅 =========
st.sidebar.header("📜 대화 기록")
st.sidebar.text_input(" ", value=USER_ID, disabled=True, label_visibility="collapsed")
st.sidebar.markdown("""
<div class="bg-blue-50 p-4 rounded-lg">
    <p class="text-blue-600 font-semibold">당신의 마음 친구</p>
    <p class="text-gray-600 text-sm">언제나 곁에서 위로를 드릴게요 💙</p>
</div>
""", unsafe_allow_html=True)

if PAGE == "chat":
    if st.sidebar.button("💳 결제/FAQ 확인하기", key="plans_button"):
        st.query_params = {"uid": USER_ID, "page": "plans"}
        st.rerun()
else:
    if st.sidebar.button("⬅ 채팅으로 돌아가기", key="chat_button"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()
