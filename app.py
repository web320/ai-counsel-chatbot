# ==========================================
# 💙 EOERWAY AI Therapy v2.8 (modified)
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
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.8"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 4
ADMIN_KEYS = ["4321"]

# ================= ads.txt (for AdSense) =================
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
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ================= Visitor Counter (유저당 1회만 카운트) =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_visit_ref = db.collection("user_visits").document(USER_ID)

    # 이미 기록된 유저면 다시 카운트하지 않음
    if user_visit_ref.get().exists:
        return

    user_visit_ref.set({
        "uid": USER_ID,
        "first_visit": datetime.utcnow().isoformat(),
        "day": today,
    })

    total_ref = db.collection("stats").document("total")
    daily_ref = db.collection("stats").document(today)

    # 전체 방문자
    if total_ref.get().exists:
        total_ref.update({"count": firestore.Increment(1)})
    else:
        total_ref.set({"count": 1})

    # 오늘 방문자
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

if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

# ================= Language State =================
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
    st.session_state.update({k: data.get(k, v) for k, v in defaults.items()})
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    """Firestore + session_state 동시 업데이트"""
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ================= AI Response Function (명령문 새 버전) =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = """
You're talking to someone who came here because they're hurting. Not as a "therapist" - as a real person who genuinely cares.

How to respond:

1. First, LISTEN. Really hear what they're saying beneath the words.
   - Don't rush to fix or advise
   - Just be with them in that moment

2. Name what you're sensing - specifically.
   Bad: "That sounds hard"
   Good: "It sounds like you're feeling completely drained, like even getting through the day takes everything you have"

3. Let them know this reaction makes sense.
   - "Of course you feel this way"
   - "Anyone in your situation would struggle with this"

4. Only if it feels natural, gently offer:
   - A slightly different way to see it, OR
   - One tiny thing they could try right now (like taking 3 slow breaths)
   - But don't force it. Sometimes people just need to be heard.

5. End with warmth, not formality.
   Bad: "I'm here if you need to talk more"
   Good: "I'm here. You don't have to figure this out alone"

Respond in 4-6 sentences. Be warm, not clinical. Vary your language - you're a human, not a script.

Critical: Never diagnose or suggest medication. If they mention self-harm/suicide, acknowledge their pain gently while suggesting professional help."""
        else:
            system_prompt = """
상처받고 힘들어서 여기 온 사람이에요. "상담사"처럼 대하지 말고, 진심으로 걱정해주는 사람처럼 대해주세요.

대답하는 방법:

1. 일단, 들어주세요. 말 속에 숨은 진짜 마음을 읽어주세요.
   - 해결하거나 조언하려 하지 마세요
   - 그냥 그 순간 함께 있어주세요

2. 느껴지는 감정을 구체적으로 말해주세요.
   나쁜 예: "힘드시겠어요"
   좋은 예: "하루를 버티는 것만으로도 다 쓰는 것처럼, 완전히 지친 기분이시겠어요"

3. 그런 반응이 당연하다고 말해주세요.
   - "그럴 수밖에 없어요"
   - "누구라도 이런 상황이면 힘들어요"

4. 자연스럽다면, 조심스럽게:
   - 조금 다르게 볼 수 있는 관점을 제시하거나
   - 지금 바로 할 수 있는 아주 작은 것(깊게 숨쉬기 3번 같은) 제안
   - 하지만 강요하지 마세요. 때론 그냥 들어주는 것만으로도 충분해요

5. 마무리는 따뜻하게, 격식 차리지 말고.
   나쁜 예: "언제든 더 이야기하고 싶으시면 말씀해주세요"
   좋은 예: "제가 곁에 있을게요. 혼자 감당하지 않아도 돼요"

4-6문장으로 답하세요. 따뜻하게, 임상적이지 않게. 다양하게 표현하세요 - 당신은 사람이지 스크립트가 아니에요.

모든 문장은 '요'로 끝나는 존댓말이지만, 너무 격식 차리지 말고 친구처럼 편하게 말하세요.

중요: 절대 진단하거나 약 권하지 말아요. 자해/자살 언급이 있으면 고통을 부드럽게 인정하면서 전문가 도움을 제안하세요."""
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

    # 🔹 결제 의사 버튼 (한 유저당 1번만)
    intent_ref = db.collection("purchase_intent").document(USER_ID)
    intent_doc = intent_ref.get()
    clicked = intent_doc.exists

    total_intents = len(list(db.collection("purchase_intent").stream()))

    st.markdown("#### 50회 이용권 3,000원 결제 의사 확인")

    if clicked:
        st.info("💙 이미 결제 의사를 눌러주셨어요. 정말 감사합니다.")
    else:
        if st.button("💳 3,000원에 50회 이용권, 결제 의사가 있으신가요?"):
            intent_ref.set({
                "uid": USER_ID,
                "plan": "50회_3000원",
                "created_at": datetime.utcnow().isoformat(),
            })
            st.success("결제 기능이 열리면 가장 먼저 알려드릴게요 💖")
            st.experimental_rerun()

    st.caption(f"지금까지 {total_intents}명이 결제 의사를 눌러주셨어요.")

    # (선택) 기존 PayPal 안내는 참고용으로만 유지
    components.html(
        f"""
    <div style="text-align:center; margin-top: 16px;">
      <a href="{PAYPAL_URL}" target="_blank">
        <button style="background:#ffaa00;color:black;padding:12px 20px;border:none;border-radius:10px;font-size:18px;cursor:pointer;">
          💳 PayPal 결제 페이지 (참고용)
        </button>
      </a>
      <p style="opacity:0.9;margin-top:14px;line-height:1.6;font-size:17px;">
      실제 결제는 선택 사항이며, 현재는 <b>결제 의사 확인 버튼</b>이 메인 기능이에요 💙
      </p>
    </div>
    """,
        height=260
    )

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
        st.experimental_rerun()

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

# 방문자 수 표시
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

if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.experimental_rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.experimental_rerun()

# ================= Main Render =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()


