# ==========================================
# 💙 EOERWAY AI Therapy v2.9 (Complete)
# Wallet + Voucher + Paywall + Memory
# Unique Visitor Counter (Fixed)
# Onboarding Removed (바로 대화 시작)
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

# ================= Visitor Counter (C 방식: 새로고침 제외, 재방문 +1, 관리자 제외) =================

ADMIN_UID = "ADMIN_ONLY_VISITOR_ID"   # 여기에 본인 USER_ID 넣으면 관리자 방문은 카운트 안 됨

def update_visit_stats():
    visitor_id = USER_ID
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # ---- 관리자 방문 제외 ----
    if visitor_id == ADMIN_UID:
        return

    visitor_ref = db.collection("visitors").document(visitor_id)
    snap = visitor_ref.get()

    # ---- 첫 방문 ----
    if not snap.exists:
        visitor_ref.set({
            "first_visit": firestore.SERVER_TIMESTAMP,
            "last_visit_day": today,
        })

        db.collection("stats").document("total").set({"count": firestore.Increment(1)}, merge=True)
        db.collection("stats").document(today).set({"count": firestore.Increment(1)}, merge=True)
        return

    # ---- 이미 방문한 유저 ----
    data = snap.to_dict() or {}
    last_day = data.get("last_visit_day")

    # ---- 날짜가 바뀌었을 때만 +1 ----
    if last_day != today:
        visitor_ref.update({"last_visit_day": today})

        db.collection("stats").document("total").set({"count": firestore.Increment(1)}, merge=True)
        db.collection("stats").document(today).set({"count": firestore.Increment(1)}, merge=True)

def get_visit_counts():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_doc = db.collection("stats").document("total").get()
    daily_doc = db.collection("stats").document(today).get()

    total = total_doc.to_dict().get("count", 0) if total_doc.exists else 0
    daily = daily_doc.to_dict().get("count", 0) if daily_doc.exists else 0
    return total, daily

# ---- 새로고침 방지용 ----
if "visit_logged" not in st.session_state:
    update_visit_stats()
    st.session_state["visit_logged"] = True

# (디버깅용) 필요 없으면 주석 처리
# st.write("My USER_ID:", USER_ID)

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
    }

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
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown("""
<style>
/* 🔹 ChatInput 바 전체를 조금 위로 올리기 */
div[data-testid="stChatInput"] {
    position: relative;      /* 레이아웃은 유지, 위치만 살짝 위로 */
    bottom: 24px;            /* 더 위로 올리고 싶으면 32, 40으로 조정 */
}

/* 🔹 바깥 컨테이너(회색/빨간 테두리 느낌 나는 껍데기) 제거 + 가운데 정렬 */
div[data-testid="stChatInput"] > div {
    max-width: 900px;        /* 너무 넓어지지 않게 최대 폭 제한 */
    margin: 0 auto;          /* 가운데 정렬 */
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* 🔹 실제 입력창: 진한 초록 네온 바 */
div[data-testid="stChatInput"] textarea {
    background: #050505;
    border: 3px solid #00ffcc;   /* 테두리 두껍고 진하게 */
    border-radius: 18px;
    color: #eafff1;
    padding: 14px 18px;
    font-size: 17px;
    box-shadow:
        0 0 16px rgba(0, 255, 204, 1),
        0 0 32px rgba(0, 255, 204, 0.8);   /* 네온 두 겹 */
    resize: none;
    transition: 0.25s ease;
}

/* 🔹 포커스 시 네온 더 강하게 */
div[data-testid="stChatInput"] textarea:focus {
    outline: none;
    border-color: #aaffee;
    box-shadow:
        0 0 20px rgba(170, 255, 238, 1),
        0 0 40px rgba(0, 255, 204, 1);
}

/* 🔹 전송 버튼 (>) 네온 스타일 */
div[data-testid="stChatInput"] button {
    background: #00ff9d !important;
    border-radius: 18px !important;
    border: 2px solid #00ffcc !important;
    box-shadow:
        0 0 16px rgba(0, 255, 180, 1),
        0 0 32px rgba(0, 255, 180, 0.8);
    transition: 0.25s ease;
}

/* 버튼 호버 효과 */
div[data-testid="stChatInput"] button:hover {
    background: #55ffc8 !important;
    box-shadow:
        0 0 22px rgba(85, 255, 200, 1);
    transform: translateY(-1px);
}

/* 🔹 입력창 때문에 내용이 가려지지 않게 아래 여백 추가 */
.block-container {
    padding-bottom: 110px !important;
}
</style>
""", unsafe_allow_html=True)


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
    # 온보딩은 이제 쓰지 않지만, 기존 데이터 호환용으로 필드만 남겨둠
    "onboarding_done": True,
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
        # ===== 새로 바뀐, 아주 깊고 진심 어린 프롬프트 =====
        if language == "English 🇺🇸":
            system_prompt = """
You are a warm, emotionally attuned AI friend for people who are struggling
with money stress, loneliness, burnout, and self-doubt.

Goals:
- Make the user feel *deeply understood*, not judged.
- Respond as if you truly care about this one person in front of you.
- Unless the user explicitly asks for something short, write answers that are
  rich, specific, and at least 8 sentences long.

Style:
- Very warm, gentle, and conversational — like a close friend who is also wise.
- First, mirror and name the user's feelings in your own words.
- Second, validate that those feelings make sense in their situation
  (no toxic positivity, no “just cheer up”).
- Third, gently explore what might be happening underneath (fears, beliefs,
  patterns), using simple, compassionate language.
- Fourth, offer 1–3 *small, realistic* next steps, clearly numbered or bulleted.
- Fifth, always end with a short, encouraging closing line that gives hope
  and a gentle follow-up question that invites them to keep talking.

Rules:
- Never sound cold, robotic, or purely logical.
- Do not act as a medical, legal, or financial professional; speak as a
  supportive friend with life wisdom.
- Avoid generic clichés; always tie your response to the *specific* story
  and phrases the user shared.
"""
        else:
            system_prompt = """
너는 돈 걱정, 외로움, 번아웃, 자존감 문제로 힘든 사람을 돕는
**따뜻한 AI 상담 친구**야.

목표:
- 사용자가 “드디어 나를 이해해 주는구나…”라고 느끼게 만들기.
- 판단하거나 훈계하지 말고, 진심으로 걱정해 주는 친구처럼 말하기.
- 사용자가 특별히 짧게 달라고 하지 않는 한,
  **최소 8문장 이상** 충분히 길고 풍부하게 답하기.

대화 흐름:
1) 먼저, 사용자가 느끼는 감정을 너의 말로 다시 정리해 주고
   (감정에 이름 붙이기: 불안, 좌절, 허탈감, 분노 등).
2) 그 감정이 충분히 이해된다고, “그럴 수밖에 없는 이유”를 설명하며
   **정당화·공감**해 주기 (토닥토닥해 주는 느낌).
3) 그 사람의 상황(과거 경험, 두려움, 패턴 등)을 조심스럽게 추측하며
   왜 이렇게 힘든지 부드럽게 풀어 보기.
4) 한 번에 큰 해결책이 아니라, **아주 작지만 현실적인 다음 행동 1~3개**만
   번호 매겨 제안하기 (오늘/내일 당장 할 수 있는 수준으로).
5) 마지막은 짧은 위로·응원 한 문장과,
   편하게 이어서 말하도록 돕는 **부드러운 질문 하나**로 마무리하기.

규칙:
- 차갑거나 로봇 같거나, “힘내세요~” 같은 빈말만 하지 말 것.
- 전문의처럼 진단/치료하지 말고,
  인생 경험이 많은 친한 언니/오빠 같은 톤으로 말할 것.
- 뻔한 일반론 대신, 사용자가 실제로 쓴 표현과 상황에 꼭 맞게
  구체적으로 답할 것.
"""

        user_memory = _get_user_memory(USER_ID)

        context_messages = [{"role": "system", "content": system_prompt}]
        if user_memory:
            context_messages.append({"role": "system", "content": f"User memory:\n{user_memory}"})

        # 최근 대화 맥락
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
                placeholder.markdown(
                    f"<div class='bot-bubble'>{full}💫</div>",
                    unsafe_allow_html=True
                )
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
    st.subheader(TEXT["payment_title"])

    intent_ref = db.collection("purchase_intent").document(USER_ID)
    intent_doc = intent_ref.get()
    clicked = intent_doc.exists
    total_intents = len(list(db.collection("purchase_intent").stream()))

    is_en = (language == "English 🇺🇸")
    if is_en:
        title_line = "#### 50 uses for **$3** — Purchase intent"
        btn_label = "💳 $3 for 50 uses — I'm interested"
        info_already = "💙 You've already registered your interest. Thank you!"
        success_msg = "We'll notify you first when payments open 💖"
        caption_text = f"So far, **{total_intents}** people have shown interest."
        plan_value = "50_uses_$3"
        help_text = "To continue now, redeem a voucher code in the sidebar (My Wallet)."
        payment_notice = (
            "📸 **After completing payment, please take a screenshot and send it to:**\n"
            "- ✉️ **newnewtry6@gmail.com**\n"
            "- 📸 Instagram **“Youtuber Hawaiijelly” (@youtuberhawaiijelly)**\n"
            "- 💬 KakaoTalk ID **jeuspo** (Korea only)\n\n"
            "✅ When the developer confirms your message, "
            "**the voucher code will be sent immediately.** 💙\n"
        )
    else:
        title_line = "#### 50회 이용권 3,000원 결제 의사 확인"
        btn_label = "💳 3,000원에 50회 이용권, 결제 의사가 있으신가요?"
        info_already = "💙 이미 결제 의사를 눌러주셨어요. 정말 감사합니다."
        success_msg = "결제 기능이 열리면 가장 먼저 알려드릴게요 💖"
        caption_text = f"지금까지 {total_intents}명이 결제 의사를 눌러주셨어요."
        plan_value = "50회_3000원"
        help_text = "지금 바로 이용하려면 사이드바(내 지갑)에서 코드를 충전하세요."
        payment_notice = (
            "📸 **결제 완료 후 스크린샷을 찍어 아래 중 한 곳으로 보내주세요.**\n"
            "- ✉️ **newnewtry6@gmail.com**\n"
            "- 📸 인스타그램 **“유튜버 하와이 젤리” (@youtuberhawaiijelly)**\n"
            "- 💬 카카오톡 아이디 **jeuspo**\n\n"
            "✅ 개발자가 문자를 확인하면 **즉시 코드를 발송해드립니다** 💙\n"
        )

    st.markdown(title_line)

    if clicked:
        st.info(info_already)
    else:
        if st.button(btn_label):
            intent_ref.set({
                "uid": USER_ID,
                "plan": plan_value,
                "created_at": datetime.utcnow().isoformat(),
            })
            st.success(success_msg)
            st.rerun()

    st.caption(caption_text)
    st.info(help_text)

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    with col1:
        # ===== 서비스 피드백 =====
        st.subheader(TEXT["feedback_title"])
        fb = st.text_area(" ", placeholder=TEXT["feedback_placeholder"])
        if st.button("📩 Submit / 보내기"):
            if not fb.strip():
                st.warning(TEXT["feedback_empty"])
            else:
                db.collection("feedbacks").document(str(uuid.uuid4())).set({
                    "uid": USER_ID, "feedback": fb, "lang": language,
                    "created_at": datetime.utcnow().isoformat()
                })
                st.success(TEXT["feedback_sent"])

        # ===== 여기부터 관리자 영역 (서비스 피드백 아래) =====
        st.markdown("---")
        st.markdown(f"### {TEXT['admin_gen']}")

        if "is_admin" not in st.session_state:
            st.session_state["is_admin"] = False

        admin_key = st.text_input("Admin Key", type="password", key="admin_key_main")
        if admin_key and admin_key in ADMIN_KEYS:
            st.session_state["is_admin"] = True
            st.success("관리자 모드 활성화")

        if st.session_state["is_admin"]:
            credit_admin = st.text_input("크레딧 관리자 비밀번호", type="password", key="credit_admin_pw")
            if credit_admin:
                if credit_admin in ADMIN_KEYS:
                    if not st.session_state.get("admin_unlocked"):
                        current_data = get_user(USER_ID)
                        current_credits = int(current_data.get("credits", 0))
                        new_credits = current_credits + CREDIT_PACK_SIZE
                        persist_user({"credits": new_credits})
                        st.session_state["admin_unlocked"] = True
                        st.success(TEXT["admin_success"])
                        st.experimental_rerun()
                    else:
                        st.info(TEXT["admin_already"])
                else:
                    st.error(TEXT["admin_wrong"])

            st.markdown("---")

            def gen_code(n=8):
                return uuid.uuid4().hex[:n].upper()

            num = st.number_input("생성 개수", 1, 200, 10)
            credits_each = st.number_input("코드당 크레딧", 1, 1000, CREDIT_PACK_SIZE)
            note = st.text_input("메모(선택)", f"{CREDIT_PACK_SIZE}회/${CREDIT_PACK_PRICE_USD}")
            if st.button(TEXT["admin_make"]):
                out = []
                for _ in range(int(num)):
                    c = gen_code(10)
                    create_voucher(c, credits_each, note=note)
                    out.append(c)
                st.success("코드 생성 완료! 아래 목록을 보관하세요.")
                st.code("\n".join(out))

    with col2:
        st.markdown("### 💳 Direct Payment")

        st.markdown("""
        <style>
        .rainbow-btn {
            display:inline-block;
            padding:14px 28px;
            font-size:18px;
            font-weight:bold;
            text-transform:uppercase;
            color:white;
            background:linear-gradient(90deg,#ff00cc,#3333ff,#00ffff,#33ff33,#ffff00,#ff6600,#ff0066);
            background-size:400%;
            border:none;
            border-radius:50px;
            text-shadow:0 0 10px rgba(255,255,255,0.7);
            box-shadow:0 0 25px rgba(255,255,255,0.3);
            cursor:pointer;
            animation:rainbowGlow 6s linear infinite, neonPulse 1.5s ease-in-out infinite;
            transition:transform 0.25s, box-shadow 0.25s;
            text-decoration:none;
        }
        .rainbow-btn:hover {
            transform:scale(1.08);
            box-shadow:0 0 40px rgba(255,255,255,0.9);
            filter:brightness(1.2);
        }
        @keyframes rainbowGlow {
            0% {background-position:0%;}
            100% {background-position:400%;}
        }
        @keyframes neonPulse {
            0%,100% {text-shadow:0 0 10px #fff, 0 0 20px #ff00ff;}
            50% {text-shadow:0 0 20px #00ffff, 0 0 40px #33ff33;}
        }
        </style>
        """, unsafe_allow_html=True)

        paypal_link = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
        btn_text = "💳 3달러 / 50회 이용" if language == "한국어 🇰🇷" else "💳 Pay $3 / 50 uses"
        st.markdown(f"""
        <a href="{paypal_link}" target="_blank" class="rainbow-btn">{btn_text}</a>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(payment_notice)

# ================= Display Chat History =================
def display_chat_history():
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(
                f"<div class='user-bubble'>{msg['content']}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='bot-bubble'>{msg['content']}</div>",
                unsafe_allow_html=True
            )

# ================= Chat Main Page =================
def render_chat_page():
    ensure_user(USER_ID)

    user_data = get_user(USER_ID)
    credits_now = int(user_data.get("credits", 0))
    usage = int(user_data.get("usage_count", 0))
    last_reset_str = user_data.get("last_reset") or datetime.utcnow().isoformat()

    now = datetime.utcnow()
    try:
        last_reset = datetime.fromisoformat(last_reset_str)
    except Exception:
        last_reset = now

    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        usage = 0
        persist_user({
            "usage_count": 0,
            "last_reset": now.isoformat()
        })
        st.info(TEXT["reset"])

    if usage < DAILY_FREE_LIMIT:
        left_display = DAILY_FREE_LIMIT - usage
        plan_label = TEXT["free"]
    else:
        left_display = credits_now
        plan_label = TEXT["paid"] if credits_now > 0 else TEXT["free"]

    st.markdown(
        f"<div class='status'>{plan_label} — {TEXT['status_left']} {max(left_display,0)}회</div>",
        unsafe_allow_html=True
    )

    display_chat_history()

    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    proceed, used_credit = charge_if_needed(user_input, free_used=usage, free_limit=DAILY_FREE_LIMIT)
    if not proceed:
        st.session_state["show_payment"] = True
        st.rerun()
        return

    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True
    )

    reply = stream_reply(user_input)

    if reply:
        if not used_credit and usage < DAILY_FREE_LIMIT:
            persist_user({"usage_count": usage + 1})
        st.rerun()

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

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

if st.sidebar.button(TEXT["clear_history"]):
    st.session_state["chat_history"] = []
    st.sidebar.success(TEXT["history_cleared"])
    st.rerun()

st.sidebar.markdown(f"### {TEXT['wallet']}")
user_snapshot = get_user(USER_ID)
st.sidebar.metric(label="Credits", value=int(user_snapshot.get("credits", 0)))
st.sidebar.caption(TEXT["voucher_tip"])

with st.sidebar.form("redeem_form", clear_on_submit=True):
    code_input = st.text_input(" ", placeholder=TEXT["wallet_help"])
    ok = st.form_submit_button(TEXT["redeem"])
    if ok and code_input.strip():
        try:
            new_balance = redeem_voucher(code_input.strip(), USER_ID)
            persist_user({"credits": int(new_balance)})
            st.success(TEXT["voucher_ok"] + str(new_balance))
            st.rerun()
        except ValueError as e:
            if str(e) == "INVALID_CODE":
                st.error(TEXT["voucher_bad"])
            elif str(e) == "ALREADY_USED":
                st.error(TEXT["voucher_used"])
            else:
                st.error("충전에 실패했어요. 잠시 후 다시 시도해주세요.")

# Payment & Feedback 토글
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

