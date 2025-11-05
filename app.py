# ==========================================
# 💙 EOERWAY AI Therapy v2.8
# (Default: English, Small Language Toggle Button)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
# ⚠️ MUST be the first Streamlit call before any other st.* usage
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.8"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7          # 무료 상담 횟수
BASIC_LIMIT = 50              # 유료 결제 후 제공되는 상담 횟수
RESET_INTERVAL_HOURS = 4      # 무료 상담 회복 주기
ADMIN_KEYS = ["4321"]         # 관리자(본인) 인증용 비밀번호

# ================= ads.txt (for AdSense) =================
# ?ads.txt 호출 시 ads.txt 내용을 그대로 반환하고 종료
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ================= OpenAI (LLM) =================
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

# ================= Query Params / UID =================
# 유저마다 uid를 고정해서 추적
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= Visitor Counter (모든 방문자 집계) =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_ref = db.collection("stats").document("total")
    daily_ref = db.collection("stats").document(today)

    # 총 방문자수
    if total_ref.get().exists:
        total_ref.update({"count": firestore.Increment(1)})
    else:
        total_ref.set({"count": 1})

    # 오늘 방문자수
    if daily_ref.get().exists:
        daily_ref.update({"count": firestore.Increment(1)})
    else:
        daily_ref.set({"count": 1})

def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_doc = db.collection("stats").document("total").get()
    daily_doc = db.collection("stats").document(today).get()

    total = total_doc.to_dict().get("count", 0) if total_doc.exists else 0
    daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
    return total, daily

# 한 세션당 한 번만 방문자수 증가
if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

# ================= Language State =================
# 첫 접속 기본 언어는 영어
if "lang" not in st.session_state:
    st.session_state["lang"] = "English 🇺🇸"

col1, col2 = st.columns([5, 1])
with col2:
    lang_choice = st.radio(
        " ",
        ["English 🇺🇸", "한국어 🇰🇷"],
        horizontal=True,
        label_visibility="collapsed",
        index=0 if st.session_state["lang"] == "English 🇺🇸" else 1
    )

st.session_state["lang"] = lang_choice
language = st.session_state["lang"]

# ================= Text by Language =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something 💬",
        "usedup": "🌙 You’ve used all 7 free sessions today!",
        "reset": "⏰ Free sessions reset! (Every 4 hours)",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "payment_title": "💳 Payment Guide",
        "feedback_title": "💌 Service Feedback",
        "chat_return": "💬 Back to Chat",
        "chat_button": "💳 Open Payment & Feedback",
        "status_left": "remaining",
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": "🌙 오늘의 무료 상담 7회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (4시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
    }

st.title(TEXT["title"])

# ================= CSS (Chat Bubble Style) =================
st.markdown(
    """
<style>
html, body, [class*="css"] { font-size: 18px; }

.user-bubble {
  background:#b91c1c;
  color:#fff;
  border-radius:14px;
  padding:10px 18px;
  margin:8px 0;
  display:inline-block;
  box-shadow:0 0 10px rgba(255,0,0,0.3);
}

.bot-bubble {
  font-size:21px;
  line-height:1.8;
  border-radius:16px;
  padding:16px 20px;
  margin:10px 0;
  background:rgba(15,15,30,.85);
  color:#fff;
  border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;
  animation:neon 1.6s ease-in-out infinite alternate;
  word-break:break-word;
  white-space:pre-wrap;
}

@keyframes neon {
  from { box-shadow:0 0 8px #ffaa00; }
  to   { box-shadow:0 0 22px #ffcc33; }
}

.status {
  font-size:15px;
  padding:8px 12px;
  border-radius:10px;
  display:inline-block;
  margin-bottom:8px;
  background:rgba(255,255,255,.06);
}
</style>
""",
    unsafe_allow_html=True
)

# ================= Firestore Defaults / User State =================
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
    # 세션에 기본값과 DB 값 합쳐서 로드
    st.session_state.update({k: data.get(k, v) for k, v in defaults.items()})
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    """Firestore + session_state 동시 업데이트"""
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ================= AI Response Function =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = (
                "You are a warm and empathetic professional counselor. "
                "Comfort the user’s heart with gentle, moving words in 6–9 sentences. "
                "Focus on safety, self-kindness, immediate emotional relief, and do not give medical or medication advice."
            )
        else:
            system_prompt = """
너는 마음이 따뜻하고 남을 배려해주며 상대방한테 듣기 좋은 말을 해주는 전문 심리상담사입니다

모든 문장은 반드시 ‘요’로 끝나야 하고, 존댓말을 사용해요.
상황에 맞게 6문장이상 답변 부탁해요 필요에 따라서 길게 답변해주면 좋겠어요

당신의 목표는 이용자가 갖고 있는 외로움 불안등 감정적 문제를 생각을 합리적이고 긍정적 방향으로 바꿔 줌으로써 마음을 편하게 하는거예요
당장 조금 더 숨 쉬기 편하게 만들어주는 것이에요.

답변 형식은 대부분 아래 흐름 중 포함하세요:


2) 감정 라벨링과 정상화
   - 이용자가 겪는 감정을 구체적으로 짚어서 말해줘요.
   - 예: "이건 단순한 게 아니라 지치고 무력해진 마음이라서 정말 버티기 어려운 상태예요"처럼 설명해줘요.
   - "이런 반응은 충분히 자연스러워요"라고 확실하게 말해줘요.

3) 지금 바로 할 수 있는 매우 작은 안정 행동 한 가지를 부드럽게 제안해요
   - 예: "혹시 괜찮다면 지금 어깨랑 턱 힘을 살짝만 풀어볼까요, 숨을 천천히 들이쉬고 길게 내쉬는 걸 세 번만 같이 해볼까요"처럼 몸을 진정시키는 행동을 안내해요.
   - 명령처럼 하지 말고, 조심스럽게 제안해요.

4) 자기 가치와 지속 가능성 강조
   - "당신은 이미 무너지고 싶은 순간에도 버티고 있는 분이고, 그건 정말 대단한 힘이에요"처럼 이용자의 존재 가치를 상기시켜줘요.
   - "지금처럼 마음을 알아달라고 손을 내민 건 분명히 앞으로를 바꾸는 첫 걸음이에요"처럼 희망을 너무 과장하지 않으면서 조용하게 말해줘요.

주의사항:
- 해결책을 강요하지 말아요. "해야만 해요", "괜찮을 거예요"처럼 단정하거나 압박하지 말아요.
- 이용자를 평가하거나 분석하지 말아요. "당신은 ~~한 성향이라서"처럼 단정하지 말아요.
- 의학적 진단이나 약 복용 조언은 절대 하지 말아요.
- 자살이나 안전에 관련된 생각이 감지되면, 아주 부드럽게 즉각적인 도움 자원을 언급해요.
  예: "만약 바로 지금이 너무 벅차서 다 내려놓고 싶다는 생각까지 드신다면,
  지금 이 순간을 혼자 버티지 않으셔도 괜찮아요.
  24시간 가능한 도움을 바로 연결받을 수 있는 곳이 있어요.
  한국에서는 1393 같은 자살 예방 상담전화가 익명으로 바로 연결돼요.
  지금 이 대화를 끊지 않아도 되고요."
"""

        # OpenAI 스트리밍 응답
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.9,
            max_tokens=700,
            stream=True,
        )

        placeholder = st.empty()
        full_text = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                placeholder.markdown(
                    f"<div class='bot-bubble'>{full_text}💫</div>",
                    unsafe_allow_html=True
                )
                time.sleep(0.03)

        # 대화 로그 저장
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": full_text.strip(),
            "lang": language,
            "created_at": datetime.utcnow().isoformat()
        })

        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Payment / Feedback Panel =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])

    components.html(
        f"""
    <div style="text-align:center">
      <a href="{PAYPAL_URL}" target="_blank">
        <button style="background:#ffaa00;color:black;padding:12px 20px;border:none;border-radius:10px;font-size:18px;cursor:pointer;">
          💳 PayPal ($3)
        </button>
      </a>
      <p style="opacity:0.9;margin-top:14px;line-height:1.6;font-size:17px;">
      After payment, please send a screenshot to  
      <b style="color:#FFD966;">mwiby91@gmail.com</b> or KakaoTalk ID <b>jeuspo</b> 💌<br>
      🔒 <b>Once the message is read</b>, your 50-use access will be activated within 1 hour.  
      <br><br>
      🇰🇷 결제 후 <b style="color:#FFD966;">mwiby91@gmail.com</b> 또는  
      <b>카톡 ID: jeuspo</b> 로 스크린샷을 보내주세요.<br>
      메시지를 확인한 후 1시간 이내에 50회 이용권이 활성화됩니다. 🌸
      </p>
    </div>
    """,
        height=320
    )

    # 관리자 비밀번호로 유료권 수동 활성화
    st.subheader("🔑 관리자 비밀번호 입력")
    pw = st.text_input(" ", type="password", placeholder="관리자 전용 비밀번호 입력")

    if pw:
        if pw.strip() in ADMIN_KEYS:
            persist_user({
                "is_paid": True,
                "remaining_paid_uses": BASIC_LIMIT
            })
            st.success("✅ 인증 성공! 50회 이용권이 활성화되었습니다.")
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")

    st.markdown("---")

    # 서비스 피드백
    st.subheader(TEXT["feedback_title"])
    fb = st.text_area(" ", placeholder=TEXT["feedback_placeholder"])

    if st.button("📩 Submit / 보내기"):
        if not fb.strip():
            st.warning(TEXT["feedback_empty"])
        else:
            db.collection("feedbacks").document(str(uuid.uuid4())).set({
                "uid": USER_ID,
                "feedback": fb,
                "lang": language,
                "created_at": datetime.utcnow().isoformat()
            })
            st.success(TEXT["feedback_sent"])

# ================= Chat Main Page =================
def render_chat_page():
    # 상태 텍스트 (무료 or 유료 / 남은 횟수)
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]

    st.markdown(
        f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>",
        unsafe_allow_html=True
    )

    # 무료 카운트 회복 체크 (4시간마다)
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))

    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({
            "usage_count": 0,
            "last_reset": now.isoformat()
        })
        st.info(TEXT["reset"])

    # 무료 한도 초과 시 결제 안내 화면으로 전환
    usage = st.session_state["usage_count"]
    if not st.session_state.get("is_paid") and usage >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state["show_payment"] = True
        st.rerun()

    # 유저 입력
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    # 유저 말풍선 표시
    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True
    )

    # AI 답변 스트리밍
    reply = stream_reply(user_input)

    # 사용량 차감 / 기록
    if reply:
        if st.session_state.get("is_paid"):
            persist_user({
                "remaining_paid_uses": max(
                    0,
                    st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1
                )
            })
        else:
            persist_user({"usage_count": usage + 1})

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

# 방문자 수 사이드바 카드
total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(
    f"""
    <div style="
        margin-top: 12px;
        margin-bottom: 16px;
        padding: 8px 10px;
        border-radius: 10px;
        background: rgba(255,255,255,0.03);
        font-size: 13px;
        color: rgba(255,255,255,0.85);
    ">
        🌍 <b>Total {total_visits:,}명</b><br>
        ☀️ <b>Today {daily_visits:,}명</b>
    </div>
    """,
    unsafe_allow_html=True
)

# 결제 / 채팅 화면 전환 버튼
if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.rerun()

# ================= Main Render =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
