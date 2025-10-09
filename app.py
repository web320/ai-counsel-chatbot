# ==========================================
# 💙 AI 심리상담 앱 v2.1.1
# (AdSense 메타태그 추가 버전 — 기존 기능 그대로 유지)
# ==========================================
import os, uuid, json, time, random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= App Config =================
APP_VERSION = "v2.1.1"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 30
DEFAULT_TONE = "따뜻하게"
RESET_INTERVAL_HOURS = 4
ADMIN_KEYS = ["4321"]  # 🔐 관리자 비밀번호 (절대 노출 금지)

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
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= UI =================
st.set_page_config(page_title="💙 마음을 기댈 수 있는 따뜻한 AI 친구", layout="wide")

# ✅ 구글 애드센스 메타태그 삽입 (사이트 소유권 검증용)
st.markdown("""
<meta name="google-adsense-account" content="ca-pub-5846666879010880">
""", unsafe_allow_html=True)

# ================= CSS =================
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
  font-size:15px;padding:8px 12px;border-radius:10px;
  display:inline-block;margin-bottom:8px;background:rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 따뜻한 AI 친구")

# ================= 이하 기존 코드 동일 =================
# (Firestore / 감정 분석 / 채팅 / 결제 / 피드백 등 그대로)
# --------------------------------------------------------
defaults = {
    "is_paid": False,
    "usage_count": 0,
    "remaining_paid_uses": 0,
    "last_reset": datetime.utcnow().isoformat()
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
        return "사용자가 불안을 표현했습니다. 다정하고 안정감을 주는 말로 답해주세요."
    if any(w in msg for w in ["외로워", "혼자", "쓸쓸", "고독"]):
        return "사용자가 외로움을 표현했습니다. 따뜻하게 곁에 있어주는 말로 위로해주세요."
    if any(w in msg for w in ["힘들", "귀찮", "하기 싫", "지쳤"]):
        return "사용자가 무기력을 표현했습니다. 존재를 인정하며 다정하게 공감해주세요."
    if any(w in msg for w in ["싫어", "쓸모없", "못해", "가치없"]):
        return "사용자가 자기혐오를 표현했습니다. 자존감을 세워주는 따뜻한 말로 위로해주세요."
    return "일상 대화입니다. 공감하며 따뜻하게 대화를 이어가주세요."

# ================= 스트리밍 응답 =================
def stream_reply(user_input: str):
    try:
        emotion_prompt = get_emotion_prompt(user_input)
        full_prompt = f"""
{emotion_prompt}

너는 따뜻하고 공감력 높은 전문 심리상담사야.
한 문장씩 타이핑하듯 자연스럽게 말하되, 너무 짧지 않게 이야기해줘.
5~7문장을 기본으로, 필요시 10문장까지 괜찮아.
사용자의 감정을 충분히 인정하고, 현실적으로 도움이 될 수 있는 구체적 제안을 포함해줘.

사용자: {user_input}
AI:"""

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "너는 공감력 있고 따뜻한 상담사야. 현실적인 위로와 해결책을 함께 말해."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.8,
            max_tokens=600,
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
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": full_text.strip(),
            "created_at": datetime.utcnow().isoformat()
        })
        return full_text.strip()
    except Exception as e:
        st.error(f"AI 응답 오류: {e}")
        return None

# ================= 결제 및 피드백 =================
def render_payment_and_feedback():
    st.markdown("---")
    st.markdown("### 💳 결제 안내")
    components.html(f"""
    <div style="text-align:center">
      <a href="{PAYPAL_URL}" target="_blank">
        <button style="background:#ffaa00;color:black;padding:12px 20px;border:none;border-radius:10px;font-size:18px;">
          💳 PayPal로 결제하기 ($3)
        </button>
      </a>
      <p style="opacity:0.9;margin-top:14px;line-height:1.6;font-size:17px;">
        결제 후 <b style="color:#FFD966;">카톡 ID: jeuspo</b> 또는
        <b style="color:#9CDCFE;">이메일: mwiby91@gmail.com</b> 으로 스크린샷을 보내주세요.<br>
        🔒 확인 후 비밀번호 입력 시 30회 이용권이 즉시 적용됩니다.
      </p>
    </div>
    """, height=260)

    st.subheader("🔑 관리자 비밀번호 입력")
    pw = st.text_input(" ", type="password", placeholder="관리자 전용 비밀번호 입력")
    if pw:
        if pw.strip() in ADMIN_KEYS:
            persist_user({"is_paid": True, "remaining_paid_uses": BASIC_LIMIT})
            st.success("✅ 인증 성공! 30회 이용권이 활성화되었습니다.")
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")

    st.markdown("---")
    st.subheader("💌 서비스 피드백")
    feedback = st.text_area("소중한 의견을 남겨주세요 💬", placeholder="예: 상담이 정말 따뜻했어요 🌷")
    if st.button("📩 피드백 보내기"):
        text = feedback.strip()
        if text:
            try:
                db.collection("feedbacks").document(str(uuid.uuid4())).set({
                    "uid": USER_ID,
                    "feedback": text,
                    "created_at": datetime.utcnow().isoformat()
                })
                st.success("💖 피드백이 안전하게 저장되었습니다. 감사합니다!")
            except Exception as e:
                st.error(f"⚠️ 피드백 저장 오류: {e}")
        else:
            st.warning("내용을 입력해주세요 💬")

# ================= 상태 표시 =================
def status_chip():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = "💎 유료 이용중"
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = "🌱 무료 체험중"
    st.markdown(f"<div class='status'>{plan} — 남은 {max(left,0)}회</div>", unsafe_allow_html=True)

# ================= 채팅 =================
def render_chat_page():
    status_chip()
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    elapsed = (now - last_reset).total_seconds() / 3600

    if elapsed >= RESET_INTERVAL_HOURS:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info("⏰ 무료 상담이 다시 가능해졌어요! (4시간마다 자동 복구)")

    usage = st.session_state["usage_count"]
    if not st.session_state.get("is_paid") and usage >= DAILY_FREE_LIMIT:
        st.warning("🌙 오늘의 무료 상담 7회를 모두 사용했어요!")
        st.info("💳 결제 안내 및 피드백으로 이동합니다.")
        time.sleep(1.2)
        render_payment_and_feedback()
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

    if st.session_state.get("is_paid"):
        persist_user({"remaining_paid_uses": st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1})
    else:
        persist_user({"usage_count": usage + 1})

    if (not st.session_state.get("is_paid")) and st.session_state["usage_count"] >= DAILY_FREE_LIMIT:
        st.info("🌙 오늘의 무료 상담이 모두 소진되었습니다.")
        render_payment_and_feedback()

# ================= Sidebar =================
st.sidebar.header("📜 대화 기록")
st.sidebar.markdown(f"**사용자 ID:** `{USER_ID[:8]}...`")
st.sidebar.markdown("---")
if st.sidebar.button("💳 결제 및 피드백 열기"):
    render_payment_and_feedback()

# ================= ads.txt 라우트 (💡 맨 위로 이동!) =================
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ================= 실행 =================
render_chat_page()


# ================= 실행 =================
render_chat_page()

