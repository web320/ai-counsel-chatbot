# ==========================================
# 💙 AI 심리상담 앱 v1.9.4
# (광고 제거 + 결제/피드백 유지 + 실시간 스트리밍)
# ==========================================
import os, uuid, json, time, hmac, random
from datetime import datetime, date
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= App Config =================
APP_VERSION = "v1.9.4"
PAYPAL_URL  = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
DEFAULT_TONE = "따뜻하게"

# ================= OpenAI =================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

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
uid  = st.query_params.get("uid", [str(uuid.uuid4())])[0]
page = st.query_params.get("page", ["chat"])[0]
st.query_params = {"uid": uid, "page": page}
USER_ID = uid
PAGE = page

# ================= UI 설정 =================
st.set_page_config(page_title="💙 마음을 기댈 수 있는 따뜻한 AI 친구", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
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
@keyframes neon {from{box-shadow:0 0 8px #ffaa00;}to{box-shadow:0 0 22px #ffcc33;} }
.status {
  font-size:15px; padding:8px 12px; border-radius:10px;
  display:inline-block;margin-bottom:8px; background:rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)
st.title("💙 마음을 기댈 수 있는 따뜻한 AI 친구")

# ================= Firestore User =================
defaults = {
    "is_paid": False, "usage_count": 0,
    "remaining_paid_uses": 0, "last_use_date": str(date.today())
}
user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    st.session_state.update({k: data.get(k, v) for k, v in defaults.items()})
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ================= 감정 인식 =================
def get_emotion_prompt(msg: str):
    msg = msg.lower()
    if any(w in msg for w in ["불안", "초조", "걱정", "긴장"]):
        return "사용자가 불안을 표현했습니다. 다정하고 안정감을 주는 말로 3~4문장으로 답해주세요."
    if any(w in msg for w in ["외로워", "혼자", "쓸쓸", "고독"]):
        return "사용자가 외로움을 표현했습니다. 따뜻하게 곁에 있어주는 말로 3~4문장으로 위로해주세요."
    if any(w in msg for w in ["힘들", "귀찮", "하기 싫", "지쳤"]):
        return "사용자가 무기력을 표현했습니다. 존재를 인정하며 다정한 말로 3~4문장으로 공감해주세요."
    if any(w in msg for w in ["싫어", "쓸모없", "못해", "가치없"]):
        return "사용자가 자기혐오를 표현했습니다. 자존감을 세워주는 말로 3~4문장으로 답해주세요."
    return "일상 대화입니다. 따뜻하고 인간적인 말로 3~4문장 이내로 대화해주세요."

# ================= 스트리밍 AI 응답 =================
def stream_reply(user_input: str):
    try:
        emotion_prompt = get_emotion_prompt(user_input)
        full_prompt = f"{emotion_prompt}\n\n{DEFAULT_TONE}로 답변해주세요.\n사용자: {user_input}\nAI:"
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 따뜻하고 다정한 AI 상담사야. 인간처럼 부드럽게, 문장마다 감정을 담아 말해줘."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.85,
            max_tokens=280,
            stream=True,
        )

        placeholder = st.empty()
        full_text = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
                time.sleep(0.03)
        return full_text.strip()
    except Exception as e:
        st.error(f"AI 응답 오류: {e}")
        return None

# ================= 상태 표시 =================
def status_chip():
    left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
    st.markdown(f"<div class='status'>🌱 무료 체험 — 남은 {max(left,0)}회</div>", unsafe_allow_html=True)

# ================= 결제/피드백 페이지 =================
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
    st.subheader("💌 서비스 피드백")
    feedback_text = st.text_area("무엇이든 자유롭게 남겨주세요 💬", 
                                 placeholder="예: 상담이 따뜻했어요 😊")
    if st.button("📩 피드백 보내기"):
        text = feedback_text.strip()
        if text:
            db.collection("feedbacks").add({
                "uid": USER_ID,
                "feedback": text,
                "created_at": datetime.now().isoformat()
            })
            st.success("💖 피드백이 전달되었습니다. 감사합니다!")
        else:
            st.warning("내용을 입력해주세요 💬")

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ================= 채팅 페이지 =================
def render_chat_page():
    status_chip()
    today = str(date.today())
    if st.session_state.get("last_use_date") != today:
        persist_user({"usage_count": 0, "last_use_date": today})

    if st.session_state["usage_count"] >= DAILY_FREE_LIMIT:
        st.warning("🌙 오늘의 무료 상담 7회를 모두 사용했어요!")
        if st.button("💳 결제하러 가기"):
            st.query_params = {"uid": USER_ID, "page": "plans"}
            st.success("💎 결제 안내로 이동 중이에요...")
            time.sleep(1)
            st.rerun()
        return

    if "greeted" not in st.session_state:
        greetings = [
            "안녕 💙 오늘 하루 많이 지쳤지? 내가 들어줄게 ☁️",
            "마음이 조금 무거운 날이지? 나랑 얘기하자 🌙",
            "괜찮아, 그냥 나한테 털어놔도 돼 🌷"
        ]
        st.markdown(f"<div class='bot-bubble'>🧡 {random.choice(greetings)}</div>", unsafe_allow_html=True)
        st.session_state["greeted"] = True

    user_input = st.chat_input("지금 어떤 기분이예요?")
    if not user_input:
        return

    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    reply = stream_reply(user_input)
    if not reply:
        return

    persist_user({"usage_count": st.session_state["usage_count"] + 1})

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

if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()
