# ==========================================
# 💙 EOERWAY AI Therapy v2.9 — Wallet + Voucher + Paywall + Memory
# ==========================================
# 추가된 것:
# - Firestore에 사용자 감정/고민 요약 메모리 저장 (users/{uid}/memory/profile)
# - 매 대화마다 메모리를 업데이트해서 "감정 패턴 / 반복 고민 / 조심할 점" 축적
# - 다음 응답 생성 시 이 메모리를 system 메시지로 넣어 개인화

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
BASIC_LIMIT = 50              # (과거 호환용) 남아있는 유료 회수 개념
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
    "is_paid": False,                    # (이전 호환) 사용 안 함
    "usage_count": 0,                    # 무료 사용량(주기적 회복)
    "remaining_paid_uses": 0,            # (이전 호환) 사용 안 함
    "last_reset": datetime.utcnow().isoformat(),
    # 신규 지갑 필드
    "credits": 0,
    "purchased_packs": 0,
    "ad_free": False,
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

# ================= Long-term Memory (read-only) =================
def _get_user_memory(uid: str) -> str:
    """
    Firestore: users/{uid}/memory/profile 문서에서 text 필드 읽기.
    여기에는 '감정 패턴 / 반복 고민 / 말투 / 조심할 점' 등이 요약되어 있음.
    """
    doc = db.collection("users").document(uid).collection("memory").document("profile").get()
    if doc.exists:
        return (doc.to_dict() or {}).get("text", "")
    return ""

# ================= Long-term Memory (update) =================
def update_user_memory(uid: str, user_input: str, reply: str, language: str):
    """
    매 대화마다 사용자 감정/고민 요약을 업데이트.
    - 이전 요약 + 이번 대화 내용 기반으로 짧은 메모리 문자열 생성
    - users/{uid}/memory/profile 에 저장
    실패해도 메인 상담 흐름은 깨지지 않도록 예외는 조용히 무시.
    """
    try:
        mem_ref = db.collection("users").document(uid).collection("memory").document("profile")
        prev_doc = mem_ref.get()
        prev_text = ""
        if prev_doc.exists:
            prev_text = (prev_doc.to_dict() or {}).get("text", "")

        if language == "English 🇺🇸":
            system_prompt = """
You maintain a short, cumulative psychological + contextual profile for one specific user.
Goal: help an AI therapist remember the user's recurring worries, emotional patterns, and what has worked well.

Update the previous summary using the new conversation turn.
Be concise and structured. Do NOT mention token counts or models.
Write as if you're talking *about* the user, not *to* them.
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
2) Emotional patterns (e.g. anxiety, depression, burnout, frustration, hopelessness, mixed with humor, etc.)
3) User's typical thinking style or tone (e.g. self-critical, perfectionistic, joking, catastrophic thinking)
4) Helpful ways of responding (what the user seems to like or find comforting)
Keep it compact but specific.
"""
        else:
            system_prompt = """
당신은 한 명의 사용자를 위한 '장기 메모리 요약 AI'입니다.
목표: 이 사용자의 반복되는 고민, 감정 패턴, 말투, 도움이 되었던 상담 방식 등을 짧게 정리해
다음 상담 때 더 개인화된 공감을 할 수 있게 돕는 것입니다.

이전 요약 + 새로운 대화 내용을 합쳐서,
너무 길지 않게 핵심만 업데이트하세요.
"""
            user_prompt = f"""
[이전까지의 메모리 요약]
{prev_text}

[이번 대화의 사용자 메시지]
{user_input}

[이번 대화에서 AI의 응답(참고용)]
{reply}

[요청]
아래 항목을 포함해 5~9줄 정도로 한국어로 요약을 업데이트해주세요.

1) 자주 등장하는 고민/주제 (예: 돈·수입, 미래 불안, 무기력, 인간관계, 자존감 등)
2) 감정 패턴 (예: 불안, 우울, 분노, 허무감, 조급함, 자기비난, 유머 섞인 자조 등)
3) 사용자의 사고/말투 스타일 (예: 극단적 표현, '망했다' 식 표현, 장난섞인 표현, 완벽주의 등)
4) 상담 시 조심해야 할 부분 또는 이 사람에게 특히 잘 먹히는 위로/도움 방식
5) AI가 앞으로 기억하면 좋을 포인트 1~2개

사용자에게 직접 말하지 말고, 제3자가 이 사람을 설명하듯 적어주세요.
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
        # 메모리 업데이트 실패해도 상담은 계속 되도록
        print("memory update error:", e)

# ================= Wallet / Voucher Helpers =================
def ensure_user(uid: str):
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if not snap.exists:
        ref.set(defaults, merge=True)
    else:
        # 누락 필드가 있으면 보강
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
        "expires_at": None,  # 필요 시 Timestamp
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
            u = {"credits": 0, "purchased_packs": 0}
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
[대화 가이드 — 권장(강제 아님)]
- 상황과 맥락에 맞게 자연스럽게 대화하세요. 아래는 참고용 예시일 뿐, 반드시 따를 필요는 없습니다.
- 톤: 따뜻하고 인간적이며 존댓말 사용. 과장·훈계·가스라이팅·공허한 긍정은 피합니다.
- 길이: 3~6문장을 권장하되, 사용자의 호흡에 맞춰 더 짧거나 길어도 괜찮습니다.
- 제안은 선택지처럼 1가지만, “원하시면 시도해볼 수 있어요” 식으로 부드럽게.

[우선순위]
1) 안전: 자해·자살 언급 시 고통을 인정하고 즉각적인 안전을 우선합니다.
   - 예: “정말 많이 힘드셨겠어요. 지금 안전이 가장 중요해요.”
   - 한국: 생명이 위급하거나 즉시 도움이 필요하면 112 또는 가까운 응급실, 상담은 국번없이 1393을 안내합니다.
2) 공감 → 감정명명 → 정상화 → 작은 실천(선택) → 연결감 순으로 접근하되, 필요 시 일부만 사용해도 됩니다.

[열린 질문 예시]
- “요즘 무엇이 가장 버겁게 느껴지셨어요?”
- “지금 이 순간 몸은 어떤 신호를 보내고 있나요?”
- “조금이라도 나아지도록 제가 어떻게 도와드리면 좋을까요?”

[상황별 응답 샘플 (예시일 뿐)]
- 가벼운 인사: “와주셔서 고마워요. 요즘 마음이 어떠셨어요? 저는 당신 편에 있을게요.”
- 막막/불안: “끝이 안 보이는 느낌이 드셨군요. 그렇게 느끼는 게 정말 이해돼요. 원하시면 지금 딱 한 가지, 숨을 천천히 3번 고르는 것부터 같이 해볼까요?”
- 우울/무기력: “기운이 쏙 빠진 나날을 버티고 계시네요. 그만큼 애쓰고 계신 증거예요. 오늘을 버티게 한 작은 것 하나만 떠올려볼까요?”
- 분노/좌절: “화를 느끼는 건 당연해요. 그 감정이 알려주는 니즈가 뭘까요—경계, 휴식, 인정 중에 가까운 게 있을까요?”
- 자기비난: “스스로에게 너무 엄격하신 것 같아요. 같은 상황의 친구에게도 이렇게 말하실까요? 말투를 10%만 다정하게 바꿔보는 건 어떨까요?”
- 금전/진로 걱정: “불확실성이 큰만큼 마음이 조일 수 있어요. 당장 가능한 10분짜리 행동 하나만 정해볼까요? (예: 해야 할 것 1개만 적기)”
- 대화 마무리: “오늘 여기까지도 큰걸음이었어요. 필요하실 때 언제든 이어가요. 혼자가 아니세요.”

[하지 말 것]
- 진단·약물·법률 조언, 허위 확신, 과도한 해결책 나열, ‘~해야만 한다’식 훈계.
- 위치·개인정보를 불필요하게 요구하지 않기. 트리거가 될 수 있는 세부 묘사 자제.

[선택적 확장]
- 사용자가 ‘실행 계획’을 원하면 SMART하게 한 걸음만 제시(구체·작게·바로 가능).
- 이전 대화·사용자 메모리의 핵심을 1줄로 상기시켜 개인화를 돕되, 사생활 의도 추측은 피합니다.
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

        # 대화 기록 저장 (Firebase - 1회 쓰기만)
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

        # 🔹 메모리 업데이트 (감정 패턴 / 반복 고민 요약)
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
    st.warning(TEXT["paywall"])  # 언어별 문구
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

    # ✨ 결제 의사(좌) / 결제 안내 + PayPal(우)
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

        # 🌈 네온 무지개 결제버튼 CSS
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
    """채팅 기록 표시 (한 줄씩)"""
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
    # 상태 라벨 계산: 무료 잔여 또는 크레딧
    credits_now = int(st.session_state.get("credits", 0))
    usage = int(st.session_state.get("usage_count", 0))

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

    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))

    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({
            "usage_count": 0,
            "last_reset": now.isoformat()
        })
        st.info(TEXT["reset"])
        usage = 0

    # 기존 채팅 기록 표시
    display_chat_history()

    # 사용자 입력
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    # 무료/유료 과금 가드
    proceed, used_credit = charge_if_needed(user_input, free_used=usage, free_limit=DAILY_FREE_LIMIT)
    if not proceed:
        st.session_state["show_payment"] = True
        st.rerun()
        return

    # 새 메시지 표시
    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True
    )

    reply = stream_reply(user_input)

    if reply:
        # 무료 사용분이면 카운트만 +1, 크레딧 사용 시에는 이미 차감 완료
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

# 대화 기록 지우기 버튼 (세션만 초기화 — 기존 유지)
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
    code_input = st.text_input(" ", placeholder=TEXT["wallet_help"])  # 라벨 숨김용
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
    st.session_state.is_admin = False

with st.sidebar.expander(TEXT["admin_gen"]):
    admin_key = st.text_input("Admin Key", type="password")
    if admin_key and admin_key in ADMIN_KEYS:
        st.session_state.is_admin = True
        st.success("관리자 모드 활성화")

    if st.session_state.is_admin:
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
