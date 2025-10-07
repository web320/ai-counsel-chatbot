# ==========================================
# 💙 AI 심리상담 앱 v1.7.0 (감정인식 통합)
# ==========================================
import os, uuid, json, time, hmac
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= App Config =================
APP_VERSION = "v1.7.0"
PAYPAL_URL  = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
FREE_LIMIT  = 4
BASIC_LIMIT = 30
PRO_LIMIT   = 100
DEFAULT_TONE = "따뜻하게"

# ================= OpenAI =================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ================= Firebase =================
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

# ================= Admin Keys =================
ADMIN_KEYS = []
for k in [st.secrets.get("ADMIN_KEY"), os.getenv("ADMIN_KEY"), "6U4urDCJLr7D0EWa4nST", "4321"]:
    if k and str(k) not in ADMIN_KEYS:
        ADMIN_KEYS.append(str(k))

def check_admin(pw: str) -> bool:
    return any(hmac.compare_digest(pw.strip(), key) for key in ADMIN_KEYS)

# ================= Query Params =================
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

# ================= Styles =================
st.set_page_config(page_title="💙 마음을 기댈 수 있는 AI 친구", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
.user-bubble { background:#b91c1c;color:#fff;border-radius:12px;padding:10px 16px;margin:8px 0;display:inline-block; }
.bot-bubble { font-size:21px;line-height:1.8;border-radius:14px;padding:14px 18px;margin:10px 0;background:rgba(15,15,30,.85);color:#fff;
  border:2px solid transparent;border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;animation:neon-glow 1.8s ease-in-out infinite alternate; }
@keyframes neon-glow { from{box-shadow:0 0 5px #ff8800,0 0 10px #ffaa00;} to{box-shadow:0 0 20px #ff8800,0 0 40px #ffaa00,0 0 60px #ff8800;} }
.status { font-size:15px; padding:8px 12px; border-radius:10px; display:inline-block; margin-bottom:8px; background:rgba(255,255,255,.06); }
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# ================= Firestore User =================
defaults = {"is_paid": False, "plan": None, "limit": FREE_LIMIT, "usage_count": 0, "remaining_paid_uses": 0}
user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        st.session_state[k] = data.get(k, v)
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    try:
        user_ref.set(fields, merge=True)
        time.sleep(0.4)
        st.session_state.update(fields)
        return True
    except Exception as e:
        st.error(f"Firestore 저장 실패: {e}")
        return False

# ================= 감정 인식 로직 =================
def get_emotion_prompt(user_message: str) -> str:
    text = user_message.lower()
    if any(word in text for word in ["불안", "초조", "걱정", "긴장"]):
        return "사용자가 불안을 표현했습니다. 원인을 묻지 말고 지금 그 감정을 그대로 인정해주는 따뜻한 말로 답해주세요."
    elif any(word in text for word in ["외로워", "혼자", "쓸쓸", "고독"]):
        return "사용자가 외로움을 표현했습니다. 누군가 곁에 있는 듯한 문장을 만들어주세요."
    elif any(word in text for word in ["나 싫어", "못해", "쓸모없어", "가치없어"]):
        return "사용자가 자기혐오를 표현했습니다. 공감적으로 이해하고, 자존감을 회복시키는 문장을 포함해주세요."
    elif any(word in text for word in ["하기 싫", "지쳤", "힘들어", "귀찮"]):
        return "사용자가 무기력을 표현했습니다. 행동을 강요하지 않고, 존재 자체가 괜찮다는 위로를 전달해주세요."
    else:
        return "사용자가 일상 대화를 하고 있습니다. 부드럽고 따뜻하게 이어가세요."

# ================= OpenAI 답변 =================
def stream_reply(text):
    if not client: return
    emotion_prompt = get_emotion_prompt(text)
    sys = f"""
당신은 {DEFAULT_TONE} 말투의 심리상담사이자 친구입니다.
답변은 3문단 이내로 짧고 따뜻하게.
감정별 가이드: {emotion_prompt}
"""
    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            stream=True,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": text}]
        )
        msg = ""
        placeholder = st.empty()
        for chunk in stream:
            delta = getattr(chunk.choices[0], "delta", None)
            if delta and getattr(delta, "content", None):
                msg += delta.content
                safe = msg.replace("\n\n", "<br><br>")
                placeholder.markdown(f"<div class='bot-bubble'>🧡 {safe}</div>", unsafe_allow_html=True)
        return msg
    except Exception as e:
        st.error(f"OpenAI 오류: {e}")

# ================= 상태 표시 =================
def status_chip():
    if st.session_state.get("is_paid"):
        st.markdown(
            f"<div class='status'>💎 유료({st.session_state.get('plan')}) — 남은 {st.session_state.get('remaining_paid_uses',0)}/{st.session_state.get('limit',0)}회</div>",
            unsafe_allow_html=True)
    else:
        left = st.session_state["limit"] - st.session_state["usage_count"]
        st.markdown(f"<div class='status'>🌱 무료 체험 — 남은 {max(left,0)}회</div>", unsafe_allow_html=True)

# ================= 결제 페이지 =================
def render_plans_page():
    status_chip()
    st.markdown("""
    <div style='text-align:center;'>
      <h2>💳 결제 안내</h2>
      <p>💙 단 3달러로 30회의 마음상담을 이어갈 수 있어요.</p>
    </div>
    """, unsafe_allow_html=True)

    components.html(f"""
    <div style="text-align:center">
      <a href="{PAYPAL_URL}" target="_blank">
        <button style="background:#ffaa00;color:black;padding:12px 20px;border:none;border-radius:10px;font-size:18px;">
          💳 PayPal로 결제하기 ($3)
        </button>
      </a>
      <p style="opacity:0.8;margin-top:10px;">결제 후 카톡 <b>jeuspo</b> 또는 이메일 <b>mwiby91@gmail.com</b>으로<br>스크린샷을 보내주시면 비밀번호를 알려드립니다.</p>
    </div>
    """, height=280)

    st.markdown("---")
    st.subheader("🔐 관리자 인증 (자동 적용)")

    pw = st.text_input("관리자 비밀번호", type="password")
    if pw:
        if check_admin(pw):
            st.success("✅ 관리자 인증 완료! 베이직 30회 이용권을 적용합니다...")
            fields = {
                "is_paid": True, "plan": "basic",
                "limit": BASIC_LIMIT, "usage_count": 0,
                "remaining_paid_uses": BASIC_LIMIT
            }
            if persist_user(fields):
                st.success("🎉 베이직 30회 이용권 적용 완료! 채팅으로 이동 중...")
                time.sleep(0.8)
                st.session_state.clear()
                st.query_params = {"uid": USER_ID, "page": "chat"}
                st.experimental_rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ================= 채팅 페이지 =================
def render_chat_page():
    status_chip()
    if st.session_state.get("is_paid"):
        if st.session_state["remaining_paid_uses"] <= 0:
            st.warning("💳 이용권이 소진되었습니다. 결제 후 이용해주세요.")
            return
    elif st.session_state["usage_count"] >= FREE_LIMIT:
        st.warning("🌱 무료 체험이 끝났어요. 유료 이용권을 구매해주세요.")
        return

    user_input = st.chat_input("지금 어떤 기분이야?")
    if not user_input: return

    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    reply = stream_reply(user_input)
    if not reply: return

    if st.session_state["is_paid"]:
        persist_user({"remaining_paid_uses": st.session_state["remaining_paid_uses"] - 1})
    else:
        persist_user({"usage_count": st.session_state["usage_count"] + 1})

# ================= 사이드바 =================
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

# ================= Routing =================
if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()
