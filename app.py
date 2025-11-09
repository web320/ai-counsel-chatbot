# ==========================================
# 💙 EOERWAY AI Therapy v3.0 — Chat History + Payment Guide Update
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v3.0"
DAILY_FREE_LIMIT = 15
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 6
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

# ================= Visitor Counter =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_visit_ref = db.collection("user_visits").document(USER_ID)

    if user_visit_ref.get().exists:
        return
    user_visit_ref.set({
        "uid": USER_ID,
        "first_visit": datetime.utcnow().isoformat(),
        "day": today,
    })

    total_ref = db.collection("stats").document("total")
    daily_ref = db.collection("stats").document(today)

    if total_ref.get().exists:
        total_ref.update({"count": firestore.Increment(1)})
    else:
        total_ref.set({"count": 1})

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

# ================= Language =================
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

# ================= Text =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something 💬",
        "usedup": "🌙 You’ve used all 15 free sessions today!",
        "reset": "⏰ Free sessions reset every 6 hours!",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "payment_title": "💳 Payment Guide",
        "feedback_title": "💌 Service Feedback",
        "chat_return": "💬 Back to Chat",
        "chat_button": "💳 Open Payment & Feedback",
        "status_left": "remaining",
        "payment_desc": "✨ 50 sessions for just $3 — your support helps us keep growing 💕"
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": "🌙 오늘의 무료 상담 15회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (6시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
        "payment_desc": "✨ 50회 이용권 3,000원 — 여러분의 응원이 큰 힘이 됩니다 💕"
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown("""
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
""", unsafe_allow_html=True)

# ================= User Defaults =================
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

# ================= AI Response =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = """
You’re talking to someone who came here because they’re hurting.
Be a kind, real person — not a therapist.
1. Listen first.
2. Name their feeling specifically.
3. Say it makes sense.
4. If natural, suggest one tiny helpful action (like 3 deep breaths).
5. End warmly, not formally.
4–6 gentle sentences, never clinical.
If they mention self-harm, respond with compassion and gently recommend professional help."""
        else:
            system_prompt = """
상처받고 힘들어서 여기 온 사람이에요. 친구처럼 따뜻하게 이야기해 주세요.
1. 먼저 공감해 주세요.
2. 구체적으로 감정을 짚어 주세요.
3. 이런 감정이 당연하다고 말해 주세요.
4. 가능하면 지금 바로 할 수 있는 아주 작은 행동 한 가지를 제안해 주세요.
5. 마지막은 "혼자가 아니다"는 느낌으로 마무리해 주세요.
4~6문장, 모두 요로 끝나게, 존댓말로. 진단이나 약 관련 이야기는 금지. 자살 언급시 1393 권유."""

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.7,
            max_tokens=700,
            stream=True,
        )

        bot_placeholder = st.empty()
        full_text = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                bot_placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
                time.sleep(0.03)

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

# ================= Payment / Feedback =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])
    st.markdown(TEXT["payment_desc"])

    intent_ref = db.collection("purchase_intent").document(USER_ID)
    intent_doc = intent_ref.get()
    clicked = intent_doc.exists
    total_intents = len(list(db.collection("purchase_intent").stream()))

    st.markdown("#### 💎 50 uses / 3,000원 ($3 USD)")

    if clicked:
        st.info("💙 You’ve already shown interest. Thank you for your support!")
    else:
        if st.button("💳 I’m interested in purchasing / 결제 의사 있습니다"):
            intent_ref.set({
                "uid": USER_ID,
                "plan": "50회_3000원",
                "created_at": datetime.utcnow().isoformat(),
            })
            st.success("You’ll be notified first when payment opens 💖")
            st.rerun()

    st.caption(f"So far, {total_intents} users have shown interest 💕")

    st.markdown("---")
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

# ================= Chat Page =================
def render_chat_page():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]

    st.markdown(f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>", unsafe_allow_html=True)

    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info(TEXT["reset"])

    usage = st.session_state["usage_count"]
    if not st.session_state.get("is_paid") and usage >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state["show_payment"] = True
        st.rerun()

    # 대화 기록 유지 및 표시
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    chat_container = st.container()
    for chat in st.session_state["chat_history"]:
        if chat["role"] == "user":
            chat_container.markdown(f"<div class='user-bubble'>{chat['content']}</div>", unsafe_allow_html=True)
        else:
            chat_container.markdown(f"<div class='bot-bubble'>{chat['content']}</div>", unsafe_allow_html=True)

    user_input = st.chat_input(TEXT["input"])
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        chat_container.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

        reply = stream_reply(user_input)
        if reply:
            st.session_state.chat_history.append({"role": "bot", "content": reply})

        if st.session_state.get("is_paid"):
            persist_user({"remaining_paid_uses": max(0, st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1)})
        else:
            persist_user({"usage_count": usage + 1})

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")
total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(f"""
<div style="margin-top:12px; padding:8px 10px; border-radius:10px; background:rgba(255,255,255,0.03); font-size:13px; color:rgba(255,255,255,0.85);">
🌍 <b>Total {total_visits:,}</b><br>☀️ <b>Today {daily_visits:,}</b>
</div>
""", unsafe_allow_html=True)

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
