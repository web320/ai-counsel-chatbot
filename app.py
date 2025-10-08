# ==========================================
# 💙 AI 심리상담 앱 v2.0 (광고수익형 + 결제 + 안정화)
# ==========================================
import os, uuid, json, time, hmac, random
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Config =================
APP_VERSION = "v2.0"
PAYPAL_URL  = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
FREE_LIMIT  = 4
BASIC_LIMIT = 30
DAILY_FREE_LIMIT = 7
BONUS_AFTER_AD = 3
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
ADMIN_KEYS = [str(k) for k in [st.secrets.get("ADMIN_KEY"), os.getenv("ADMIN_KEY"), "6U4urDCJLr7D0EWa4nST", "4321"] if k]
def check_admin(pw: str) -> bool:
    return any(hmac.compare_digest(pw.strip(), key) for key in ADMIN_KEYS)

# ================= Query Params =================
def _qp_get(name: str, default=None):
    val = st.query_params.get(name)
    return (val[0] if isinstance(val, list) else val) or default

uid  = _qp_get("uid") or str(uuid.uuid4())
page = _qp_get("page", "chat")
st.query_params = {"uid": uid, "page": page}
USER_ID, PAGE = uid, page

# ================= Page Setup =================
st.set_page_config(page_title="💙 마음을 기댈 수 있는 따뜻한 AI 친구", layout="wide")

# ===== Google AdSense 코드 삽입 =====
st.markdown("""
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5846666879010880"
     crossorigin="anonymous"></script>
""", unsafe_allow_html=True)

# ================= Style =================
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; transition: all 0.3s ease; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
.user-bubble {
  background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;margin:8px 0;
  display:inline-block;box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble {
  font-size:21px;line-height:1.8;border-radius:16px;padding:16px 20px;margin:10px 0;
  background:rgba(15,15,30,.85);color:#fff;border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;animation:neon 1.6s ease-in-out infinite alternate;
}
@keyframes neon {from{box-shadow:0 0 8px #ffaa00;}to{box-shadow:0 0 22px #ffcc33;}}

.status {
  font-size:15px;padding:8px 12px;border-radius:10px;
  display:inline-block;margin-bottom:8px;background:rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)
st.title("💙 마음을 기댈 수 있는 따뜻한 AI 친구")

# ================= Firestore User =================
defaults = {"is_paid": False, "plan": None, "limit": FREE_LIMIT, "usage_count": 0, "remaining_paid_uses": 0, "last_use_date": None}
user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    st.session_state.update({k: data.get(k, v) for k, v in defaults.items()})
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    try:
        user_ref.set(fields, merge=True)
        st.session_state.update(fields)
    except Exception as e:
        st.error(f"Firestore 저장 실패: {e}")

# ================= 감정 인식 =================
def get_emotion_prompt(msg: str):
    msg = msg.lower()
    if any(w in msg for w in ["불안", "초조", "걱정", "긴장"]):
        return "사용자가 불안을 표현했습니다. 안정감을 주는 따뜻한 말을 해주세요."
    if any(w in msg for w in ["외로워", "혼자", "쓸쓸", "고독"]):
        return "사용자가 외로움을 표현했습니다. 부드럽게 공감하며 위로해주세요."
    if any(w in msg for w in ["힘들", "귀찮", "하기 싫", "지쳤"]):
        return "사용자가 무기력을 표현했습니다. 존재 자체를 인정해주세요."
    return "일상적인 대화를 따뜻하게 이어가주세요."

# ================= 답변 + 광고 =================
def stream_reply(user_input):
    st.markdown(f"<div class='bot-bubble'>🧡 '{user_input}' 에 대한 따뜻한 예시 답변입니다.<br>현재는 테스트 모드입니다.</div>", unsafe_allow_html=True)
    # 광고 배너 (하단)
    components.html("""
    <div style='text-align:center;margin:20px 0;'>
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="ca-pub-5846666879010880"
           data-ad-slot="1234567890"
           data-ad-format="auto"
           data-full-width-responsive="true"></ins>
      <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
    </div>
    """, height=120)
    return "테스트 모드"

# ================= 결제 페이지 =================
def render_plans_page():
    st.markdown("<div class='status'>💎 유료 이용권 안내</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center;'>
      <h2>💳 결제 안내</h2>
      <p>💙 단 3달러로 30회의 마음상담을 이어갈 수 있어요.</p>
      <a href="https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG" target="_blank">
        <button style="background:#ffaa00;color:black;padding:12px 20px;border:none;border-radius:10px;font-size:18px;">
          💳 PayPal로 결제하기 ($3)
        </button>
      </a>
      <p style="margin-top:16px;opacity:0.8;">결제 후 카톡 ID <b>jeuspo</b> 또는 이메일 <b>mwiby91@gmail.com</b> 로<br>스크린샷을 보내주시면 이용 비밀번호를 알려드립니다.</p>
    </div>
    """, unsafe_allow_html=True)

# ================= 상태 표시 =================
def status_chip():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", 0)
        total = st.session_state.get("limit", 30)
        st.markdown(f"<div class='status'>💎 유료 이용중 — 남은 {left}/{total}회</div>", unsafe_allow_html=True)
    else:
        left = st.session_state["limit"] - st.session_state["usage_count"]
        st.markdown(f"<div class='status'>🌱 무료 체험 — 남은 {max(left,0)}회</div>", unsafe_allow_html=True)

# ================= 채팅 페이지 =================
def render_chat_page():
    status_chip()
    if "greeted" not in st.session_state:
        greeting = random.choice([
            "오늘은 힘든 일 있었어? 내가 곁에 있을게 🤍",
            "괜찮아, 그냥 나한테 털어놔도 돼 🌷",
            "마음이 무겁지? 같이 이야기해볼까 ☁️"
        ])
        st.markdown(f"<div class='bot-bubble'>{greeting}</div>", unsafe_allow_html=True)
        st.session_state["greeted"] = True

    user_input = st.chat_input("지금 어떤 기분이에요?")
    if not user_input: return
    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    stream_reply(user_input)

# ================= Sidebar =================
st.sidebar.header("📜 대화 기록")
st.sidebar.text_input(" ", value=USER_ID, disabled=True, label_visibility="collapsed")
if PAGE == "chat":
    if st.sidebar.button("💳 결제 / FAQ 열기"):
        st.query_params = {"uid": USER_ID, "page": "plans"}
        st.rerun()
else:
    if st.sidebar.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

if PAGE == "chat": render_chat_page()
elif PAGE == "plans": render_plans_page()

