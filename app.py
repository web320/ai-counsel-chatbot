import os, uuid, json, hmac
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ===== App Config =====
APP_VERSION = "v1.3.0"
PAYPAL_URL  = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
FEEDBACK_COLLECTION = "feedback"
FREE_LIMIT  = 4
BASIC_LIMIT = 30
PRO_LIMIT   = 100
DEFAULT_TONE = "따뜻하게"

# ===== OpenAI =====
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ===== Firebase Admin =====
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

# ===== Admin Keys =====
PRIMARY_KEY = st.secrets.get("ADMIN_KEY") or os.getenv("ADMIN_KEY") or "6U4urDCJLr7D0EWa4nST"
LEGACY_KEY  = "4321"
def check_admin(pw: str) -> bool:
    candidates = [PRIMARY_KEY, LEGACY_KEY]
    return any(k and hmac.compare_digest(str(pw or ""), str(k)) for k in candidates)

# ===== Query Params =====
def _qp_get(name: str, default=None):
    val = st.query_params.get(name)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

uid  = _qp_get("uid")
page = _qp_get("page", "chat")
if not uid:
    uid = str(uuid.uuid4())
    st.query_params = {"uid": uid, "page": page}
USER_ID = uid
PAGE     = page

# ===== UI Style =====
st.set_page_config(page_title="당신을 기댈 수 있는 AI 친구", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 18px; color: #333; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
.chat-container { display: flex; flex-direction: column; gap: 10px; }
.message-row { display: flex; align-items: flex-start; gap: 10px; }
.user-row { justify-content: flex-end; }
.bot-row { justify-content: flex-start; }
.avatar { font-size: 24px; margin-top: 8px; }
.user-bubble {
    background: linear-gradient(135deg, #ff6b6b, #ff8e53);
    color: #fff;
    border-radius: 16px;
    padding: 12px 20px;
    margin: 10px 0;
    display: inline-block;
    max-width: 70%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: transform 0.2s ease;
}
.user-bubble:hover { transform: scale(1.02); }
.bot-bubble {
    font-size: 20px;
    line-height: 1.6;
    border-radius: 16px;
    padding: 14px 20px;
    margin: 10px 0;
    background: linear-gradient(135deg, #2b2d42, #4a4e69);
    color: #fff;
    border: 2px solid transparent;
    border-image: linear-gradient(90deg, #6b7280, #9ca3af) 1;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: soft-glow 2s ease-in-out infinite alternate;
}
@keyframes soft-glow {
    from { box-shadow: 0 0 8px rgba(107, 114, 128, 0.3), 0 0 16px rgba(156, 163, 175, 0.2); }
    to { box-shadow: 0 0 12px rgba(107, 114, 128, 0.5), 0 0 24px rgba(156, 163, 175, 0.3); }
}
.stButton > button {
    background: linear-gradient(135deg, #3b82f6, #60a5fa);
    color: #fff;
    border: none;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 16px;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb, #3b82f6);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    transform: translateY(-2px);
}
.stTextInput > div > input {
    border-radius: 12px;
    border: 1px solid #d1d5db;
    padding: 10px;
    background: #f9fafb;
}
.stTextArea > div > textarea {
    border-radius: 12px;
    border: 1px solid #d1d5db;
    background: #f9fafb;
}
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# ===== Session & User Doc =====
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
        st.session_state[k] = data.get(k, v) if data.get(k, v) is not None else st.session_state[k]
else:
    user_ref.set(defaults)

# ===== Helpers =====
def persist_user(fields: dict) -> bool:
    try:
        db.collection("users").document(USER_ID).set(fields, merge=True)
        st.session_state.update(fields)
        return True
    except Exception as e:
        st.error("저장 중 오류")
        st.code(str(e))
        return False

def show_paypal_button(message: str):
    st.markdown(f"""
    <style>
    .paypal-card {
        background: linear-gradient(135deg, #ffffff, #f3f4f6);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 20px 0;
        animation: fadeIn 1s ease-in-out;
    }
    .paypal-button {
        background: linear-gradient(135deg, #0070ba, #0096db);
        color: #fff;
        padding: 12px 24px;
        border: none;
        border-radius: 12px;
        font-size: 18px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .paypal-button:hover {
        background: linear-gradient(135deg, #005ea6, #0070ba);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    <div class='paypal-card'>
        <p style='color:#dc2626;font-size:18px;margin:0 0 12px 0;'>{message}</p>
        <p style='color:#1f2937;font-size:16px;'>💙 단 3달러로 30회의 마음상담을 이어갈 수 있어요.</p>
        <a href='{PAYPAL_URL}' target='_blank'>
            <button class='paypal-button'>💳 PayPal로 결제하기 ($3)</button>
        </a>
        <p style='color:#4b5563;opacity:.8;margin-top:12px;font-size:14px;'>
            결제 후 카카오톡 <b>jeuspo</b> 또는 이메일 <b>mwiby91@gmail.com</b>으로 스크린샷을 보내주세요.<br>
            관리자 비밀번호를 알려드려요.
        </p>
    </div>
    """, unsafe_allow_html=True)

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
        doc_ref = db.collection(FEEDBACK_COLLECTION).document()
        doc_ref.set(doc)
        st.success("피드백이 저장되었어요 💙")
        st.info(f"문서 ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        st.error("피드백 저장 실패")
        st.code(str(e))
        return None

def apply_plan(plan: str):
    if plan == "basic":
        fields = {
            "is_paid": True, "plan": "basic",
            "limit": BASIC_LIMIT,
            "usage_count": 0,
            "remaining_paid_uses": BASIC_LIMIT,
        }
    elif plan == "pro":
        fields = {
            "is_paid": True, "plan": "pro",
            "limit": PRO_LIMIT,
            "usage_count": 0,
            "remaining_paid_uses": PRO_LIMIT,
        }
    else:
        return
    if persist_user(fields):
        st.success("권한 적용 완료! 채팅으로 이동합니다.")
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ===== OpenAI Stream =====
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

# ===== Pages =====
def render_chat_page():
    # 제한/잔여 표시
    if st.session_state.get("is_paid"):
        remaining = int(st.session_state.get("remaining_paid_uses", 0))
        st.caption(f"💎 남은 상담 횟수: {remaining}회 / {st.session_state.get('limit', 0)}회")
        if remaining <= 0:
            show_paypal_button("💳 이용권이 모두 소진되었습니다. 새로 결제 후 이용해주세요.")
            return
    else:
        used = int(st.session_state.get("usage_count", 0))
        left = int(st.session_state.get("limit", FREE_LIMIT)) - used
        if used >= st.session_state.get("limit", FREE_LIMIT):
            show_paypal_button("무료 체험이 모두 끝났어요 💙")
            return
        st.caption(f"🌱 무료 체험 남은 횟수: {left}회")

    # 대화 기록 표시
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for user_msg, bot_msg in st.session_state.get("chat_history", []):
        st.markdown(f"""
        <div class='message-row user-row'>
            <div class='user-bubble'>{user_msg}</div>
            <span class='avatar'>😔</span>
        </div>
        <div class='message-row bot-row'>
            <span class='avatar'>🧡</span>
            <div class='bot-bubble'>{bot_msg.replace('\n\n', '<br><br>')}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 입력
    user_input = st.chat_input("지금 어떤 기분이야?")
    if not user_input:
        return

    # 가벼운 감정 힌트
    if any(k in user_input for k in ["힘들", "피곤", "짜증", "불안", "우울"]):
        st.markdown("<div class='message-row bot-row'><span class='avatar'>🧡</span><div class='bot-bubble'>💭 많이 지쳐 있네요... 그래도 괜찮아요.</div></div>", unsafe_allow_html=True)
    elif any(k in user_input for k in ["행복", "좋아", "괜찮", "고마워"]):
        st.markdown("<div class='message-row bot-row'><span class='avatar'>🧡</span><div class='bot-bubble'>🌤️ 그 기분, 참 소중하네요.</div></div>", unsafe_allow_html=True)

    # 대화 스트림
    st.markdown(f"<div class='message-row user-row'><div class='user-bubble'>{user_input}</div><span class='avatar'>😔</span></div>", unsafe_allow_html=True)
    placeholder = st.empty()
    placeholder.markdown("<div class='message-row bot-row'><span class='avatar'>🧡</span><div class='bot-bubble'>⏳ 답변을 준비 중이에요...</div></div>", unsafe_allow_html=True)
    streamed = ""
    for token in stream_reply(user_input):
        streamed += token
        safe = streamed.replace("\n\n", "<br><br>")
        placeholder.markdown(f"<div class='message-row bot-row'><span class='avatar'>🧡</span><div class='bot-bubble'>{safe}</div></div>", unsafe_allow_html=True)

    # 기록/차감
    st.session_state.chat_history.append((user_input, streamed))
    if st.session_state.get("is_paid"):
        new_left = max(0, int(st.session_state.get("remaining_paid_uses", 0)) - 1)
        persist_user({"remaining_paid_uses": new_left})
    else:
        new_usage = int(st.session_state.get("usage_count", 0)) + 1
        persist_user({"usage_count": new_usage})

    # 체험 종료 CTA
    if (not st.session_state.get("is_paid")) and (st.session_state.get("usage_count", 0) >= st.session_state.get("limit", FREE_LIMIT)):
        show_paypal_button("무료 체험이 끝났어요. 다음 대화부터는 유료 이용권이 필요해요 💳")

    # 피드백
    with st.expander("📝 대화에 대한 피드백을 남겨주세요"):
        fb = st.text_area("좋았던 점/아쉬운 점을 적어주세요", placeholder="예: 위로가 많이 됐어요 / 답변이 조금 짧았어요 / 결제 안내가 헷갈려요")
        if st.button("📩 피드백 제출"):
            if fb and fb.strip():
                save_feedback(USER_ID, fb, "chat")
            else:
                st.warning("내용을 입력해주세요 😊")

def render_plans_page():
    header_html = """
    <div style='text-align:center; padding-top:8px;'>
      <h2 style="margin:0 0 6px 0;">💙 마음을 기댈 수 있는 AI 친구</h2>
      <h3 style="margin:0;">💳 결제 안내</h3>
    </div>
    """
    cards_html = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .pricing-wrap {
        display: flex;
        justify-content: center;
        gap: 24px;
        flex-wrap: wrap;
        padding: 20px;
    }
    .card {
        width: 300px;
        border-radius: 16px;
        padding: 24px;
        background: linear-gradient(135deg, #ffffff, #f3f4f6);
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 24px rgba(0,0,0,0.15);
    }
    .card.basic {
        border: 3px solid #3b82f6;
    }
    .card.pro {
        border: 3px solid #10b981;
    }
    .card h3 {
        margin: 0;
        font-size: 24px;
        font-weight: 700;
    }
    .price {
        font-size: 36px;
        font-weight: 700;
        margin: 12px 0 8px;
        color: #1f2937;
    }
    .desc {
        font-size: 16px;
        color: #4b5563;
        margin: 4px 0;
    }
    .btn {
        width: 100%;
        padding: 12px;
        font-size: 16px;
        border: none;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .btn.basic {
        background: linear-gradient(135deg, #3b82f6, #60a5fa);
        color: #fff;
    }
    .btn.basic:hover {
        background: linear-gradient(135deg, #2563eb, #3b82f6);
    }
    .btn.pro {
        background: #6b7280;
        color: #d1d5db;
    }
    .howto {
        margin-top: 32px;
        text-align: center;
        color: #4b5563;
    }
    .idbox {
        display: flex;
        gap: 12px;
        align-items: center;
        justify-content: center;
        margin: 8px 0;
    }
    .copy {
        padding: 6px 12px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        background: #f9fafb;
        color: #1f2937;
        cursor: pointer;
        font-size: 14px;
        transition: background 0.2s ease;
    }
    .copy:hover {
        background: #e5e7eb;
    }
    </style>

    <div class="pricing-wrap">
      <div class="card basic">
        <h3 style="color:#3b82f6;">⭐ 베이직 플랜</h3>
        <div class="price">$3</div>
        <p class="desc">30회 상담 이용권</p>
        <p class="desc">가볍게 시작하는 마음 친구</p>
        <a href="{PAYPAL_URL}" target="_blank">
          <button class="btn basic">💳 결제하기</button>
        </a>
      </div>

      <div class="card pro">
        <h3 style="color:#10b981;">💎 프로 플랜</h3>
        <div class="price">$6</div>
        <p class="desc">100회 상담 이용권</p>
        <p class="desc">깊은 대화를 위한 동반자</p>
        <button class="btn pro" disabled>준비 중</button>
      </div>
    </div>

    <div class="howto">
      <p style="margin:0;font-size:18px;">💬 결제 후 인증 방법</p>
      <div class="idbox">
        <span>카톡: <b>jeuspo</b></span>
        <button class="copy" onclick="navigator.clipboard.writeText('jeuspo')">복사</button>
      </div>
      <div class="idbox">
        <span>이메일: <b>mwiby91@gmail.com</b></span>
        <button class="copy" onclick="navigator.clipboard.writeText('mwiby91@gmail.com')">복사</button>
      </div>
      <p style="opacity:.8;margin-top:12px;font-size:16px;">
        결제 스크린샷을 보내주시면 <b>관리자 비밀번호</b>를 드립니다.
      </p>
    </div>
    """
    components.html(header_html + cards_html, height=620, scrolling=False)

    # ---- 관리자 로그인/영역 ----
    st.markdown("<hr>", unsafe_allow_html=True)
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
            apply_plan("basic")
    with c2:
        if st.button("✅ 프로 100회 적용 ($6)"):
            apply_plan("pro")
    with c3:
        if st.button("🚪 로그아웃"):
            st.session_state["is_admin"] = False
            st.success("로그아웃되었습니다.")

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ===== Sidebar =====
st.sidebar.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #e5e7eb, #f3f4f6);
}
.sidebar-button {
    background: linear-gradient(135deg, #3b82f6, #60a5fa);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 10px;
    width: 100%;
    font-size: 16px;
    margin-bottom: 10px;
    transition: all 0.3s ease;
}
.sidebar-button:hover {
    background: linear-gradient(135deg, #2563eb, #3b82f6);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.history-item {
    background: #ffffff;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 8px;
    font-size: 14px;
    color: #4b5563;
    cursor: pointer;
    transition: background 0.2s ease;
}
.history-item:hover {
    background: #f3f4f6;
}
</style>
""", unsafe_allow_html=True)
st.sidebar.header("📜 대화 기록")
st.sidebar.text_input("사용자 ID", value=USER_ID, disabled=True, label_visibility="collapsed")
for i, (user_msg, _) in enumerate(st.session_state.get("chat_history", [])):
    st.sidebar.markdown(f"<div class='history-item'>😔 {user_msg[:50]}...</div>", unsafe_allow_html=True)
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
st.sidebar.subheader("⚙️ 설정")
theme = st.sidebar.selectbox("테마", ["Light", "Dark"], index=0)
if theme == "Dark":
    st.markdown("""
    <style>
    html, body, [class*="css"] { background: #1f2937; color: #f3f4f6; }
    .card, .paypal-card { background: linear-gradient(135deg, #374151, #4b5563); }
    .stTextInput > div > input, .stTextArea > div > textarea { background: #374151; color: #f3f4f6; border-color: #4b5563; }
    .desc, .howto, .paypal-card p { color: #d1d5db; }
    </style>
    """, unsafe_allow_html=True)
if PAGE == "chat":
    if st.sidebar.button("💳 결제/FAQ 열기", key="to_plans", help="결제 및 FAQ 페이지로 이동"):
        st.query_params = {"uid": USER_ID, "page": "plans"}
        st.rerun()
else:
    if st.sidebar.button("⬅ 채팅으로 돌아가기", key="to_chat", help="채팅 페이지로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ===== Routing =====
if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()
