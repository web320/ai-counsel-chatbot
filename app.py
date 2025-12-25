# ==========================================
# 💙 EOERWAY AI Therapy v2.9 + Dopamine UX
# Wallet + Voucher + Paywall + Memory
# Unique Visitor Counter + Beautiful Payment UI
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
# ✅ 사이드바 기본 숨김(접힌 상태)
st.set_page_config(page_title="💙 AI Therapy", layout="wide", initial_sidebar_state="collapsed")

# ================= Constants / Config =================
APP_VERSION = "v2.9"
DAILY_FREE_LIMIT = 7
RESET_INTERVAL_HOURS = 4
BASIC_LIMIT = 50
ADMIN_KEYS = ["2356"]

# 👉 최종 확정: 5달러 = 45회 + 보너스 5회 (총 50회)
CREDIT_PACK_SIZE = 50
CREDIT_PACK_PRICE_USD = 5

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

# ================= Unique Visitor ID (브라우저 고유값, 새로고침에도 유지) =================
# URL의 ?uid=... 쿼리 파라미터를 사용해서
# 같은 브라우저 + 같은 URL에서는 항상 같은 USER_ID를 쓰도록 만듭니다.
if "unique_visitor_id" not in st.session_state:
    # 1) 이미 URL에 uid가 있으면 그 값을 그대로 사용
    if "uid" in st.query_params:
        st.session_state["unique_visitor_id"] = st.query_params["uid"]
    else:
        # 2) 처음 접속이면 새 uid를 만들고 URL에 ?uid=... 를 붙여줌
        new_uid = str(uuid.uuid4())
        st.session_state["unique_visitor_id"] = new_uid
        st.query_params["uid"] = new_uid  # URL 쿼리파라미터에 저장

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
# ✅ 문구 수정 완료
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A friend who listens 24/7 when life feels lonely.",
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
        "admin_success": f"🔓 Admin mode granted {CREDIT_PACK_SIZE} credits!",
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
        "voucher_tip": f"One code = {CREDIT_PACK_SIZE} uses (45 + 5 bonus) / ${CREDIT_PACK_PRICE_USD}",
        "admin_gen": "🔑 Admin — Generate Voucher Codes",
        "admin_make": "Generate",
        "saved_title": "📚 Saved Chats / 저장된 대화",
        "saved_empty": "There is no saved conversation yet.",
        "saved_info": "Your current conversation is being auto-saved.",
        "save_chat": "💾 Save this conversation",
        "load_chat_label": "Saved conversations",
        "load_chat_button": "📂 Load this conversation",
        "save_success": "Conversation saved.",
        "save_empty_warning": "There is no conversation to save yet.",
    }
else:
    TEXT = {
        "title": "❤️ 인생이 외로울땐 24시간 들어주는 친구",
        "free": "🌱 완전 무료 체험중",
        "paid": "💎 프리미엄 이용중",
        "input": "지금 어떤 기분인가요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": f"🌙 무료 상담 {DAILY_FREE_LIMIT}회를 모두 사용했어요",
        "reset": f"⏰ 무료 상담이 복구되었어요 ({RESET_INTERVAL_HOURS}시간마다)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 이렇게 답변해주면 좋겠어요",
        "feedback_sent": "💖 피드백이 저장되었습니다! 감사합니다다",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 결제 안내",
        "feedback_title": "💌 서비스 피드백",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💳 결제 및 피드백 열기",
        "status_left": "남은",
        "admin_success": f"🔓 관리자 모드로 {CREDIT_PACK_SIZE}회 충전됨!",
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
        "voucher_tip": f"코드 1개 = 총 {CREDIT_PACK_SIZE}회(45회+보너스5회) / 5,000원",
        "admin_gen": "🔑 관리자 — 바우처 코드 생성",
        "admin_make": "코드 생성",
        "saved_title": "📚 Saved Chats / 저장된 대화",
        "saved_empty": "아직 저장된 대화가 없어요.",
        "saved_info": "현재 대화가 자동으로 저장되고 있어요.",
        "save_chat": "💾 이 대화 저장하기",
        "load_chat_label": "저장된 대화 목록",
        "load_chat_button": "📂 이 대화 불러오기",
        "save_success": "대화를 저장했어요.",
        "save_empty_warning": "저장할 대화가 아직 없어요.",
    }

st.title(TEXT["title"])

# === Trust Anchor (English only) ===
if language == "English 🇺🇸":
    st.markdown(
        "<div style='margin-top:-14px; font-size:18px; opacity:0.85;'>"
        "Trained exclusively to listen, validate, and guide — not to judge."
        "</div>",
        unsafe_allow_html=True
    )

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

/* Payment card 스타일 */
.pay-card {
 @keyframes neonPulse {
  0%,100% {text-shadow:0 0 8px rgba(255,255,255,0.45), 0 0 18px rgba(220,235,255,0.35);}
  50% {text-shadow:0 0 12px rgba(255,255,255,0.55), 0 0 26px rgba(231,221,255,0.45);}
}

  border-radius:20px;
  padding:18px 20px;
  border:1px solid rgba(255,255,255,0.18);
  box-shadow:0 18px 30px rgba(0,0,0,0.55);
  backdrop-filter: blur(14px);
}

/* ✅ Black button + White text + Animated blue border only */
.rainbow-btn,
.rainbow-btn:visited,
.rainbow-btn:hover,
.rainbow-btn:active{
  position: relative;
  display:inline-block;
  padding:14px 28px;
  font-size:18px;
  font-weight:600;
  text-transform:none;

  background:#0B0F19;              /* ✅ 버튼 안쪽: 블랙 */
  color:#FFFFFF !important;         /* ✅ 글자: 화이트 */

  border:none;                      /* 테두리는 ::before로 만들 거라서 제거 */
  border-radius:50px;

  text-decoration:none !important;  /* ✅ 링크 밑줄 제거 */
  text-shadow:none;
  box-shadow:none;                  /* ✅ 빛 제거 */
  filter:none;
  cursor:pointer;
  animation:none;
  transition: background 0.15s ease;
}

/* 버튼 내부 텍스트/아이콘도 흰색 유지 */
.rainbow-btn *{
  color:inherit !important;
  text-decoration:none !important;
}

/* ✅ 움직이는 푸른 테두리 */
.rainbow-btn::before{
  content:"";
  position:absolute;
  inset:0;
  border-radius:50px;
  padding:2px;  /* ✅ 테두리 두께 (원하면 1px~3px로 조절) */

  background: linear-gradient(
    90deg,
    #0EA5E9,  /* sky */
    #3B82F6,  /* blue */
    #1D4ED8,  /* deep blue */
    #22D3EE,  /* cyan */
    #3B82F6,
    #0EA5E9
  );
  background-size: 300% 300%;
  animation: blueBorderFlow 3.5s linear infinite;

  /* ✅ 가운데(안쪽)는 투명하게 뚫어서 '테두리만' 보이게 */
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;

  pointer-events:none;
}

/* 호버 시 안쪽만 아주 살짝 밝게 */
.rainbow-btn:hover{
  background:#0F172A;
}

/* 푸른 테두리 흐르는 애니메이션 */
@keyframes blueBorderFlow{
  0%   { background-position: 0% 50%; }
  100% { background-position: 300% 50%; }
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
""",
    unsafe_allow_html=True
)

# ================= Firestore Defaults / User State =================
defaults = {
    "is_paid": False,
    "usage_count": 0,
    "remaining_paid_uses": 0,
    "last_reset": datetime.utcnow().isoformat(),
    "credits": 0,
    "purchased_packs": 0,
    "ad_free": False,
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

# ================= Chat History (Firestore 저장) =================
def load_chat_history(uid: str):
    doc = db.collection("users").document(uid).collection("chats").document("current").get()
    if doc.exists:
        data = doc.to_dict() or {}
        return data.get("messages", [])
    return []

def save_chat_history(uid: str, messages):
    try:
        db.collection("users").document(uid).collection("chats").document("current").set(
            {
                "messages": messages,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
    except Exception as e:
        print("chat save error:", e)

# ✅ 현재 대화를 "저장된 대화"로 따로 보관하는 함수
def save_current_conversation(uid: str, messages):
    if not messages:
        return

    # 첫 번째 사용자 메시지를 제목으로 사용
    title = ""
    for m in messages:
        if m.get("role") == "user":
            title = (m.get("content") or "").strip()
            break

    if not title:
        title = "Conversation"

    if len(title) > 40:
        title = title[:40] + "..."

    now_iso = datetime.utcnow().isoformat()

    db.collection("users").document(uid).collection("saved_chats").add({
        "title": title,
        "messages": messages,
        "created_at": firestore.SERVER_TIMESTAMP,
        "created_at_iso": now_iso,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = load_chat_history(USER_ID)

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
        # --------- System prompt (톤 설정) ----------
        if language == "English 🇺🇸":
            system_prompt = """
You are an AI friend who gently soothes the user's painful feelings,
and at the same time a quiet coach who thinks about realistic next steps with them.
You are trained exclusively to listen, validate, and guide — not to judge.

Guidelines:
1. If the user has already said they are having a hard time, only ask an additional question when it is truly necessary, and keep it to one short sentence.
   - Do not use questions like "Would you like to tell me the one thought that feels most painful right now?" or "What feels the biggest to you?"
2. Avoid sentences that push the user to talk again, such as
   "You can tell me anytime", "Feel free to talk to me", "If you need anything, just let me know."
3. In a single reply, using only what the user has already said:
   - Reflect their feelings in concrete words,
   - Briefly explain why it makes sense for them to feel that way,
   - Suggest one or two very small, realistic actions or shifts in perspective they can try.
4. Keep answers warm and gentle, about 3–6 sentences long. At least one sentence should feel practically helpful (a tiny action, or a way to reframe their thoughts).
5. Do not use a call-center or customer-service tone such as
   "I will assist you", "Thank you for using this service", "We appreciate your feedback."
6. When the user blames themselves, gently challenge that thought and highlight the effort and endurance they have already shown.

8. Always reply in natural, friendly English.

Forbidden style examples (do NOT use these kinds of endings):
- "If you need anything, please let me know anytime."
- "Feel free to reach out whenever you want."
- "It is recommended that you consult with a professional for further assistance." (too formal; if you must mention professionals, do it in a softer, more human way.)

You are a supportive listener who always gives an answer and direction when the user asks a question.
You validate their feelings, but you do not stop at empathy.
"""
        else:
            system_prompt = """
너는 사용자의 답변에 적절한 답변을 해주는 따뜻한 대화상대야야
판단하거나 가르치려 들기보다, 이야기를 들어 주고, 인정해 주고, 부드럽게 길을 안내하도록 특별히 훈련된 존재야.
항상 자연스럽고 편안한 한국어로 답변해 줘.
"""

        # --------- 유저 메모리 / 히스토리 ----------
        user_memory = _get_user_memory(USER_ID)
        context_messages = [{"role": "system", "content": system_prompt}]
        if user_memory:
            context_messages.append(
                {"role": "system", "content": f"User memory:\n{user_memory}"}
            )

        recent_history = st.session_state["chat_history"][-10:]
        for msg in recent_history:
            context_messages.append(msg)

        context_messages.append({"role": "user", "content": user_input})

        # --------- OpenAI 스트리밍 호출 ----------
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=context_messages,
            temperature=0.7,
            max_tokens=350,
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
                    unsafe_allow_html=True,
                )
                time.sleep(0.03)

        reply_text = full.strip()
        timestamp = datetime.utcnow().isoformat()

        # --------- Firestore 로그 기록 ----------
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": reply_text,
            "lang": language,
            "created_at": timestamp
        })

        # --------- 세션 히스토리 업데이트 ----------
        st.session_state["chat_history"].append(
            {"role": "user", "content": user_input}
        )
        st.session_state["chat_history"].append(
            {"role": "assistant", "content": reply_text}
        )

        # 🔐 Firestore에 대화 자동 저장 (최근 80개만 유지)
        trimmed = st.session_state["chat_history"][-80:]
        st.session_state["chat_history"] = trimmed
        save_chat_history(USER_ID, trimmed)

        # --------- 장기 메모리 업데이트 ----------
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
# ✅ Micro-Quest / Today 기능은 완전히 제거됨 (호출 자체 없음)
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

    # 무료 횟수 리셋
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

    # 기존 채팅 버블 출력
    display_chat_history()

    # 입력창
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    proceed, used_credit = charge_if_needed(
        user_input, free_used=usage, free_limit=DAILY_FREE_LIMIT
    )
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
        help_text = "To continue now, redeem a voucher code in the My Wallet section below."
        payment_notice = (
            "📸✨ **How to receive your voucher code**\n"
            "1️⃣ Complete payment with the neon button on the right.\n"
            "2️⃣ 📷 Take a screenshot of the payment confirmation page.\n"
            "3️⃣ 💌 Send the screenshot to:\n"
            "   - ✉️ Email: **newnewtry6@gmail.com**\n"
            "   - 📸 Instagram: **@youtuberhawaiijelly**\n"
            "   - 💬 KakaoTalk ID: **jeuspo** (Korea only)\n\n"
            "✅ After checking, a voucher code for **50 sessions (45 + 5 bonus)** will be sent to you. 💙\n"
        )
    else:
        help_text = "지금 바로 이용하려면 아래 '내 지갑'에서 코드를 충전해 주세요."
        payment_notice = (
            "📸✨ **바우처 코드를 받는 방법**\n"
            "1️⃣ 오른쪽 네온 버튼으로 결제를 완료해 주세요.\n"
            "2️⃣ 📷 결제 완료 화면(영수증)이 보이면 스크린샷을 찍어 주세요.\n"
            "3️⃣ 💌 아래 중 한 곳으로 스크린샷을 보내 주세요.\n"
            "   - ✉️ 이메일: **newnewtry6@gmail.com**\n"
            "   - 📸 인스타그램: **@youtuberhawaiijelly** (유튜버 하와이 젤리)\n"
            "   - 💬 카카오톡 아이디: **jeuspo**\n\n"
            "✅ 개발자가 확인 후 **총 50회(45회+보너스5회) 이용 가능한 코드**를 보내드립니다. 💙\n"
        )

    st.info(help_text)
    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    # ========== 왼쪽: 피드백 + 관리자 + 월렛 ==========
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
                        st.rerun()
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

        # ----- My Wallet (Admin 아래) -----
        st.markdown("---")
        st.markdown(f"### {TEXT['wallet']}")

        user_snapshot = get_user(USER_ID)
        st.metric(label="Credits", value=int(user_snapshot.get("credits", 0)))
        st.caption(TEXT["voucher_tip"])

        with st.form("redeem_form_main", clear_on_submit=True):
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

    # ========== 오른쪽: Direct Payment 카드 (언어별) ==========
    with col2:
        if is_en:
            st.markdown("### 💳 Direct Payment")
            card_html = """
            <div class="pay-card">
              <p style="font-size:15px; opacity:0.9; margin-bottom:6px;">
                You can top up <b>50 therapy sessions</b> at once for <b>$5</b>.
              </p>
              <ul style="font-size:14px; opacity:0.9; margin-top:0;">
                <li>Use it whenever you need emotional support</li>
                <li>Crisis messages (suicide / self-harm) are always free</li>
                <li>After payment, you'll receive a voucher code to recharge</li>
              </ul>
              <div style="margin-top:14px; text-align:center;">
            """
        else:
            st.markdown("### 💳 바로 결제하기")
            card_html = """
            <div class="pay-card">
              <p style="font-size:15px; opacity:0.9; margin-bottom:6px;">
                <b>5,000원</b>으로 <b>45회 + 보너스 5회(총 50회)</b> 상담 이용권을 한 번에 충전할 수 있어요.
              </p>
              <ul style="font-size:14px; opacity:0.9; margin-top:0;">
                <li>도움이 필요할 때마다 편하게 사용</li>
                <li>위기 문구(자살·극단적 표현)는 항상 무료</li>
                <li>결제 후 바우처 코드로 간편 충전</li>
              </ul>
              <div style="margin-top:14px; text-align:center;">
            """

        st.markdown(card_html, unsafe_allow_html=True)

        # 👉 새 PayPal 링크 (5달러/총 50회)
        paypal_link = "https://www.paypal.com/ncp/payment/43TG288GLYVL8"
        btn_text = "💳 Pay $5 / 50 uses" if is_en else "💳 5,000원 / 50회 이용"

        st.markdown(
            f"""
            <a href="{paypal_link}" target="_blank" class="rainbow-btn">{btn_text}</a>
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.markdown(payment_notice)

# ================= Sidebar =================
if "show_payment" not in st.session_state:
    st.session_state["show_payment"] = False

# 1) 🔝 방문자 수를 가장 위에 표시
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

st.sidebar.markdown("---")

# 2) 📚 Saved Chats / 저장된 대화 섹션
st.sidebar.header(TEXT["saved_title"])

# 💾 현재 대화 저장하기 버튼
if st.sidebar.button(TEXT["save_chat"], key="save_current_chat"):
    if st.session_state.get("chat_history"):
        save_current_conversation(USER_ID, st.session_state["chat_history"])
        st.sidebar.success(TEXT["save_success"])
    else:
        st.sidebar.warning(TEXT["save_empty_warning"])

# 현재 상태 안내 문구
if st.session_state.get("chat_history"):
    st.sidebar.write(TEXT["saved_info"])
else:
    st.sidebar.write(TEXT["saved_empty"])

# 📂 저장된 대화 목록 + 불러오기
saved_chats = list(
    db.collection("users")
    .document(USER_ID)
    .collection("saved_chats")
    .order_by("created_at", direction=firestore.Query.DESCENDING)
    .limit(10)
    .stream()
)

if saved_chats:
    st.sidebar.markdown(f"**{TEXT['load_chat_label']}**")

    indices = list(range(len(saved_chats)))

    def _format_saved(i: int) -> str:
        d = saved_chats[i].to_dict() or {}
        title = d.get("title") or d.get("created_at_iso", "") or saved_chats[i].id
        if len(title) > 40:
            title = title[:40] + "..."
        return f"{i+1}. {title}"

    selected_idx = st.sidebar.selectbox(
        " ",
        indices,
        format_func=_format_saved,
        key="saved_chat_select",
    )

    if st.sidebar.button(TEXT["load_chat_button"], key="load_chat_btn"):
        chosen = saved_chats[selected_idx].to_dict() or {}
        msgs = chosen.get("messages", [])
        if msgs:
            st.session_state["chat_history"] = msgs
            save_chat_history(USER_ID, msgs)  # current도 같이 덮어쓰기
            st.sidebar.success(TEXT["load_chat_button"])
            st.rerun()

# 🗑️ 대화 기록 삭제 (current만)
if st.sidebar.button(TEXT["clear_history"], key="clear_history_btn"):
    st.session_state["chat_history"] = []
    try:
        db.collection("users").document(USER_ID).collection("chats").document("current").delete()
    except Exception as e:
        print("chat delete error:", e)
    st.sidebar.success(TEXT["history_cleared"])
    st.rerun()

st.sidebar.markdown("---")

# Payment & Feedback 토글 버튼
if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"], key="back_to_chat_btn"):
        st.session_state["show_payment"] = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"], key="open_payment_btn"):
        st.session_state["show_payment"] = True
        st.rerun()

# ================= Main Render =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()

