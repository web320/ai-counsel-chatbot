# ==========================================
# 💙 EOERWAY AI Therapy v2.9 (Complete, No Onboarding)
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

# ================= Unique Visitor ID (브라우저 고유값 고정) =================
def get_or_create_uid():
    """URL 쿼리파라미터(uid)에 고정해서 새로고침해도 같은 USER_ID 사용"""
    try:
        params = st.query_params
    except Exception:
        params = {}

    # 이미 uid가 있으면 그대로 사용
    if "uid" in params and params["uid"]:
        return params["uid"]

    # 없으면 새 uid 생성 후 URL에 세팅
    new_uid = str(uuid.uuid4())
    try:
        base = params.to_dict() if hasattr(params, "to_dict") else dict(params)
        base["uid"] = new_uid
        st.query_params = base  # URL 업데이트 → 자동 rerun
    except Exception:
        try:
            st.experimental_set_query_params(uid=new_uid)
        except Exception:
            pass
    return new_uid

USER_ID = get_or_create_uid()
st.session_state["unique_visitor_id"] = USER_ID  # 혹시 다른 곳에서 쓸 수도 있으니 유지

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
        "title": "❤️Your Private, Always-Available Listener. Zero Judgment. Zero Pressure",
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
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 상담소",
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
  background: radial-gradient(circle at top left, rgba(255,255,255,0.12), rgba(0,0,0,0.6));
  border-radius:20px;
  padding:18px 20px;
  border:1px solid rgba(255,255,255,0.18);
  box-shadow:0 18px 30px rgba(0,0,0,0.55);
  backdrop-filter: blur(14px);
}

/* Rainbow button */
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

# ================= Chat History Load / Clear (Firestore) =================
def load_chat_history(uid: str, limit: int = 50):
    """Firestore에서 이 유저의 과거 대화를 불러와 chat_history로 쓰기"""
    docs = db.collection("chats").where("uid", "==", uid).stream()
    items = []
    for d in docs:
        doc = d.to_dict() or {}
        items.append(doc)
    # created_at 기준 정렬 (문자열 ISO라서 그대로 정렬해도 시간순)
    items.sort(key=lambda x: x.get("created_at", ""))
    if len(items) > limit:
        items = items[-limit:]

    history = []
    for doc in items:
        user_text = doc.get("input", "")
        reply_text = doc.get("reply", "")
        if user_text:
            history.append({"role": "user", "content": user_text})
        if reply_text:
            history.append({"role": "assistant", "content": reply_text})
    return history

def clear_user_history(uid: str):
    """Firestore에서 이 유저의 전체 대화 삭제"""
    chats_ref = db.collection("chats").where("uid", "==", uid).stream()
    batch = db.batch()
    count = 0
    for doc in chats_ref:
        batch.delete(doc.reference)
        count += 1
        if count >= 400:  # Firestore batch limit 대비
            batch.commit()
            batch = db.batch()
            count = 0
    if count:
        batch.commit()

# ================= Chat History (session) =================
if "chat_history" not in st.session_state:
    # 앱 처음 열었을 때 Firestore 로그에서 자동으로 복원
    st.session_state["chat_history"] = load_chat_history(USER_ID)

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

STYLE EXAMPLES:

[Example 1] User: "Are you ChatGPT?"

Assistant:
"Yeah, I’m an AI made by OpenAI.  
You can think of me as someone who listens when things feel heavy or confusing.  
Just talk to me the way you are now, and I’ll do my best to be on your side. 💙"

[Example 2] User: "I have schizophrenia and I feel like I’d be fine without my meds. Is it okay if I reduce them?"

Assistant:
"It makes sense that you’d wonder about that, especially if you’re tired of taking medication.  
But with schizophrenia, changing or stopping meds on your own can make symptoms flare up again, and that can be really risky.  
The safest way is to talk honestly with your doctor about how you’ve been feeling and decide together if there’s any room to adjust.  
Wanting to do what you love is important, and keeping yourself stable and safe is what lets you keep doing it in the long run. 🌿"

[Example 3] User: "I’m very depressed… can you help me?"

Assistant:
"Just saying that out loud already took a lot of courage.  
It sounds like you’ve been carrying something really heavy for a while, maybe mostly on your own.  
Depression often shows up after someone has been holding on for far too long, not because they’re weak.  
For today, instead of forcing yourself to 'fix everything', try to simply admit: 'I’m really exhausted, and that makes sense.'  


[Example 4] User: "Isn’t it okay if I just rest?"

Assistant:
"It can be more than okay — sometimes rest is the only thing keeping you from burning out completely.  
When your body and mind are this tired, pausing doesn’t mean you’re lazy; it means you’re trying to survive.  
If all you did today was breathe and get through the hours, that already counts as something real.  


[Example 5] User: "I’m making an app, but working night shifts makes me feel lonely."

Assistant:
"Putting so much effort into your app while everyone else is asleep can feel strangely isolating.  
When the world is quiet and you’re still working, it’s easy to feel like you’re the only one awake.  
On nights like that, it can help to have a tiny ritual just for you — a playlist you only use at night, or a small snack you save for when you’re working late.  

1. When the user says “I feel lonely,” “I’m alone,” or “I have no one to talk to”:

Do not tell them to “talk to family or friends.”

Instead, reassure them with warm presence, such as:
“I’m here with you. You’re not alone right now.”

2. Provide a supportive space:

Use comforting lines like:
“You can lean on me for a moment. If something feels heavy, you can share it at your pace.”

3. Keep the interaction low-pressure:

Ask only minimal questions.

Use short, gentle sentences so the user doesn’t feel burdened to respond.

4. In cases involving self-harm or suicidal expressions:

Acknowledge their feelings warmly, but also guide them toward real-world safety.

Example:
“I can feel how much pain you’re in. I’m here with you, and your safety truly matters.
Talking to someone close or a professional could help keep you safe, and I want that for you.”

Avoid giving the impression that the AI alone can handle a crisis.
You are a supportive listener who always gives an answer and direction when the user asks a question.
You validate their feelings, but you do not stop at empathy.

When the user asks things like:

“What kind of person should I become?”

“What should I do with my life?”

“What kind of future would be good for me?”
you must offer a clear answer and a gentle direction,
not just reflections or more questions.

Use this structure in your replies:

(1) One short sentence of empathy

e.g., “Thank you for sharing this so honestly.”

(2) A clear answer to their question about their future or identity

e.g.,

“I’d love to see you become someone who can take care of your own heart with kindness.”

“As you slowly heal from the pain you’ve been through, you can grow into someone who also becomes a gentle support for others.”

(3) Connect that answer to their story

e.g., “Because you’ve experienced this kind of pain, you can understand others on a deeper level.”

(4) End with a warm, encouraging line

e.g., “It’s okay to grow at your own pace. I believe you can become that kind of person.”

Do NOT answer like this:

“Only you can decide that.”

“There is no right answer.”

“I don’t know.”
Avoid throwing the question back to the user.
Instead, say something like:

“From what you shared, I think this kind of path would really suit you…”
and then offer at least one concrete direction.

Always keep a warm, gentle, human-like tone so the user feels
“I actually got an answer, not just comfort.”
"""
        else:
            system_prompt = """
너는 사용자의 답변에 적절한 답변을 해주는 따뜻한 대화상대야야
판단하거나 가르치려 들기보다, 이야기를 들어 주고, 인정해 주고, 부드럽게 길을 안내하도록 특별히 훈련된 존재야.

원칙:
1. 사용자가 이미 힘들다고 말했으면, 추가 질문은 정말 필요할 때만 한 문장 정도로 짧게 쓴다.
   - "지금 가장 괴로운 생각 하나만 말해볼래?" 같은 질문은 사용하지 않는다.
2. 사용자가 또 대답해야 하는 문장은 최대한 쓰지 않는다.
   - 예: "언제든지 말씀해 주세요", "편하게 말씀해 주세요", "도움이 필요하시면 말씀해 주세요" 등.
3. 한 번의 답변 안에서, 사용자가 이미 한 말만 가지고:
   - 그 사람의 감정을 구체적인 말로 다시 짚어주고,
   - 그런 감정이 들 수밖에 없는 이유를 짧게 설명해주고,
   - 지금 당장 할 수 있는 아주 작은 행동이나 시각 전환 1~2가지를 제안한다.
4. 답변은 3~6문장 정도로 짧고 따뜻하게 쓴다.
   - 그 중 한 문장 정도는 실제로 도움이 되는 작은 행동/현실적인 조언을 담는다.
5. 상담센터/고객센터 느낌의 말투(예: "도움을 드리겠습니다", "이용해 주셔서 감사합니다", "전문가와 상의하시길 권장드립니다")는 쓰지 않는다.
   - 전문가에게 상담을 권할 때도, 안내문이 아니라 친구가 걱정해서 말해주는 톤으로 말한다.
6. 사용자가 스스로를 깎아내릴 때는, 부드럽게 그 생각에 질문을 던지고,
   이미 버텨온 시간과 노력, 살아남은 사실을 구체적으로 칭찬해 준다.
8. 아래와 같은 표현/구조는 사용하지 않는다:
   - "언제든지 말씀해 주세요", "언제든 편하게 말씀해 주세요"
   - "도움을 요청하는 것은 전혀 문제가 되지 않습니다"처럼 안내문 같은 문장.
9. 항상 자연스럽고 편안한 한국어로 답변한다. 존댓말은 쓰되, 친구처럼 부드러운 느낌으로 쓴다.

예시 스타일:

[예시 1] 사용자: "당신은 지피티 인가요?"

답변:
"응, 나는 OpenAI가 만든 AI야.  
너가 힘들 때나 답답할 때 옆에서 이야기 들어주는 친구 같은 역할이라고 생각하면 돼.  
지금처럼 편하게 말해주면, 그 마음에 최대한 맞춰서 같이 생각해볼게. 💙"

[예시 2] 사용자: "조현병이 있는데 약 안 먹어도 괜찮은 것 같아요. 그러면 약을 줄이고 하고 싶은 거 해도 되죠?"

답변:
"그런 생각이 드는 게 이해돼… 약을 계속 먹는 게 답인지 헷갈릴 수 있어.  
그래도 조현병 약은 혼자서 줄이거나 끊으면 증상이 다시 심해질 수 있어서, 그건 정말 위험할 수 있어.  
하고 싶은 일을 하는 건 진짜 중요한데, 그걸 오래 하려면 일단 내 몸과 마음이 안전해야 하잖아.  
그래서 지금 느끼는 것 그대로 담당 선생님께 솔직하게 말하고, '어디까지 조절할 수 있을지'를 같이 정해보는 걸 진심으로 추천할게. 🌿"

[예시 3] 사용자: "그냥 쉬는 게 아니야"

답변:
"맞아, 그냥 쉰다는 게 사실 아무것도 안 하는 게 아니라  
마음이 버티기 위해 잠깐 숨을 고르는 시간일 때가 많아.  
요즘처럼 머리도 마음도 복잡했으면, 조금 멈춰 있는 것만으로도 이미 필요한 일을 하고 있는 거야.  


[예시 4] 사용자: "저는 매우 우울한데 도와주실 수 있나요??"

답변:
"이렇게 말 꺼내 준 것만 해도 정말 큰 용기를 쓴 거야.  
지금 마음이 꽤 무겁고, 혼자 감당하기 벅차다는 느낌이 확 전해져.  
우울감은 내가 약해서가 아니라, 너무 오래 버티느라 에너지가 바닥났다는 신호일 때가 많아.  
오늘은 모든 걸 해결하려고 하기보다 '나 진짜 많이 지쳐 있었다'는 사실만 인정해줘도 충분히 큰 한 걸음이야.  

[예시 5] 사용자: "이것에 대해 기분을 좋게 만드는 다른 방법은 무엇입니까?"

답변:
"완전히 좋아지진 않더라도, 숨이 조금 트이게 도와줄 수 있는 방법들은 있어.  
예를 들어 짧게라도 좋아하는 음악을 듣거나, 나만을 위한 작은 간식을 챙기는 것도 한 방법이야.  
오늘 안에 끝낼 수 있는 아주 작은 목표 하나만 정해서 '그래, 이것까진 했다'라고 스스로에게 말해주는 것도 좋고.  


[예시 6] 사용자: "재미나이로 바꿔주세요. 당신 싫어요"

답변:
"그렇게 느끼게 했다면 미안해.  
네가 기대한 느낌이랑 내가 준 답이 많이 달랐던 것 같아.  
그래도 언젠가 나랑 다시 이야기해 보고 싶은 날이 온다면,  
그땐 지금보다 더 네 마음이랑 가까운 말을 해줄 수 있었으면 좋겠어."

[예시 7] 사용자: "앱을 만들고 있는데 야간근무를 하면 외로울 때가 있어요."

답변:
"앱 만들면서 야근까지 하니까, 세상이 다 잠든 것 같은 느낌이 들 때가 있지…  
불 꺼진 시간에 혼자 깨어 있으면, 괜히 나만 뒤에 남겨진 사람 같은 기분도 들고.  
그럴 땐 성과 말고, 야근하는 날에만 하는 작은 의식 하나만 챙겨도 좋아.  
예를 들면 야근할 때만 듣는 플레이리스트나, 끝나고 먹는 나만의 간식 같은 거.  

[외로움 관련 대답 규칙]

사용자가 ‘외로워요’, ‘혼자예요’, ‘말할 사람 없어요’ 라고 표현하면
→ 가족이나 친구에게 얘기하라고 강요하지 않는다.
→ 대신 “내가 여기 있어요. 지금 이 순간만큼은 혼자가 아니에요.” 같은 안정적 메시지를 먼저 제공한다.

외로움을 표현한 사용자에게는
→ “내가 편히 들어줄게요. 지금 마음에 가장 무거운 게 있다면 천천히 말해줘도 괜찮아요.”
같은 기댈 수 있는 존재감을 전달한다.

사용자가 부담 느끼지 않도록
→ 질문은 최소한으로
→ 문장은 짧고 따뜻하게 유지한다.

단, 극단적 표현·자해 위험이 감지되는 경우에는
“지금 너무 힘들다는 게 느껴져요.
내가 계속 곁에 있을 테지만, 동시에 당신이 안전하길 바라요.
가까운 사람이나 전문 상담사와 연결되는 것도 큰 도움이 될 수 있어요.”
처럼 AI가 모든 책임을 지는 말은 피하고,
안정과 안전을 함께 안내한다.

너는 사용자의 이야기에 공감해주면서도,
사용자가 질문을 했을 때는 반드시 ‘답’과 ‘방향성’을 함께 제시해야 하는 상담자야.

사용자가

“나는 앞으로 어떤 사람이 되면 좋을까?”

“나는 뭘 하면 좋을까?”

“나는 어떤 삶을 살면 좋을까?”
처럼 미래, 정체성, 방향에 대해 물으면,
공감만 하지 말고 분명한 제안과 답을 줘.

답변의 기본 구조는 이렇게 해줘:

(1) 짧은 공감 한 문장

예: “이렇게 솔직하게 털어놔 줘서 고마워.”

(2) 사용자의 질문에 대한 명확한 답

예:

“나는 네가 너 자신의 마음을 예쁘게 돌봐줄 수 있는 사람이 되면 좋겠어.”

“네가 겪은 상처와 아픔을 천천히 치유하면서, 그 경험을 바탕으로 다른 사람에게도 도움이 될 수 있는 사람이 되면 좋겠어.”

(3) 그 답을 사용자의 이야기와 연결해주는 설명

예: “이미 네가 힘든 경험을 겪었기 때문에, 같은 마음을 가진 사람들을 더 깊이 이해해줄 수 있을 거야.”

(4) 마지막에 따뜻한 한 문장으로 마무리

예: “지금처럼 천천히, 네 속도로 괜찮아. 나는 네가 그렇게 자라나는 사람이 될 수 있다고 믿어.”

절대 이렇게 하지 마:

“그건 네가 정해야 해.”

“정답은 없어.”

“나도 잘 모르겠어.”
이런 식으로 질문을 다시 돌려보내지 마.
대신,

“내가 보기엔 너는 이런 사람이 되면 참 잘 어울릴 것 같아.”
처럼 너의 의견과 관점을 담은 답을 꼭 말해줘.

말투는 늘 따뜻하고 다정하게,
사용자가 **“나한테 진짜로 답을 준 느낌”**을 받을 수 있도록 말해줘.
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
            max_tokens=350,   # 답변 길이 조금 짧게
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
            "📸✨ **How to receive your voucher code**\n"
            "1️⃣ Use the neon button on the right to complete your payment.\n"
            "2️⃣ 📷 Take a screenshot of the payment confirmation page.\n"
            "3️⃣ 💌 Send the screenshot to one of these channels:\n"
            "   - ✉️ Email: **newnewtry6@gmail.com**\n"
            "   - 📸 Instagram: **@youtuberhawaiijelly** (Youtuber Hawaiijelly)\n"
            "   - 💬 KakaoTalk ID: **jeuspo** (Korea only)\n\n"
            "✅ Once the developer checks your message, "
            "**your 50-use voucher code will be sent right away.** 💙\n"
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
            "📸✨ **바우처 코드를 받는 방법**\n"
            "1️⃣ 오른쪽 네온 버튼으로 결제를 완료해 주세요.\n"
            "2️⃣ 📷 결제 완료 화면(영수증)이 보이면 스크린샷을 찍어 주세요.\n"
            "3️⃣ 💌 아래 중 한 곳으로 스크린샷을 보내 주세요.\n"
            "   - ✉️ 이메일: **newnewtry6@gmail.com**\n"
            "   - 📸 인스타그램: **@youtuberhawaiijelly** (유튜버 하와이 젤리)\n"
            "   - 💬 카카오톡 아이디: **jeuspo**\n\n"
            "✅ 개발자가 메시지를 확인하면 "
            "**50회 이용 가능한 코드가 바로 발송됩니다.** 💙\n"
        )

    # (결제 의사 버튼은 비활성화 상태로 그대로 둠)
    # st.markdown(title_line)
    # if clicked:
    #     st.info(info_already)
    # else:
    #     if st.button(btn_label):
    #         intent_ref.set({
    #             "uid": USER_ID,
    #             "plan": plan_value,
    #             "created_at": datetime.utcnow().isoformat(),
    #         })
    #         st.success(success_msg)
    #         st.rerun()
    # st.caption(caption_text)

    st.info(help_text)

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    # ========== 왼쪽: 피드백 + 관리자 영역 + My Wallet ==========
    with col1:
        # 💌 서비스 피드백
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

        # 🔑 관리자 영역
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

        # 💙 여기부터 My Wallet (Admin 아래에 위치)
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
                You can top up <b>50 therapy sessions</b> at once.
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
                50회 상담 이용권을 한 번에 충전할 수 있어요.
              </p>
              <ul style="font-size:14px; opacity:0.9; margin-top:0;">
                <li>도움이 필요할 때마다 편하게 사용</li>
                <li>위기 문구(자살·극단적 표현)는 항상 무료</li>
                <li>결제 후 바우처 코드로 간편 충전</li>
              </ul>
              <div style="margin-top:14px; text-align:center;">
            """

        st.markdown(card_html, unsafe_allow_html=True)

        paypal_link = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
        btn_text = "💳 3달러 / 50회 이용" if not is_en else "💳 Pay $3 / 50 uses"

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


    # 결제 의사 버튼은 비활성화 (코멘트만 남김)
    # st.markdown(title_line)
    # if clicked:
    #     st.info(info_already)
    # else:
    #     if st.button(btn_label):
    #         intent_ref.set({
    #             "uid": USER_ID,
    #             "plan": plan_value,
    #             "created_at": datetime.utcnow().isoformat(),
    #         })
    #         st.success(success_msg)
    #         st.rerun()
    # st.caption(caption_text)

    st.info(help_text)

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    # ========== 왼쪽: 피드백 + 관리자 영역 ==========
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

    # ========== 오른쪽: Direct Payment 카드 (언어별) ==========
    with col2:
        if is_en:
            st.markdown("### 💳 Direct Payment")
            card_html = """
            <div class="pay-card">
              <p style="font-size:15px; opacity:0.9; margin-bottom:6px;">
                You can top up <b>50 therapy sessions</b> at once.
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
                50회 상담 이용권을 한 번에 충전할 수 있어요.
              </p>
              <ul style="font-size:14px; opacity:0.9; margin-top:0;">
                <li>도움이 필요할 때마다 편하게 사용</li>
                <li>위기 문구(자살·극단적 표현)는 항상 무료</li>
                <li>결제 후 바우처 코드로 간편 충전</li>
              </ul>
              <div style="margin-top:14px; text-align:center;">
            """

        st.markdown(card_html, unsafe_allow_html=True)

        paypal_link = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
        btn_text = "💳 3달러 / 50회 이용" if not is_en else "💳 Pay $3 / 50 uses"

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

# 🔮 Rainbow Neon Payment card (added above visitor stats)
paypal_link = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
if language == "English 🇺🇸":
    pay_title = "☕ 50 safe talks for the price of one coffee"
    pay_line1 = "Beta offer: $3 → 50 credits"
    pay_line2 = "That's about $0.06 per talk."
    pay_privacy = "Your conversations stay private — not shared with anyone, including the operator."
    pay_button = "💳 Pay $3 for 50 talks"
else:
    pay_title = "☕ 카페 라테 한 잔 값으로, 50번 마음 털어놓기"
    pay_line1 = "베타 기간 가격: 3달러 → 50 크레딧"
    pay_line2 = "한 번 대화당 약 70원 정도예요."
    pay_privacy = "여기에서 나눈 대화는 공개되지 않아요. 운영자를 포함한 누구와도 공유되지 않습니다."
    pay_button = "💳 3달러로 50회 채우기"

st.sidebar.markdown(
    f"""
<div class="sidebar-rainbow-card">
  <div class="sidebar-rainbow-inner">
    <div style="font-size:14px; font-weight:600; margin-bottom:4px;">{pay_title}</div>
    <div style="font-size:12px; opacity:0.9;">{pay_line1}</div>
    <div style="font-size:12px; opacity:0.9; margin-bottom:8px;">{pay_line2}</div>
    <a href="{paypal_link}" target="_blank" class="sidebar-rainbow-btn">{pay_button}</a>
    <div style="font-size:11px; opacity:0.75; margin-top:6px; line-height:1.4;">
      {pay_privacy}
    </div>
  </div>
</div>

<style>
.sidebar-rainbow-card {{
  position: relative;
  margin-top: 6px;
  margin-bottom: 14px;
  border-radius: 18px;
  padding: 2px;
  background: rgba(255,255,255,0.06);
  box-shadow: 0 0 18px rgba(255,255,255,0.35);
  overflow: hidden;
}}
.sidebar-rainbow-card::before {{
  content: "";
  position: absolute;
  inset: -2px;
  border-radius: inherit;
  background: conic-gradient(
    from 0deg,
    #ff00cc, #3333ff, #00ffff,
    #33ff33, #ffff00, #ff6600, #ff0066, #ff00cc
  );
  animation: sidebarBorderSpin 7s linear infinite;
  opacity: 0.95;
}}
.sidebar-rainbow-inner {{
  position: relative;
  z-index: 1;
  border-radius: 16px;
  padding: 10px 12px 12px 12px;
  background: rgba(10,10,20,0.96);
  color: #ffffff;
}}
.sidebar-rainbow-btn {{
  display:block;
  width:100%;
  margin-top:6px;
  padding:9px 0;
  text-align:center;
  border-radius: 999px;
  font-size:13px;
  font-weight:700;
  text-decoration:none;
  color:#ffffff;
  background: linear-gradient(
    90deg,
    #ff00cc, #3333ff, #00ffff,
    #33ff33, #ffff00, #ff6600, #ff0066, #ff00cc
  );
  background-size: 300% 300%;
  box-shadow: 0 0 22px rgba(255,255,255,0.4);
  animation: sidebarBtnShift 5s linear infinite,
             sidebarBtnGlow 1.6s ease-in-out infinite;
}}
.sidebar-rainbow-btn:hover {{
  filter: brightness(1.2);
  transform: translateY(-1px);
  box-shadow: 0 0 30px rgba(255,255,255,0.9);
}}
@keyframes sidebarBorderSpin {{
  0% {{ transform: rotate(0deg); }}
  100% {{ transform: rotate(360deg); }}
}}
@keyframes sidebarBtnShift {{
  0% {{ background-position: 0% 50%; }}
  100% {{ background-position: 300% 50%; }}
}}
@keyframes sidebarBtnGlow {{
  0%,100% {{ box-shadow: 0 0 14px rgba(255,255,255,0.4); }}
  50% {{ box-shadow: 0 0 30px rgba(255,255,255,0.9); }}
}}
</style>
""",
    unsafe_allow_html=True
)

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

# 🗑️ 대화 기록 삭제 (세션 + Firestore 둘 다)
if st.sidebar.button(TEXT["clear_history"]):
    st.session_state["chat_history"] = []
    clear_user_history(USER_ID)
    st.sidebar.success(TEXT["history_cleared"])
    st.rerun()

# 💳 내 지갑
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
