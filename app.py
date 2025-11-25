# ==========================================
# 💙 EOERWAY AI Therapy v2.9 (No Onboarding)
# Wallet + Voucher + Paywall + Memory
# Unique Visitor Counter + Persistent Chat History
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
BASIC_LIMIT = 50
ADMIN_KEYS = ["2356"]

# 💳 Credit Pack: $1 for 15 uses
CREDIT_PACK_SIZE = 15
CREDIT_PACK_PRICE_USD = 1

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

# ================= User ID (persistent via query params) =================
def get_or_create_user_id() -> str:
    qp = st.query_params
    uid_val = qp.get("uid")
    if uid_val:
        if isinstance(uid_val, list):
            return uid_val[0]
        return uid_val
    new_id = str(uuid.uuid4())
    qp["uid"] = new_id
    return new_id

USER_ID = get_or_create_user_id()

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

update_visit_stats()

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
  line-height:1.5;
  border-radius:16px;
  padding:16px 20px;
  margin:4px 0;
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

# ================= Chat History Helpers =================
def load_chat_history(uid: str, limit: int = 50):
    """Firestore에서 유저별 대화 기록 불러오기"""
    try:
        msgs_ref = (
            db.collection("users")
            .document(uid)
            .collection("messages")
            .order_by("created_at")
            .limit(limit)
        )
        docs = msgs_ref.stream()
        history = []
        for doc in docs:
            d = doc.to_dict() or {}
            role = d.get("role")
            content = d.get("content")
            if role in ("user", "assistant") and content:
                history.append({"role": role, "content": content})
        return history
    except Exception as e:
        print("load_chat_history error:", e)
        return []

def clear_chat_history_in_db(uid: str):
    """Firestore에서 유저별 대화 기록 전체 삭제"""
    try:
        msgs_ref = db.collection("users").document(uid).collection("messages")
        docs = list(msgs_ref.stream())
        for doc in docs:
            doc.reference.delete()
    except Exception as e:
        print("clear_chat_history error:", e)

# ================= Chat History (session) =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = load_chat_history(USER_ID)

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
    user_ref2 = db.collection("users").document(uid)

    @firestore.transactional
    def _tx(transaction):
        v_snap = voucher_ref.get(transaction=transaction)
        if not v_snap.exists:
            raise ValueError("INVALID_CODE")

        v = v_snap.to_dict()
        if v.get("used_by"):
            raise ValueError("ALREADY_USED")

        u_snap = user_ref2.get(transaction=transaction)
        u = u_snap.to_dict() if u_snap.exists else defaults

        new_credits = int(u.get("credits", 0)) + int(v.get("credits", 0))
        new_packs = int(u.get("purchased_packs", 0)) + 1

        transaction.update(user_ref2, {
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
    user_ref2 = db.collection("users").document(uid)

    @firestore.transactional
    def _tx(transaction):
        snap2 = user_ref2.get(transaction=transaction)
        data = snap2.to_dict() or {}
        curr = int(data.get("credits", 0))
        if curr < amount:
            raise ValueError("NO_CREDIT")
        transaction.update(user_ref2, {"credits": curr - amount})
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

[중략: 영어 버전 전체 프롬프트는 기존 코드와 동일하게 유지]"""
        else:
            system_prompt = """
너는 사용자의 답변에 적절한 답변을 해주는 따뜻한 대화상대야야
[중략: 한국어 버전 전체 프롬프트는 기존 코드와 동일하게 유지]"""

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

        # --------- 유저별 메시지 기록 (Persistent Chat History) ----------
        try:
            msgs_ref = db.collection("users").document(USER_ID).collection("messages")
            msgs_ref.add({
                "role": "user",
                "content": user_input,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
            msgs_ref.add({
                "role": "assistant",
                "content": reply_text,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
        except Exception as e:
            print("per-user messages error:", e)

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
    # 위기 문구는 항상 무료
    if is_crisis(user_input):
        return True, False

    # 무료 한도 내에서는 차감 없음
    if free_used < free_limit:
        return True, False

    # 무료 한도 초과 → 크레딧 차감
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

    # 무료 사용량 리셋 (4시간 기준)
    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        usage = 0
        persist_user({
            "usage_count": 0,
            "last_reset": now.isoformat()
        })
        st.info(TEXT["reset"])

    # 상태 표시
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

    # 과거 대화 표시
    display_chat_history()

    # 입력
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    proceed, used_credit = charge_if_needed(user_input, free_used=usage, free_limit=DAILY_FREE_LIMIT)
    if not proceed:
        return

    # 유저 발화 표시
    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True
    )

    reply = stream_reply(user_input)

    if reply:
        # 무료 구간이면 usage_count 증가
        if not used_credit and usage < DAILY_FREE_LIMIT:
            persist_user({"usage_count": usage + 1})
        st.rerun()

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

# 대화 기록 삭제 (Firestore + session 둘 다)
if st.sidebar.button(TEXT["clear_history"]):
    clear_chat_history_in_db(USER_ID)
    st.session_state["chat_history"] = []
    st.sidebar.success(TEXT["history_cleared"])
    st.rerun()

# 방문자 통계
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

# 결제 / 피드백 페이지 링크 (별도 페이지)
st.sidebar.markdown("### 💳 Payment / 결제")
try:
    st.sidebar.page_link("pages/payment.py", label="➡️ 결제 / 피드백 페이지로 이동")
except Exception:
    st.sidebar.markdown("상단 메뉴에서 결제 페이지를 열 수 있어요.")

# 지갑 / 바우처
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

# ================= Main Render =================
render_chat_page()
# ==========================================
# 💳 EOERWAY Payment & Feedback Page
# $1 = 15 uses
# ==========================================

import os, uuid, json
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💳 Payment | EOERWAY", layout="centered")

# ================= Constants / Config =================
ADMIN_KEYS = ["2356"]

CREDIT_PACK_SIZE = 15
CREDIT_PACK_PRICE_USD = 1

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

# ================= User ID (same logic as app.py) =================
def get_or_create_user_id() -> str:
    qp = st.query_params
    uid_val = qp.get("uid")
    if uid_val:
        if isinstance(uid_val, list):
            return uid_val[0]
        return uid_val
    new_id = str(uuid.uuid4())
    qp["uid"] = new_id
    return new_id

USER_ID = get_or_create_user_id()

# ================= Firestore User Defaults (for admin credit) =================
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
if not user_ref.get().exists:
    user_ref.set(defaults)

def get_user(uid: str) -> dict:
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() or {}

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)

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
        "payment_title": "💳 Payment & Voucher",
        "chat_return": "💬 Back to Chat",
        "feedback_title": "💌 Service Feedback",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "admin_gen": "🔑 Admin — Generate Voucher Codes",
        "admin_make": "Generate",
        "admin_success": f"🔓 Admin mode granted {CREDIT_PACK_SIZE} credits!",
        "admin_already": "✅ Already added in this session.",
        "admin_wrong": "❌ Wrong admin password.",
        "voucher_tip": f"One code = {CREDIT_PACK_SIZE} uses / ${CREDIT_PACK_PRICE_USD}",
    }
else:
    TEXT = {
        "payment_title": "💳 결제 & 바우처",
        "chat_return": "💬 대화창으로 돌아가기",
        "feedback_title": "💌 서비스 피드백",
        "feedback_placeholder": "예: 상담이 정말 따뜻했어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "admin_gen": "🔑 관리자 — 바우처 코드 생성",
        "admin_make": "코드 생성",
        "admin_success": f"🔓 관리자 모드로 {CREDIT_PACK_SIZE}회 충전됨!",
        "admin_already": "✅ 이미 추가되었습니다",
        "admin_wrong": "❌ 관리자 비밀번호가 틀렸어요",
        "voucher_tip": f"코드 1개 = {CREDIT_PACK_SIZE}회 / ${CREDIT_PACK_PRICE_USD}",
    }

# ================= CSS =================
st.markdown(
    """
<style>
.pay-card {
  background: radial-gradient(circle at top left, rgba(255,255,255,0.12), rgba(0,0,0,0.6));
  border-radius:20px;
  padding:18px 20px;
  border:1px solid rgba(255,255,255,0.18);
  box-shadow:0 18px 30px rgba(0,0,0,0.55);
  backdrop-filter: blur(14px);
}

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

# ================= Layout =================
st.title(TEXT["payment_title"])

# 채팅 페이지로 돌아가기 링크
try:
    st.page_link("app.py", label=TEXT["chat_return"])
except Exception:
    st.write("👈 사이드바에서 채팅 페이지로 돌아갈 수 있어요.")

st.markdown("---")

col_left, col_right = st.columns([3, 2])

# ---------- 오른쪽: 결제 카드 ----------
with col_right:
    if language == "English 🇺🇸":
        card_html = f"""
        <div class="pay-card">
          <p style="font-size:15px; opacity:0.9; margin-bottom:6px;">
            You can top up <b>{CREDIT_PACK_SIZE} therapy sessions</b> at once.
          </p>
          <ul style="font-size:14px; opacity:0.9; margin-top:0;">
            <li>$1 → {CREDIT_PACK_SIZE} uses</li>
            <li>Use whenever you need emotional support</li>
            <li>Crisis messages (suicide / self-harm) are always free</li>
            <li>After payment, you'll receive a voucher code to recharge</li>
          </ul>
          <div style="margin-top:14px; text-align:center;">
        """
    else:
        card_html = f"""
        <div class="pay-card">
          <p style="font-size:15px; opacity:0.9; margin-bottom:6px;">
            한 번 결제로 <b>{CREDIT_PACK_SIZE}회 상담 이용권</b>을 충전할 수 있어요.
          </p>
          <ul style="font-size:14px; opacity:0.9; margin-top:0;">
            <li>1달러 → {CREDIT_PACK_SIZE}회 이용</li>
            <li>도움이 필요할 때마다 편하게 사용</li>
            <li>위기 문구(자살·극단적 표현)는 항상 무료</li>
            <li>결제 후 바우처 코드로 간편 충전</li>
          </ul>
          <div style="margin-top:14px; text-align:center;">
        """

    st.markdown(card_html, unsafe_allow_html=True)

    paypal_link = "https://www.paypal.com/ncp/payment/32BZVWVT2KSDS"
    btn_text = "💳 Pay $1 / 15 uses" if language == "English 🇺🇸" else "💳 1달러 / 15회 결제하기"

    st.markdown(
        f"""
        <a href="{paypal_link}" target="_blank" class="rainbow-btn">{btn_text}</a>
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 결제 후 스크린샷 안내
    if language == "English 🇺🇸":
        payment_notice = (
            "📸✨ **How to receive your voucher code**\n"
            "1️⃣ Use the button above to complete your payment.\n"
            "2️⃣ 📷 Take a screenshot of the payment confirmation page.\n"
            "3️⃣ 💌 Send the screenshot to one of these channels:\n"
            "   - ✉️ Email: **newnewtry6@gmail.com**\n"
            "   - 📸 Instagram: **@youtuberhawaiijelly**\n"
            "   - 💬 KakaoTalk ID: **jeuspo** (Korea only)\n\n"
            "✅ Once the developer checks your message, "
            f"**your {CREDIT_PACK_SIZE}-use voucher code will be sent.** 💙\n"
        )
    else:
        payment_notice = (
            "📸✨ **바우처 코드를 받는 방법**\n"
            "1️⃣ 위 버튼으로 결제를 완료해 주세요.\n"
            "2️⃣ 📷 결제 완료 화면(영수증)을 스크린샷으로 찍어 주세요.\n"
            "3️⃣ 💌 아래 중 한 곳으로 스크린샷을 보내 주세요.\n"
            "   - ✉️ 이메일: **newnewtry6@gmail.com**\n"
            "   - 📸 인스타그램: **@youtuberhawaiijelly** (유튜버 하와이 젤리)\n"
            "   - 💬 카카오톡 아이디: **jeuspo**\n\n"
            "✅ 개발자가 메시지를 확인하면 "
            f"**{CREDIT_PACK_SIZE}회 이용 가능한 코드가 발송됩니다.** 💙\n"
        )

    st.markdown("---")
    st.markdown(payment_notice)

# ---------- 왼쪽: 피드백 + 관리자 바우처 생성 ----------
with col_left:
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

    st.markdown("---")
    st.markdown(f"### {TEXT['admin_gen']}")

    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False

    admin_key = st.text_input("Admin Key", type="password", key="admin_key_payment")
    if admin_key and admin_key in ADMIN_KEYS:
        st.session_state["is_admin"] = True
        st.success("관리자 모드 활성화")

    if st.session_state["is_admin"]:
        # (선택) 관리자 본인에게 크레딧 바로 넣기
        credit_admin = st.text_input("크레딧 관리자 비밀번호", type="password", key="credit_admin_pw_payment")
        if credit_admin:
            if credit_admin in ADMIN_KEYS:
                if not st.session_state.get("admin_unlocked_payment"):
                    current_data = get_user(USER_ID)
                    current_credits = int(current_data.get("credits", 0))
                    new_credits = current_credits + CREDIT_PACK_SIZE
                    persist_user({"credits": new_credits})
                    st.session_state["admin_unlocked_payment"] = True
                    st.success(TEXT["admin_success"])
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
