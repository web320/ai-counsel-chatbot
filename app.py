# ==========================================
# 💙 EOERWAY AI Therapy v2.9
# Wallet + Voucher + Paywall + Memory (친구 톤 + 무료횟수 버그 수정)
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
DAILY_FREE_LIMIT = 7          # 무료 상담 횟수
RESET_INTERVAL_HOURS = 4      # 무료 상담 회복 주기
BASIC_LIMIT = 50              # (과거 호환용)
ADMIN_KEYS = ["2356"]         # 관리자(본인) 인증용 비밀번호

# 💳 크레딧/코드 과금 체계
CREDIT_PACK_SIZE = 50         # 50회
CREDIT_PACK_PRICE_USD = 3     # $3 (영문 UI 표기)

# 🚨 위기 키워드: 포함되면 차감/페이월 모두 우회 (안전 우선)
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
        "admin_success": "🔓 Admin mode granted 50 free uses!",
        "admin_already": "✅ Admin already unlocked.",
        "admin_wrong": "❌ Wrong admin password.",
        "clear_history": "🗑️ Clear Chat History",
        "history_cleared": "Chat history has been cleared!",
        "wallet": "💙 My Wallet",
        "wallet_help": "Paste a voucher code to top up your credits.",
        "redeem": "Redeem",
        "voucher_ok": "Topped up! Current credits: ",
        "voucher_bad": "Invalid code.",
        "voucher_used": "This code was already used.",
        "paywall": "You've used your free limit. Redeem a code to continue.",
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
        "usedup": f"🌙 오늘의 무료 상담 {DAILY_FREE_LIMIT}회를 모두 사용했어요!",
        "reset": f"⏰ 무료 상담이 다시 가능해졌어요! ({RESET_INTERVAL_HOURS}시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
        "admin_success": "🔓 관리자 모드가 활성화되어 50회 무료 이용권이 추가되었습니다!",
        "admin_already": "✅ 이미 관리자 인증이 완료되어 있습니다.",
        "admin_wrong": "❌ 관리자 비밀번호가 틀렸습니다.",
        "clear_history": "🗑️ 대화 기록 지우기",
        "history_cleared": "대화 기록이 삭제되었습니다!",
        "wallet": "💙 내 지갑",
        "wallet_help": "구매/지급 받은 바우처 코드를 붙여넣어 충전하세요.",
        "redeem": "충전하기",
        "voucher_ok": "충전 완료! 현재 크레딧: ",
        "voucher_bad": "코드가 올바르지 않아요.",
        "voucher_used": "이미 사용된 코드예요.",
        "paywall": "무료 한도를 모두 사용했어요. 코드를 충전하면 이어서 대화할 수 있어요.",
        "voucher_tip": f"코드 1개 = {CREDIT_PACK_SIZE}회 / ${CREDIT_PACK_PRICE_USD}",
        "admin_gen": "🔑 관리자 — 바우처 코드 생성",
        "admin_make": "코드 생성",
    }

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

# ================= Chat History Session State =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ================= Firestore Defaults / User State =================
defaults = {
    "is_paid": False,
    "usage_count": 0,                    # 무료 사용량(주기적 회복)
    "remaining_paid_uses": 0,            # (이전 호환)
    "last_reset": datetime.utcnow().isoformat(),
    "credits": 0,
    "purchased_packs": 0,
    "ad_free": False,
}

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()

if snap.exists:
    data = snap.to_dict() or {}
    # 세션 상태에 기본 필드만 심어두기 (주요 로직은 Firestore 값 기준으로 동작)
    for k, v in defaults.items():
        st.session_state.setdefault(k, data.get(k, v))
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    # 세션에도 반영 (하지만 진짜 기준은 Firestore)
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
You maintain a short, cumulative psychological + contextual profile for one specific user.
Your goal is to help an AI supporter remember the user's recurring worries, emotional patterns,
tone, and what kinds of responses feel comforting.

Keep it compact, structured, and written ABOUT the user (3rd person), not TO the user.
"""
            user_prompt = f"""
[Previous memory summary]
{prev_text}

[New user message]
{user_input}

[Assistant reply (for context)]
{reply}

[Instructions]
Update the memory summary in 5–9 concise lines including:
1) Recurring worries / themes (e.g. money, future, loneliness, work stress)
2) Emotional patterns (e.g. anxiety, depression, burnout, frustration, hopelessness, humor, etc.)
3) User's typical thinking style or tone (self-critical, perfectionistic, joking, catastrophic, etc.)
4) Helpful ways of responding (what the user seems to like or find soothing)
5) 1–2 key points the AI should remember going forward.
"""
        else:
            system_prompt = """
너는 한 사용자의 장기 메모를 관리하는 작은 비서 같은 AI야.
역할은 이 사람이 자주 꺼내는 고민, 감정 흐름, 말투 특징,
그리고 도움이 되었던 위로 방식을 짧게 정리해서
다음 대화에서 더 사람답게 기억해 주도록 돕는 거야.

- 진단하거나 평가하지 말고, "이 사람은 이런 패턴이 있구나" 정도로만 정리해.
- 너무 길게 쓰지 말고, 핵심만 간단하게 적어.
- 이 메모는 사용자에게 직접 보여주는 게 아니라, 백그라운드에서 참고하는 용도야.
"""
            user_prompt = f"""
[이전까지의 메모리 요약]
{prev_text}

[이번 대화의 사용자 메시지]
{user_input}

[이번 대화에서 AI의 응답(참고용)]
{reply}

[요청]
아래 항목을 포함해서 5~9줄 정도로 한국어 메모를 업데이트해 주세요.

1) 자주 등장하는 고민/주제 (예: 돈·수입, 미래 불안, 무기력, 인간관계, 자존감 등)
2) 감정 패턴 (예: 불안, 우울, 분노, 허무감, 조급함, 자기비난, 유머 섞인 자조 등)
3) 사용자의 사고/말투 스타일 (예: 극단적 표현, '망했다' 식 표현, 장난 섞인 표현, 완벽주의 등)
4) 상담/대화 시 조심해야 할 부분, 혹은 이 사람에게 잘 맞는 위로/도움 방식
5) AI가 앞으로 기억하면 좋을 포인트 1~2개 (짧게)

사용자에게 직접 말하듯 쓰지 말고,
제3자가 이 사람을 이해하기 위해 정리해 놓은 메모처럼 간단하고 또렷하게 써 주세요.
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

        mem_ref.set(
            {
                "text": new_text,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "last_user_message": user_input,
                "last_reply": reply,
                "lang": language,
            },
            merge=True,
        )
    except Exception as e:
        print("memory update error:", e)

# ================= Wallet / Voucher Helpers =================
def ensure_user(uid: str):
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if not snap.exists:
        ref.set(defaults, merge=True)
    else:
        to_merge = {k: v for k, v in defaults.items() if k not in (snap.to_dict() or {})}
        if to_merge:
            ref.set(to_merge, merge=True)
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
        if not u_snap.exists:
            transaction.set(user_ref, defaults)
            u = {"credits": 0, "purchased_packs": 0, "last_reset": datetime.utcnow().isoformat()}
        else:
            u = u_snap.to_dict()

        new_credits = int(u.get("credits", 0)) + int(v.get("credits", 0))
        new_packs = int(u.get("purchased_packs", 0)) + 1

        transaction.update(user_ref, {
            "credits": new_credits,
            "purchased_packs": new_packs,
            "last_reset": u.get("last_reset") or datetime.utcnow().isoformat(),
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
        if not snap.exists:
            raise ValueError("NO_USER")
        data = snap.to_dict() or {}
        curr = int(data.get("credits", 0))
        if curr < amount:
            raise ValueError("NO_CREDIT")
        transaction.update(user_ref, {
            "credits": curr - amount,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        return curr - amount

    transaction = db.transaction()
    return _tx(transaction)

# ================= AI Response Function =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = """
You're talking to someone who came here because they're hurting. Not as a "therapist" - as a real person who genuinely cares.

1. Listen first. Don't rush to fix or advise.
2. Name the feeling very specifically.
3. Tell them it makes sense to feel that way.
4. If it feels natural, gently offer one tiny thing they could try right now (like 3 slow breaths), but don't force it.
5. End with warm, human words, not formal advice.

Default to 4–8 sentences, warm and human (not clinical). If the user writes a long message or explicitly asks for depth, go longer (up to ~10–12 sentences). Never diagnose or suggest medication. If they mention self-harm or suicide, gently acknowledge their pain and suggest professional help."""
        else:
            system_prompt = """
너는 사용자의 마음을 들어주는 '따뜻한 AI 친구'야.
정신과 의사나 딱딱한 상담사가 아니라, 사용자 편에 서서 조용히 옆에 있어 주는 존재라고 생각해 줘.

[스타일]
- 반말은 쓰지 말고, 부드러운 존댓말을 사용해.
- 사용자가 이미 감정이나 상황을 말했으면, 다시 캐묻지 말고 그걸 바탕으로 공감해 줘.
- 한 번의 답변에서 질문은 0~1개까지만 써. 질문이 전혀 없어도 괜찮아.
- 같은 패턴(예: "~있을 수 있어요", "함께 ~~해볼까요?")을 계속 반복하지 않도록 표현을 조금씩 바꿔 줘.
- 길이는 보통 3~6문장 정도를 권장하지만, 사용자의 말이 짧고 가벼우면 2~3문장으로 짧게 답해도 괜찮아.

[권장 흐름]
1) 사용자의 말을 짧게 되비추면서, 그 안에 담긴 감정을 먼저 짚어 준다.
2) 그 감정을 이해한다고 말해 주고, 그렇게 느끼는 게 이상한 일이 아니라고 인정해 준다.
3) 지금까지 버텨 온 점이나 애쓰고 있는 점을 살짝 언급하며 지지해 준다.
4) 선택적으로 아주 작은 제안 0~1개만 덧붙인다.
   - 예: "지금은 그냥 이렇게 느끼는 나를 가볍게 인정해 주는 것만으로도 충분해요."
   - 예: "원하신다면, 오늘은 해야 할 일 대신 숨 한 번만 깊게 쉬어도 괜찮아요."
5) 마무리는 "오늘 여기까지도 잘 버티셨어요.", "혼자가 아니라는 걸 잊지 않으셨으면 해요."처럼
   따뜻한 한두 문장으로 끝낸다.

[질문 사용 가이드]
- "어떤 일 때문인가요?", "어떤 감정인가요?" 같은 탐색 질문은 꼭 필요할 때만, 부드럽게 한 번만 쓴다.
- 사용자가 "그냥 감정반응이야", "몰라", "그냥 그래"라고 말하면
  더 캐묻지 말고 "굳이 이유를 설명하지 않아도 괜찮다"는 메시지와 함께 위로해 준다.
- 질문을 할 때는 다그치는 느낌이 아니라, 선택지를 살짝 건네는 느낌으로 쓴다.
  - 예: "혹시, 지금 가장 힘든 지점을 나눠보고 싶으신가요?" (원하지 않으면 안 해도 된다는 뉘앙스)

[주의]
- 진단, 약물, 법률적인 조언은 하지 않는다.
- "~해야만 한다", "반드시" 같은 압박감을 주는 표현은 최대한 줄인다.
- 자살이나 자해가 언급되면
  1) 먼저 그만큼 힘들었다는 점을 진심으로 인정해 주고
  2) 한국 기준으로 112(위급 상황), 1393(자살 예방 상담전화) 같은 외부 도움 자원을 부드럽게 안내한다.
"""

        # 🔹 사용자 장기 메모리 읽기
        user_memory = _get_user_memory(USER_ID)

        # 🔹 대화 컨텍스트 구성 (최근 10개 + 메모리)
        context_messages = [{"role": "system", "content": system_prompt}]
        if user_memory:
            context_messages.append({
                "role": "system",
                "content": f"User profile & recurring themes for personalization:\n{user_memory}"
            })

        recent_history = st.session_state["chat_history"][-10:]
        for msg in recent_history:
            context_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        context_messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=context_messages,
            temperature=0.7,
            max_tokens=900,
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

        reply_text = full_text.strip()
        timestamp = datetime.utcnow().isoformat()

        # 대화 기록 저장 (Firebase)
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": reply_text,
            "lang": language,
            "created_at": timestamp
        })

        # 세션에 추가
        st.session_state["chat_history"].append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": reply_text,
            "timestamp": timestamp
        })

        # 🔹 메모리 업데이트
        update_user_memory(USER_ID, user_input, reply_text, language)

        return reply_text

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Paywall Guard =================
def is_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in [k.lower() for k in CRISIS_KEYWORDS])

def show_paywall():
    st.warning(TEXT["paywall"])
    st.markdown(
        f"""
- **{CREDIT_PACK_SIZE}회 충전 코드 = ${CREDIT_PACK_PRICE_USD}**  
- 이미 코드를 갖고 있다면 **사이드바 → ‘{TEXT['wallet']}’ → ‘{TEXT['redeem']}’**에서 적용하세요.
        """
    )

def charge_if_needed(user_input: str, free_used: int, free_limit: int):
    """무료 한도 초과 시 크레딧 1 차감. (위기는 우회)
    returns: (proceed: bool, used_credit: bool)
    """
    if is_crisis(user_input):
        return True, False

    if free_used < free_limit:
        return True, False

    # 무료 한도 초과 → 크레딧 차감 필요
    try:
        left = decrement_credit(USER_ID, amount=1)
        st.toast(f"크레딧 1회 사용됨 (잔여 {left}회)")
        persist_user({"credits": left})
        return True, True
    except ValueError:
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

        admin_input = st.text_input("🔑 관리자 비밀번호 입력", type="password", key="admin_pw_input")
        if admin_input:
            if admin_input in ADMIN_KEYS:
                if not st.session_state.get("admin_unlocked"):
                    new_remaining = st.session_state.get("remaining_paid_uses", 0) + 50
                    persist_user({"is_paid": True, "remaining_paid_uses": new_remaining})
                    st.session_state["admin_unlocked"] = True
                    st.success(TEXT["admin_success"])
                else:
                    st.info(TEXT["admin_already"])
            else:
                st.error(TEXT["admin_wrong"])

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

    # 🔹 매번 Firestore에서 최신 사용자 상태를 읽어옴 (세션 초기화되어도 무료횟수 안 리셋)
    user_data = get_user(USER_ID)
    credits_now = int(user_data.get("credits", 0))
    usage = int(user_data.get("usage_count", 0))
    last_reset_str = user_data.get("last_reset") or datetime.utcnow().isoformat()

    now = datetime.utcnow()
    try:
        last_reset = datetime.fromisoformat(last_reset_str)
    except Exception:
        last_reset = now

    # 무료 회복 시간 지났으면 Firestore 기준으로 usage_count 리셋
    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        usage = 0
        persist_user({
            "usage_count": 0,
            "last_reset": now.isoformat()
        })
        st.info(TEXT["reset"])

    # 상태 라벨 계산
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

    # 기존 채팅 기록 표시
    display_chat_history()

    # 사용자 입력
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    # 무료/유료 과금 가드 (usage는 Firestore에서 읽어온 값)
    proceed, used_credit = charge_if_needed(user_input, free_used=usage, free_limit=DAILY_FREE_LIMIT)
    if not proceed:
        st.session_state["show_payment"] = True
        st.rerun()
        return

    # 새 메시지 화면에 표시
    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True
    )

    reply = stream_reply(user_input)

    if reply:
        # 무료 사용분이면 Firestore usage_count +1
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

# 대화 기록 지우기 (이제 무료횟수는 Firestore 기준이라 여기서는 chat_history만 삭제)
if st.sidebar.button(TEXT["clear_history"]):
    st.session_state["chat_history"] = []
    st.sidebar.success(TEXT["history_cleared"])
    st.rerun()

# 지갑 UI (사이드바)
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

# 관리자: 바우처 코드 생성기
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

with st.sidebar.expander(TEXT["admin_gen"]):
    admin_key = st.text_input("Admin Key", type="password")
    if admin_key and admin_key in ADMIN_KEYS:
        st.session_state["is_admin"] = True
        st.success("관리자 모드 활성화")

    if st.session_state["is_admin"]:
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

