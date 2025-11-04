# ==========================================
# 💙 AI 심리상담 앱 v1.8.5 (테스트 안정화 버전)
# (감정인식 + 결제 안내 + 피드백 + 색상반전 + 인사 + 광고 + 오류수정)
# ==========================================
import os, uuid, json, time, hmac, random
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= App Config =================
APP_VERSION = "v1.8.5"
PAYPAL_URL  = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
FREE_LIMIT  = 4
BASIC_LIMIT = 30
DEFAULT_TONE = "따뜻하게"
DAILY_FREE_LIMIT = 7
BONUS_AFTER_AD = 3

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
USER_ID = uid
PAGE     = page

# ================= Styles =================
st.set_page_config(page_title="💙 마음을 기댈 수 있는 따뜻한 AI 친구", layout="wide")
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
  font-size:15px; padding:8px 12px; border-radius:10px;
  display:inline-block;margin-bottom:8px; background:rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)
st.title("💙 마음을 기댈 수 있는 따뜻한 AI 친구")

# === 자동 색상 반전 ===
def inject_auto_contrast():
    components.html("""
    <script>
    (function(){
      function rgb(c){var m=c&&c.match(/\\d+/g);return m?m.map(Number):[255,255,255];}
      function setTheme(){
        var bg=getComputedStyle(document.body).backgroundColor;
        var [r,g,b]=rgb(bg);
        var bright=0.299*r+0.587*g+0.114*b;
        var root=document.documentElement;
        if(bright>180){
          root.style.setProperty('--text','#111');root.style.setProperty('--link','#0070f3');
        }else{
          root.style.setProperty('--text','#fff');root.style.setProperty('--link','#9CDCFE');
        }}
      new MutationObserver(setTheme).observe(document.body,{childList:true,subtree:true});
      setTheme();
    })();
    </script>
    <style>
      body,html{color:var(--text);transition:.3s ease;}
      a,b{color:var(--link)!important;}
    </style>
    """, height=0)
inject_auto_contrast()

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
        return True
    except Exception as e:
        st.error(f"Firestore 저장 실패: {e}")
        return False

# ================= 감정 인식 =================
def get_emotion_prompt(msg: str):
    msg = msg.lower()
    if any(w in msg for w in ["불안", "초조", "걱정", "긴장"]):
        return "사용자가 불안을 표현했습니다. 부드럽게 안정감을 주는 말을 해주세요."
    if any(w in msg for w in ["외로워", "혼자", "쓸쓸", "고독"]):
        return "사용자가 외로움을 표현했습니다. 마음을 토닥여주고 누군가 곁에 있는 듯한 말로 위로해주세요."
    if any(w in msg for w in ["힘들", "귀찮", "하기 싫", "지쳤"]):
        return "사용자가 무기력을 표현했습니다. 강요하지 않고 존재 자체를 인정해주세요."
    if any(w in msg for w in ["싫어", "쓸모없", "못해", "가치없"]):
        return "사용자가 자기혐오를 표현했습니다. 공감하며 따뜻하게 자존감을 세워주세요."
    return "사용자가 일상 대화를 하고 있습니다. 일상의 일을 공감하고 따뜻하게 대화를 이어가주세요."

# ================= OpenAI 대신 임시 테스트 응답 =================
def stream_reply(user_input):
    """AI 대신 테스트 모드용 더미 응답"""
    st.markdown(f"<div class='bot-bubble'>🧡 (테스트 모드) '{user_input}' 에 대한 예시 답변입니다.<br>지금은 AI 연결이 꺼져있어요 💫</div>", unsafe_allow_html=True)
    components.html("""
    <div style='text-align:center;margin:20px 0;'>
        <iframe src="https://youradserver.com/banner.html"
                width="320" height="100" style="border:none;overflow:hidden;"></iframe>
    </div>
    """, height=120)
    return "테스트 모드 응답"

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
    """, height=300)

    # 광고 배너
    components.html("""
    <div style='text-align:center;margin:20px 0;'>
        <iframe src="https://youradserver.com/banner.html"
                width="320" height="100" style="border:none;overflow:hidden;"></iframe>
    </div>
    """, height=120)

    # 관리자 비밀번호 입력
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
                st.success("🎉 이용권이 적용되었습니다! 채팅으로 이동 중...")
                time.sleep(1)
                st.session_state.clear()
                st.query_params = {"uid": USER_ID, "page": "chat"}
                st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")

    # 피드백
    st.markdown("---")
    st.subheader("💌 서비스 피드백")
    feedback = st.text_area("무엇이든 자유롭게 남겨주세요 💬", placeholder="예: 결제 안내가 헷갈렸어요 / 상담이 따뜻했어요 😊")

    if st.button("📩 피드백 보내기"):
        if feedback.strip():
            try:
                db.collection("feedback").add({
                    "uid": USER_ID,
                    "feedback": feedback.strip(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                st.success("💖 피드백이 소중히 전달되었습니다. 감사합니다!")
            except Exception as e:
                st.error(f"Firestore 오류: {e}")
        else:
            st.warning("내용을 입력해주세요 💬")

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ================= 상태칩 =================
def status_chip():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", 0)
        total = st.session_state.get("limit", 30)
        st.markdown(f"<div class='status'>💎 유료 이용중 — 남은 {left}/{total}회</div>", unsafe_allow_html=True)
    else:
        left = st.session_state["limit"] - st.session_state["usage_count"]
        st.markdown(f"<div class='status'>🌱 무료 체험 — 남은 {max(left,0)}회</div>", unsafe_allow_html=True)

# ================= 채팅 =================
def render_chat_page():
    status_chip()
    today = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.get("last_use_date") != today:
        persist_user({"usage_count": 0, "last_use_date": today})

    if not st.session_state.get("is_paid") and st.session_state["usage_count"] >= DAILY_FREE_LIMIT:
        st.warning("🌙 오늘의 무료 상담 7회를 모두 사용했어요!")
        if st.button("🎬 광고 보기로 3회 추가하기"):
            components.html("""
            <div style='text-align:center;margin:10px 0;'>
                <iframe src="https://youradserver.com/ad.html"
                        width="320" height="100" style="border:none;"></iframe>
            </div>
            """, height=120)
            time.sleep(3)
            persist_user({"usage_count": st.session_state["usage_count"] - BONUS_AFTER_AD})
            st.success("🎉 광고 시청 완료! 추가 3회가 지급되었어요 💙")
        return

    if "greeted" not in st.session_state:
        greetings = [
            "안녕 💙 오늘 하루 많이 지쳤지? 내가 들어줄게 ☁️",
            "마음이 조금 무거운 날이지? 나랑 얘기하자 🌙",
            "괜찮아, 그냥 나한테 털어놔도 돼 🌷",
            "오늘은 힘든 일 있었어? 내가 곁에 있을게 🕊️"
        ]
        st.markdown(f"<div class='bot-bubble'>🧡 {random.choice(greetings)}</div>", unsafe_allow_html=True)
        st.session_state["greeted"] = True

    user_input = st.chat_input("지금 어떤 기분이예요?")
    if not user_input: return

    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    reply = stream_reply(user_input)
    if not reply: return

    if st.session_state.get("is_paid"):
        persist_user({"remaining_paid_uses": st.session_state["remaining_paid_uses"] - 1})
    else:
        persist_user({"usage_count": st.session_state["usage_count"] + 1})

# ================= Sidebar & Routing =================
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

if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()



