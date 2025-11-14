# ==========================================
# 💙 EOERWAY AI Therapy v2.9 (Complete)
# Wallet + Voucher + Paywall + Memory + Onboarding
# Unique Visitor Counter (Fixed)
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
APP_VERSION = "v2.9"
DAILY_FREE_LIMIT = 7
RESET_INTERVAL_HOURS = 4
BASIC_LIMIT = 50
ADMIN_KEYS = ["2356"]

CREDIT_PACK_SIZE = 50
CREDIT_PACK_PRICE_USD = 3

CRISIS_KEYWORDS = [
    "죽고싶", "자살", "해치고", "극단적", "고통스러워", "살기 싫", "포기하고 싶",
    "suicide", "self-harm", "kill myself", "end my life"
]

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

# ================= Unique Visitor ID (브라우저 고유값) =================
if "unique_visitor_id" not in st.session_state:
    st.session_state["unique_visitor_id"] = str(uuid.uuid4())

USER_ID = st.session_state["unique_visitor_id"]

# ================= Visitor Counter =================
def update_visit_stats():
    visitor_id = USER_ID
    today = datetime.utcnow().strftime("%Y-%m-%d")

    visitor_ref = db.collection("visitors").document(visitor_id)
    if visitor_ref.get().exists:
        return

    visitor_ref.set({
        "first_visit": firestore.SERVER_TIMESTAMP,
        "day": today,
    })

    total_ref = db.collection("stats").document("total")
    total_ref.set({"count": firestore.Increment(1)}, merge=True)

    daily_ref = db.collection("stats").document(today)
    daily_ref.set({"count": firestore.Increment(1)}, merge=True)

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
        "usedup": f"🌙 You've used all {DAILY_FREE_LIMIT} free sessions today!",
        "reset": f"⏰ Free sessions reset! (Every {RESET_INTERVAL_HOURS} hours)",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "payment_title": "💳 Payment Guide",
        "feedback_title": "💌 Service Feedback",
        "chat_return": "💬 Back to Chat",
        "chat_button": "💳 Open Payment & Feedback",
        "status_left": "remaining",
        "admin_success": "🔓 Admin mode granted 50 credits!",
        "admin_already": "✅ Already added in this session.",
        "admin_wrong": "❌ Wrong admin password.",
        "clear_history": "🗑️ Clear Chat History",
        "history_cleared": "Chat history has been cleared!",
        "wallet": "💙 My Wallet",
        "wallet_help": "Paste your voucher code to redeem.",
        "redeem": "Redeem",
        "voucher_ok": "Done! Credits: ",
        "voucher_bad": "Invalid code.",
        "voucher_used": "This code was already used.",
        "paywall": "You've used all free limits. Redeem a code to continue.",
        "voucher_tip": f"One code = {CREDIT_PACK_SIZE} uses / ${CREDIT_PACK_PRICE_USD}",
        "admin_gen": "🔑 Admin — Generate Voucher Codes",
        "admin_make": "Generate",
        # Onboarding
        "ob_title": "💙 Before we start, can you tell me just three things?",
        "ob_desc": "So I can talk less like a robot and more like a friend.",
        "ob_q1": "1) What's the area that feels hardest these days?",
        "ob_q2": "2) Describe your current state in one line:",
        "ob_q3": "3) What would you like most from today's chat?",
        "ob_placeholder_q2": "e.g., I feel stuck and stressed about money.",
        "ob_placeholder_q3": "e.g., I just want comfort and one small next step.",
        "ob_start_btn": "Start Chat",
        "ob_required": "Please fill at least one line 💙",
        "ob_saved": "Got it. I'll remember this during our talks 💙",
    }

    ONBOARDING_TOPICS = [
        "Money / income",
        "Work / study / burnout",
        "Relationships / friends",
        "Family / romance",
        "Health / sleep",
        "Life feels hard in general",
        "Other (I'll write)",
    ]
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": f"🌙 무료 상담 {DAILY_FREE_LIMIT}회를 모두 사용했어요",
        "reset": f"⏰ 무료 상담이 복구되었어요 ({RESET_INTERVAL_HOURS}시간마다)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
        "admin_success": "🔓 관리자 모드로 50회 충전됨!",
        "admin_already": "✅ 이미 추가되었습니다",
        "admin_wrong": "❌ 관리자 비밀번호가 틀렸어요",
        "clear_history": "🗑️ 대화 기록 지우기",
        "history_cleared": "대화 기록 삭제됨!",
        "wallet": "💙 내 지갑",
        "wallet_help": "바우처 코드를 붙여넣어 충전하세요",
        "redeem": "충전하기",
        "voucher_ok": "충전 완료! 잔여 크레딧: ",
        "voucher_bad": "코드가 올바르지 않아요",
        "voucher_used": "이미 사용된 코드예요",
        "paywall": "무료 한도를 모두 사용했어요. 코드를 충전해 주세요",
        "voucher_tip": f"코드 1개 = {CREDIT_PACK_SIZE}회 / ${CREDIT_PACK_PRICE_USD}",
        "admin_gen": "🔑 관리자 — 바우처 코드 생성",
        "admin_make": "코드 생성",
        # Onboarding
        "ob_title": "💙 대화를 시작하기 전에, 딱 세 가지만 알려주세요",
        "ob_desc": "그렇게 해야 정말 나를 아는 친구처럼 이야기할 수 있어요.",
        "ob_q1": "1) 요즘 가장 힘든 분야는?",
        "ob_q2": "2) 지금 내 상태를 한 줄로 표현한다면?",
        "ob_q3": "3) 오늘 대화에서 가장 얻고 싶은 건?",
        "ob_placeholder_q2": "예: 돈 걱정 때문에 하루종일 불안해요.",
        "ob_placeholder_q3": "예: 위로 한 마디와 아주 작은 행동 하나요.",
        "ob_start_btn": "시작하기",
        "ob_required": "한 줄이라도 적어주시면 도와드릴 수 있어요 💙",
        "ob_saved": "기억해 둘게요. 앞으로 참고할게요 💙",
    }

    ONBOARDING_TOPICS = [
        "돈 / 수입",
        "일 / 번아웃",
        "인간관계",
        "가족 / 연애",
        "건강 / 수면",
        "그냥 사는 게 힘들어요",
        "기타 (직접 적기)",
    ]

st.title(TEXT["title"])

# ================= CSS =================
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

# ================= Chat History =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ================= Firestore Defaults / User State =================
defaults = {
    "is_paid": False,
    "usage_count": 0,
    "remaining_paid_uses": 0,
    "last_reset": datetime.utcnow().isoformat(),
    "credits": 0,
    "purchased_packs": 0,
    "ad_free": False,
    # Onboarding
    "onboarding_done": False,
    "ob_topic": "",
    "ob_feeling_line": "",
    "ob_today_goal": "",
}

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()

if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        st.session_state.setdefault(k, data.get(k, v))
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)
# ================= Long-term Memory (read-only) =================
def _get_user_memory(uid: str) -> str:
    doc = db.collection("users").document(uid).collection("memory").document("profile").get()
    if doc.exists:
        return (doc.to_dict() or {}).get("text", "")
    return ""

# ================= Long-term Memory (update) =================
def update_user_memory(uid: str, user_input: str, reply: str, language: str):
    try:
        mem_ref = db.collection("users").document(uid).collection("memory").document("profile")
        prev_doc = mem_ref.get()
        prev_text = ""
        if prev_doc.exists:
            prev_text = (prev_doc.to_dict() or {}).get("text", "")

        if language == "English 🇺🇸":
            system_prompt = """
You maintain a short, evolving psychological + contextual profile of this user.
Keep it compact, 3rd-person, and focused on recurring themes and what responses help them."""
            user_prompt = f"""
[Previous memory]
{prev_text}

[New message]
{user_input}

[Assistant reply]
{reply}

Update in 5–9 lines including:
- Ongoing themes (money stress, loneliness, burnout, etc.)
- Emotional patterns
- Thinking style
- Helpful response styles
- 1–2 key points to remember next time
"""
        else:
            system_prompt = """
너는 한 사용자의 감정 패턴과 반복되는 고민을 짧게 정리하는 AI야.
제3자 시점으로 간단하게 ‘이 사람이 어떤 경향을 보인다’만 적어 줘."""
            user_prompt = f"""
[이전 메모]
{prev_text}

[사용자 메시지]
{user_input}

[AI 응답]
{reply}

요약을 5~9줄로 새로 정리해 주세요:
- 반복되는 고민
- 감정 패턴
- 말투/사고 스타일
- 도움되는 위로 방식
- 다음 대화를 위해 기억할 점
"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=400,
        )
        new_text = completion.choices[0].message.content.strip()
        if not new_text:
            return

        mem_ref.set({
            "text": new_text,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "last_user_message": user_input,
            "last_reply": reply,
            "lang": language,
        }, merge=True)

    except Exception as e:
        print("memory update error:", e)


# ================= Wallet / Voucher Helpers =================
def ensure_user(uid: str):
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if not snap.exists:
        ref.set(defaults, merge=True)
    return ref

def get_user(uid: str) -> dict:
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() or {}

def create_voucher(code: str, credits: int, note: str = "", created_by: str = "admin"):
    db.collection("vouchers").document(code).set({
        "credits": int(credits),
        "usd_price": CREDIT_PACK_PRICE_USD,
        "created_by": created_by,
        "used_by": None,
        "used_at": None,
        "expires_at": None,
        "note": note,
        "created_at": firestore.SERVER_TIMESTAMP,
    })

def redeem_voucher(code: str, uid: str):
    voucher_ref = db.collection("vouchers").document(code)
    user_ref = db.collection("users").document(uid)

    @firestore.transactional
    def _tx(transaction):
        v_snap = voucher_ref.get(transaction=transaction)
        if not v_snap.exists:
            raise ValueError("INVALID_CODE")

        v = v_snap.to_dict()
        if v.get("used_by"):
            raise ValueError("ALREADY_USED")

        u_snap = user_ref.get(transaction=transaction)
        u = u_snap.to_dict() if u_snap.exists else defaults

        new_credits = int(u.get("credits", 0)) + int(v.get("credits", 0))
        new_packs = int(u.get("purchased_packs", 0)) + 1

        transaction.update(user_ref, {
            "credits": new_credits,
            "purchased_packs": new_packs,
            "last_reset": u.get("last_reset"),
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        transaction.update(voucher_ref, {
            "used_by": uid,
            "used_at": firestore.SERVER_TIMESTAMP,
        })
        return new_credits

    transaction = db.transaction()
    return _tx(transaction)

def decrement_credit(uid: str, amount: int = 1):
    user_ref = db.collection("users").document(uid)

    @firestore.transactional
    def _tx(transaction):
        snap = user_ref.get(transaction=transaction)
        data = snap.to_dict() or {}
        curr = int(data.get("credits", 0))
        if curr < amount:
            raise ValueError("NO_CREDIT")
        transaction.update(user_ref, {"credits": curr - amount})
        return curr - amount

    tx = db.transaction()
    return _tx(tx)


# ================= AI Response =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = """
You're a warm AI friend. Listen gently, acknowledge feelings, avoid generic advice."""
        else:
            system_prompt = """
너는 따뜻한 AI 친구야. 공감 → 지지 → 작은 제안 → 따뜻한 마무리 흐름으로 작성해 줘."""

        user_memory = _get_user_memory(USER_ID)
        user_doc = get_user(USER_ID)

        onboarding_info = ""
        if user_doc.get("onboarding_done"):
            lines = []
            if user_doc.get("ob_topic"): lines.append(f"- Topic: {user_doc['ob_topic']}")
            if user_doc.get("ob_feeling_line"): lines.append(f"- State: {user_doc['ob_feeling_line']}")
            if user_doc.get("ob_today_goal"): lines.append(f"- Goal: {user_doc['ob_today_goal']}")
            onboarding_info = "\n".join(lines)

        context_messages = [{"role": "system", "content": system_prompt}]
        if user_memory:
            context_messages.append({"role": "system", "content": f"User memory:\n{user_memory}"})
        if onboarding_info:
            context_messages.append({"role": "system", "content": f"Onboarding:\n{onboarding_info}"})

        recent_history = st.session_state["chat_history"][-10:]
        for msg in recent_history:
            context_messages.append(msg)

        context_messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=context_messages,
            temperature=0.7,
            max_tokens=900,
            stream=True,
        )

        placeholder = st.empty()
        full = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full += delta.content
                placeholder.markdown(f"<div class='bot-bubble'>{full}💫</div>", unsafe_allow_html=True)
                time.sleep(0.03)

        reply_text = full.strip()
        timestamp = datetime.utcnow().isoformat()

        # Firebase chat log
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": reply_text,
            "lang": language,
            "created_at": timestamp
        })

        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        st.session_state["chat_history"].append({"role": "assistant", "content": reply_text})

        update_user_memory(USER_ID, user_input, reply_text, language)

        return reply_text

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None


# ================= Paywall =================
def is_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in [k.lower() for k in CRISIS_KEYWORDS])

def show_paywall():
    st.warning(TEXT["paywall"])
    st.markdown(f"- {CREDIT_PACK_SIZE}회 = ${CREDIT_PACK_PRICE_USD}")

def charge_if_needed(user_input: str, free_used: int, free_limit: int):
    if is_crisis(user_input):
        return True, False

    if free_used < free_limit:
        return True, False

    try:
        left = decrement_credit(USER_ID, 1)
        persist_user({"credits": left})
        st.toast(f"크레딧 1회 사용됨 (잔여 {left})")
        return True, True
    except:
        show_paywall()
        return False, False


# ================= Payment & Feedback =================
def render_payment_and_feedback():
    st.markdown("---")
    st.markdown("## 💳 결제 안내")

    intent_ref = db.collection("purchase_intent").document(USER_ID)
    clicked = intent_ref.get().exists
    total_intents = len(list(db.collection("purchase_intent").stream()))

    is_en = (language == "English 🇺🇸")

    # ==================== TEXT ====================
    if is_en:
        pay_btn_label = "💳 $3 / 50 uses"
        intent_btn_label = "💙 I'm interested in purchasing"
        already = "You've already expressed your interest 💙"
        success_msg = "Thank you! You'll be notified first 💖"
        count_text = f"{total_intents} people have shown interest."
        pay_desc_title = "📸 After payment, please send a screenshot to:"
        pay_notice = """
- ✉️ **Email:** newnewtry6@gmail.com  
- 📸 **Instagram:** @youtuberhawaiijelly  
- 💬 **KakaoTalk ID:** jeuspo  
"""
    else:
        pay_btn_label = "💳 3,000원 / 50회 이용"
        intent_btn_label = "💙 50회 이용권 결제 의사 표시"
        already = "이미 결제 의사를 눌러주셨어요 💙"
        success_msg = "고맙습니다! 결제가 열리면 가장 먼저 알려드릴게요 💖"
        count_text = f"{total_intents}명이 결제 의사를 표시했어요."
        pay_desc_title = "📸 결제 후 스크린샷을 아래로 보내주세요:"
        pay_notice = """
- ✉️ **이메일:** newnewtry6@gmail.com  
- 📸 **인스타그램:** @youtuberhawaiijelly  
- 💬 **카카오톡:** jeuspo  
"""

    # ================ PAYPAL RAINBOW BUTTON CSS ================
    st.markdown("""
    <style>
    .center-box { text-align:center; }

    .pay-btn {
        display:inline-block;
        padding:17px 34px;
        font-size:22px;
        font-weight:700;
        color:white;
        border-radius:50px;
        background:linear-gradient(90deg,#ff00cc,#3333ff,#00ffff,#33ff33,#ffff00,#ff6600,#ff0066);
        background-size:400%;
        text-shadow:0 0 12px rgba(255,255,255,0.9);
        animation:rainbowGlow 6s linear infinite, pulse 1.8s ease-in-out infinite;
        box-shadow:0 0 30px rgba(255,255,255,0.3);
        text-decoration:none;
        transition:0.25s ease;
    }
    .pay-btn:hover {
        transform:scale(1.07);
        box-shadow:0 0 40px rgba(255,255,255,0.8);
        filter:brightness(1.15);
    }

    @keyframes rainbowGlow { 0%{background-position:0%} 100%{background-position:400%} }
    @keyframes pulse {
        0%,100% { text-shadow:0 0 14px #fff, 0 0 30px #ff00ff; }
        50%     { text-shadow:0 0 24px #00ffff, 0 0 50px #33ff33; }
    }

    .screenshot-box {
        margin-top:18px;
        padding:18px;
        border-radius:14px;
        background:rgba(255,255,255,0.05);
        border:1px solid rgba(255,255,255,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

    # ===================== PAYPAL BUTTON =====================
    paypal_url = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"

    st.markdown("<div class='center-box'>", unsafe_allow_html=True)
    st.markdown(
        f"<a href='{paypal_url}' target='_blank' class='pay-btn'>{pay_btn_label}</a>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ===================== Screenshot Notice =====================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"### {pay_desc_title}")
    st.markdown(f"<div class='screenshot-box'>{pay_notice}</div>", unsafe_allow_html=True)

    # ===================== Purchase Intent Button =====================
    st.markdown("---")
    st.markdown("### 🔹 결제 의사 표시 | Purchase Intent")

    if clicked:
        st.info(already)
    else:
        if st.button(intent_btn_label, use_container_width=True):
            intent_ref.set({
                "uid": USER_ID,
                "plan": "50_uses",
                "created_at": datetime.utcnow().isoformat(),
            })
            st.success(success_msg)
            st.rerun()

    st.caption(count_text)

    # ====================== Feedback ======================
    st.markdown("---")
    st.markdown(f"### {TEXT['feedback_title']}")
    fb = st.text_area(" ", placeholder=TEXT['feedback_placeholder'])
    if st.button("📩 Submit / 보내기", use_container_width=True):
        if fb.strip():
            db.collection("feedbacks").add({
                "uid": USER_ID,
                "feedback": fb,
                "lang": language,
                "created_at": datetime.utcnow().isoformat()
            })
            st.success(TEXT["feedback_sent"])
        else:
            st.warning(TEXT["feedback_empty"])

    # ====================== Admin Section ======================
    st.markdown("---")
    st.markdown(f"### {TEXT['admin_gen']}")

    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False

    admin_key = st.text_input("Admin Key", type="password")
    if admin_key and admin_key in ADMIN_KEYS:
        st.session_state["is_admin"] = True
        st.success("관리자 모드 활성화")

    if st.session_state["is_admin"]:
        st.write("관리자 전용 기능:")

        credit_pw = st.text_input("크레딧 비밀번호", type="password")
        if credit_pw and credit_pw in ADMIN_KEYS:
            current = get_user(USER_ID).get("credits", 0)
            new = current + CREDIT_PACK_SIZE
            persist_user({"credits": new})
            st.success("50 크레딧 지급 완료!")
            st.rerun()

        st.markdown("---")
        st.markdown("#### 바우처 생성")

        num = st.number_input("생성 개수", 1, 200, 10)
        each = st.number_input("코드당 크레딧", 1, 1000, CREDIT_PACK_SIZE)

        if st.button("코드 생성", use_container_width=True):
            out = []
            for _ in range(int(num)):
                c = uuid.uuid4().hex[:10].upper()
                create_voucher(c, each)
                out.append(c)
            st.code("\n".join(out))
            st.success("코드 생성 완료!")



# ================= Onboarding =================
def render_onboarding():
    user_data = get_user(USER_ID)
    if user_data.get("onboarding_done"):
        return

    st.markdown("---")
    st.markdown(f"### {TEXT['ob_title']}")
    st.write(TEXT["ob_desc"])

    with st.form("onboarding_form"):
        topic = st.selectbox(TEXT["ob_q1"], ONBOARDING_TOPICS)
        other = ""
        if topic == ONBOARDING_TOPICS[-1]:
            other = st.text_input(" ", placeholder="내용 입력")

        q2 = st.text_area(TEXT["ob_q2"], placeholder=TEXT["ob_placeholder_q2"])
        q3 = st.text_area(TEXT["ob_q3"], placeholder=TEXT["ob_placeholder_q3"])

        ok = st.form_submit_button(TEXT["ob_start_btn"])

    if ok:
        final_topic = other.strip() if topic == ONBOARDING_TOPICS[-1] and other else topic

        if not (final_topic or q2.strip() or q3.strip()):
            st.warning(TEXT["ob_required"])
        else:
            persist_user({
                "onboarding_done": True,
                "ob_topic": final_topic,
                "ob_feeling_line": q2.strip(),
                "ob_today_goal": q3.strip(),
            })
            st.success(TEXT["ob_saved"])
            time.sleep(0.7)
            st.rerun()


# ================= Chat History =================
def display_chat_history():
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)


# ================= Chat Page =================
def render_chat_page():
    user_data = get_user(USER_ID)

    credits = int(user_data.get("credits", 0))
    usage = int(user_data.get("usage_count", 0))
    last_reset = datetime.fromisoformat(user_data.get("last_reset"))

    now = datetime.utcnow()
    if (now - last_reset).total_seconds() >= RESET_INTERVAL_HOURS * 3600:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        usage = 0
        st.info(TEXT["reset"])

    if usage < DAILY_FREE_LIMIT:
        left = DAILY_FREE_LIMIT - usage
        plan = TEXT["free"]
    else:
        left = credits
        plan = TEXT["paid"] if credits > 0 else TEXT["free"]

    st.markdown(f"<div class='status'>{plan} — {TEXT['status_left']} {left}</div>", unsafe_allow_html=True)

    display_chat_history()

    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    proceed, used_credit = charge_if_needed(user_input, usage, DAILY_FREE_LIMIT)
    if not proceed:
        st.session_state["show_payment"] = True
        st.rerun()
        return

    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

    reply = stream_reply(user_input)

    if reply and not used_credit and usage < DAILY_FREE_LIMIT:
        persist_user({"usage_count": usage + 1})

    st.rerun()


# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(
    f"""
    <div style="
        margin-top:10px;
        padding:8px;
        border-radius:8px;
        background:rgba(255,255,255,0.05);
    ">
        🌍 Total: <b>{total_visits:,}</b><br>
        ☀️ Today: <b>{daily_visits:,}</b>
    </div>
    """,
    unsafe_allow_html=True
)

if st.sidebar.button(TEXT["clear_history"]):
    st.session_state["chat_history"] = []
    st.sidebar.success(TEXT["history_cleared"])
    st.rerun()

st.sidebar.markdown(f"### {TEXT['wallet']}")
info = get_user(USER_ID)
st.sidebar.metric("Credits", int(info.get("credits", 0)))
st.sidebar.caption(TEXT["voucher_tip"])

with st.sidebar.form("redeem_form", clear_on_submit=True):
    code = st.text_input(" ", placeholder=TEXT["wallet_help"])
    ok = st.form_submit_button(TEXT["redeem"])
    if ok and code.strip():
        try:
            bal = redeem_voucher(code.strip(), USER_ID)
            persist_user({"credits": bal})
            st.success(TEXT["voucher_ok"] + str(bal))
            st.rerun()
        except ValueError as e:
            if str(e) == "INVALID_CODE":
                st.error(TEXT["voucher_bad"])
            elif str(e) == "ALREADY_USED":
                st.error(TEXT["voucher_used"])

if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.rerun()


# ================= Main =================
if not get_user(USER_ID).get("onboarding_done"):
    render_onboarding()
else:
    if st.session_state.get("show_payment"):
        render_payment_and_feedback()
    else:
        render_chat_page()
