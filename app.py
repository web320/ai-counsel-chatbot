# ==========================================
# 💙 AI 심리상담 앱 v1.8.0 (결제 피드백 추가)
# ==========================================
import os, uuid, json, time, hmac
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= App Config =================
APP_VERSION = "v1.8.0"
PAYPAL_URL  = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
FREE_LIMIT  = 4
BASIC_LIMIT = 30
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

# ================= Query Params =================
def _qp_get(name: str, default=None):
    val = st.query_params.get(name)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

uid  = _qp_get("uid") or str(uuid.uuid4())
page = _qp_get("page", "chat")
st.query_params = {"uid": uid, "page": page}
USER_ID, PAGE = uid, page

# ================= 스타일 =================
st.set_page_config(page_title="💙 마음을 기댈 수 있는 AI 친구", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
.user-bubble { background:#b91c1c;color:#fff;border-radius:12px;padding:10px 16px;margin:8px 0;display:inline-block; }
.bot-bubble { font-size:21px;line-height:1.8;border-radius:14px;padding:14px 18px;margin:10px 0;
  color:#fff;background:rgba(15,15,30,.85);
  border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  animation:neon-glow 1.8s ease-in-out infinite alternate; }
@keyframes neon-glow { from{box-shadow:0 0 5px #ff8800;} to{box-shadow:0 0 30px #ffaa00;} }
.status { font-size:15px;padding:8px 12px;border-radius:10px;margin-bottom:8px;background:rgba(255,255,255,.06);}
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# ================= Firestore 유저 기본정보 =================
defaults = {"is_paid": False, "plan": None, "limit": FREE_LIMIT, "usage_count": 0}
user_ref = db.collection("users").document(USER_ID)
if not user_ref.get().exists:
    user_ref.set(defaults)
st.session_state.update(defaults)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ================= 감정 프롬프트 =================
def get_emotion_prompt(msg: str):
    text = msg.lower()
    if any(x in text for x in ["불안","걱정","초조"]): return "불안을 공감해주세요."
    if any(x in text for x in ["외로워","혼자","쓸쓸"]): return "외로움을 따뜻하게 다독여주세요."
    if any(x in text for x in ["하기 싫","힘들","지쳤"]): return "무기력한 마음을 위로해주세요."
    if any(x in text for x in ["나 싫어","못해","쓸모없"]): return "자존감을 회복시켜주는 말로 답해주세요."
    return "일상 대화는 부드럽게 이어가주세요."

def stream_reply(text):
    sys = f"너는 {DEFAULT_TONE} 톤의 심리상담사야. {get_emotion_prompt(text)}"
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        stream=True,
        messages=[{"role": "system","content":sys},{"role":"user","content":text}]
    )
    msg = ""; holder = st.empty()
    for chunk in stream:
        delta = getattr(chunk.choices[0], "delta", None)
        if delta and getattr(delta, "content", None):
            msg += delta.content
            holder.markdown(f"<div class='bot-bubble'>🧡 {msg}</div>", unsafe_allow_html=True)
    return msg

# ================= 결제 페이지 =================
def render_plans_page():
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
      <p style="opacity:0.9;margin-top:14px;line-height:1.6;font-size:17px;">
        결제 후 <b style="color:#FFD966;">카톡 ID: jeuspo</b><br>
        또는 <b style="color:#9CDCFE;">이메일: mwiby91@gmail.com</b><br>
        로 결제 <b>스크린샷</b>을 보내주시면 비밀번호를 알려드립니다.<br><br>
        🔒 비밀번호 입력 후 바로 상담 이용이 가능합니다.
      </p>
    </div>
    """, height=320)

    st.markdown("---")
    st.subheader("📝 결제 관련 피드백")

    feedback = st.text_area("서비스 이용 전 궁금한 점이나 개선사항이 있나요?")
    if st.button("💌 피드백 보내기"):
        if feedback.strip():
            fb_ref = db.collection("feedback").document()
            fb_ref.set({
                "uid": USER_ID,
                "content": feedback.strip(),
                "created_at": datetime.now().isoformat()
            })
            st.success("💖 피드백이 소중히 전달되었습니다. 감사합니다!")
        else:
            st.warning("내용을 입력해주세요.")

    st.markdown("---")
    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ================= 채팅 페이지 =================
def render_chat_page():
    st.markdown("<div class='status'>🌱 무료 체험 중</div>", unsafe_allow_html=True)
    user_input = st.chat_input("지금 어떤 기분이야?")
    if not user_input: return
    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    stream_reply(user_input)

# ================= 사이드바 & 라우팅 =================
st.sidebar.header("📜 메뉴")
if PAGE == "chat":
    if st.sidebar.button("💳 결제 / 피드백"):
        st.query_params = {"uid": USER_ID, "page": "plans"}
        st.rerun()
else:
    if st.sidebar.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

if PAGE == "chat": render_chat_page()
else: render_plans_page()
