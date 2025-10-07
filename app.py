# ==========================================
# 💙 AI 심리상담 앱 v1.8.1
# (감정인식 + 결제 안내 + 피드백 + 자동 색상반전)
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
APP_VERSION = "v1.8.1"
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
html, body, [class*="css"] { font-size: 18px; transition: all 0.3s ease; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
/* 버블 */
.user-bubble { background:#b91c1c;color:#fff;border-radius:12px;padding:10px 16px;margin:8px 0;display:inline-block; }
.bot-bubble { font-size:21px;line-height:1.8;border-radius:14px;padding:14px 18px;margin:10px 0;
  background:rgba(15,15,30,.85);color:#fff;border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  animation:neon-glow 1.8s ease-in-out infinite alternate; }
@keyframes neon-glow { from{box-shadow:0 0 5px #ff8800;} to{box-shadow:0 0 25px #ffaa00;} }
/* 상태칩 */
.status { font-size:15px; padding:8px 12px; border-radius:10px; display:inline-block;
  margin-bottom:8px; background:rgba(255,255,255,.06); }
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# === 전역: 배경 밝기 감지 → 자동 색상 반전(JS는 components.html로 주입) ===
def inject_auto_contrast():
    components.html("""
    <script>
    (function(){
      function parseRGB(c){var m=c&&c.match(/\\d+/g); return m?m.map(Number):[255,255,255];}
      function setTheme(){
        var bg = getComputedStyle(document.body).backgroundColor;
        var rgb = parseRGB(bg);
        var brightness = 0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2];
        var root = document.documentElement;
        if(brightness > 180){ // Light
          root.style.setProperty('--text-color','#111');
          root.style.setProperty('--sub-color','#333');
          root.style.setProperty('--link-color','#0070f3');
        } else { // Dark
          root.style.setProperty('--text-color','#fff');
          root.style.setProperty('--sub-color','#ddd');
          root.style.setProperty('--link-color','#9CDCFE');
        }
      }
      new MutationObserver(setTheme).observe(document.body,{attributes:true,childList:true,subtree:true});
      setTheme();
    })();
    </script>
    <style>
      body, html { color: var(--text-color); transition: color .3s ease, background-color .3s ease; }
      p, span, div, h1, h2, h3, h4, h5, h6, label { color: var(--text-color) !important; }
      a, b { color: var(--link-color) !important; }
      .status { color: var(--sub-color) !important; }
    </style>
    """, height=0)
inject_auto_contrast()

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
    if any(w in text for w in ["불안", "초조", "걱정", "긴장"]):
        return "사용자가 불안을 표현했습니다. 원인을 묻지 말고 지금 그 감정을 그대로 인정해주는 따뜻한 말로 답해주세요."
    if any(w in text for w in ["외로워", "혼자", "쓸쓸", "고독"]):
        return "사용자가 외로움을 표현했습니다. 누군가 곁에 있는 듯한 문장을 만들어주세요."
    if any(w in text for w in ["나 싫어", "못해", "쓸모없어", "가치없어"]):
        return "사용자가 자기혐오를 표현했습니다. 공감적으로 이해하고, 자존감을 회복시키는 문장을 포함해주세요."
    if any(w in text for w in ["하기 싫", "지쳤", "힘들어", "귀찮"]):
        return "사용자가 무기력을 표현했습니다. 행동을 강요하지 않고, 존재 자체가 괜찮다는 위로를 전달해주세요."
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
      <p style="opacity:0.9;margin-top:14px;line-height:1.6;font-size:17px;">
        결제 후 <b style="color:#FFD966;">카톡 ID: jeuspo</b><br>
        또는 <b style="color:#9CDCFE;">이메일: mwiby91@gmail.com</b><br>
        로 결제 <b>스크린샷을 보내주시면</b> 이용 비밀번호를 알려드립니다.<br><br>
        🔒 비밀번호 입력 후 바로 30회 상담 이용이 가능합니다.
      </p>
    </div>
    """, height=320)

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

    # ================= 피드백 섹션 =================
    st.markdown("---")
    st.subheader("💌 서비스 피드백")
    st.markdown(
        "앱을 사용하면서 느낀 점이나 개선 아이디어를 남겨주세요 💙<br>"
        "당신의 한마디가 앱을 더 따뜻하게 만듭니다 🌷",
        unsafe_allow_html=True
    )

    feedback = st.text_area("무엇이든 자유롭게 남겨주세요.", placeholder="예: 결제 과정이 헷갈렸어요 / 답변이 따뜻했어요 😊")

    if st.button("📩 피드백 보내기"):
        if feedback.strip():
            try:
                fb_ref = db.collection("feedback").document()
                fb_ref.set({
                    "uid": USER_ID,
                    "feedback": feedback.strip(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                st.success("💖 피드백이 소중히 전달되었습니다. 감사합니다!")
            except Exception as e:
                st.error(f"Firestore 저장 실패: {e}")
        else:
            st.warning("내용을 입력해주세요 💬")

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
