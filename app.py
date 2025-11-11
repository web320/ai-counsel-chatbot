# ==========================================
# 💙 EOERWAY AI Therapy v2.9 — Wallet + Voucher + Paywall (50 uses = $3)
# CLEAN REBUILD (syntax safe)
# ==========================================
# - 4시간/7회 무료, 초과 시 크레딧 차감 (위기문구는 항상 무료)
# - 지갑(크레딧) + 바우처(50회/$3) + 관리자 코드 생성기
# - 스타일/질문 바퀴로 단조로움 완화 + 퀵리플라이 버튼
# - 답변 길이: 기본 4~8문장, 필요 시 8~12문장 (max_tokens=900)

import os
import uuid
import json
import time
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
DAILY_FREE_LIMIT = 7              # ⏰ 무료 회수 (기간 내)
RESET_INTERVAL_HOURS = 4          # ⏰ 무료 회수 리셋 주기(시간)
ADMIN_KEYS = ["2356"]             # 🔑 관리자 비밀키(코드 생성용)

# 💳 크레딧/코드 과금 체계
CREDIT_PACK_SIZE = 50             # 1코드 = 50회
CREDIT_PACK_PRICE_USD = 3         # $3 (표기용)

# 🚨 위기 키워드(차감/페이월 우회)
CRISIS_KEYWORDS = [
    "죽고싶", "자살", "해치고", "극단적", "고통스러워", "살기 싫", "포기하고 싶",
    "suicide", "self-harm", "kill myself", "end my life"
]

# ===== Conversational Variety (Style & Question wheels) =====
STYLE_WHEEL = ["Soothe", "Explore", "Clarify", "Plan", "Celebrate"]
QUESTION_WHEEL_KO = ["상황", "몸감각", "생각/자기대화", "가치/욕구", "다음 한 걸음"]
QUESTION_WHEEL_EN = ["situation", "body sensation", "self-talk", "value/need", "next step"]

# ================= ads.txt (for AdSense) =================
try:
    if "ads.txt" in st.query_params:  # Streamlit 1.31+
        st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
        st.stop()
except Exception:
    pass

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

# ================= UID / Session =================
if "uid" not in st.session_state:
    st.session_state["uid"] = str(uuid.uuid4())
USER_ID = st.session_state["uid"]

# ================= Visitor Counter =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_visit_ref = db.collection("user_visits").document(USER_ID)

    if user_visit_ref.get().exists:
        return

    user_visit_ref.set({
        "uid": USER_ID,
        "first_visit": datetime.utcnow().isoformat(),
        "day": today
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

# ================= Language State =================
if "lang" not in st.session_state:
    st.session_state["lang"] = "English 🇺🇸"

col_lang_a, col_lang_b = st.columns([5, 1])
with col_lang_b:
    lang_choice = st.radio(
        label=" ",
        options=["English 🇺🇸", "한국어 🇰🇷"],
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
        "usedup": f"🌙 You've used all {DAILY_FREE_LIMIT} free sessions.",
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
        "admin_make": "Generate"
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
        "admin_make": "코드 생성"
    }

st.title(TEXT["title"])

# ================= CSS =================
st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 18px; }
    .user-bubble {
      background:#b91c1c; color:#fff; border-radius:14px; padding:10px 18px; margin:8px 0;
      display:inline-block; box-shadow:0 0 10px rgba(255,0,0,0.3);
    }
    .bot-bubble {
      font-size:21px; line-height:1.8; border-radius:16px; padding:16px 20px; margin:10px 0;
      background:rgba(15,15,30,.85); color:#fff; border:2px solid transparent;
      border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1; box-shadow:0 0 12px #ffaa00;
      animation:neon 1.6s ease-in-out infinite alternate; word-break:break-word; white-space:pre-wrap;
    }
    @keyframes neon { from { box-shadow:0 0 8px #ffaa00; } to { box-shadow:0 0 22px #ffcc33; } }
    .status { font-size:15px; padding:8px 12px; border-radius:10px; display:inline-block; margin-bottom:8px;
      background:rgba(255,255,255,.06); }
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
    "ad_free": False
}

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    st.session_state.update(data)
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)


def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ================= (Optional) Memory Reader =================

def _get_user_memory(uid: str) -> str:
    doc = db.collection("users").document(uid).collection("memory").document("profile").get()
    if doc.exists:
        return (doc.to_dict() or {}).get("text", "")
    return ""

# ================= Wallet / Voucher Helpers =================

def ensure_user(uid: str):
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if not snap.exists:
        ref.set(defaults, merge=True)
    else:
        missing = {k: v for k, v in defaults.items() if k not in (snap.to_dict() or {})}
        if missing:
            ref.set(missing, merge=True)
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
        "created_at": firestore.SERVER_TIMESTAMP
    })


def redeem_voucher(code: str, uid: str):
    voucher_ref = db.collection("vouchers").document(code)
    user_ref_local = db.collection("users").document(uid)

    @firestore.transactional
    def _tx(transaction):
        v_snap = voucher_ref.get(transaction=transaction)
        if not v_snap.exists:
            raise ValueError("INVALID_CODE")
        v = v_snap.to_dict()
        if v.get("used_by"):
            raise ValueError("ALREADY_USED")

        u_snap = user_ref_local.get(transaction=transaction)
        if not u_snap.exists:
            transaction.set(user_ref_local, defaults)
            u = {"credits": 0, "purchased_packs": 0, "last_reset": datetime.utcnow().isoformat()}
        else:
            u = u_snap.to_dict()

        new_credits = int(u.get("credits", 0)) + int(v.get("credits", 0))
        new_packs = int(u.get("purchased_packs", 0)) + 1

        transaction.update(user_ref_local, {
            "credits": new_credits,
            "purchased_packs": new_packs,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        transaction.update(voucher_ref, {
            "used_by": uid,
            "used_at": firestore.SERVER_TIMESTAMP
        })
        return new_credits

    transaction = db.transaction()
    return _tx(transaction)


def decrement_credit(uid: str, amount: int = 1):
    user_ref_local = db.collection("users").document(uid)

    @firestore.transactional
    def _tx(transaction):
        snap_local = user_ref_local.get(transaction=transaction)
        if not snap_local.exists:
            raise ValueError("NO_USER")
        data_local = snap_local.to_dict() or {}
        curr = int(data_local.get("credits", 0))
        if curr < amount:
            raise ValueError("NO_CREDIT")
        transaction.update(user_ref_local, {
            "credits": curr - amount,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        return curr - amount

    transaction = db.transaction()
    return _tx(transaction)

# ================= Variety Helpers =================

def _next_style_and_qtype():
    if "style_idx" not in st.session_state:
        st.session_state["style_idx"] = 0
    if "q_idx" not in st.session_state:
        st.session_state["q_idx"] = 0
    style = STYLE_WHEEL[st.session_state["style_idx"]]
    st.session_state["style_idx"] = (st.session_state["style_idx"] + 1) % len(STYLE_WHEEL)
    if language == "English 🇺🇸":
        qwheel = QUESTION_WHEEL_EN
    else:
        qwheel = QUESTION_WHEEL_KO
    qtype = qwheel[st.session_state["q_idx"]]
    st.session_state["q_idx"] = (st.session_state["q_idx"] + 1) % len(qwheel)
    return style, qtype


def _starter(text: str) -> str:
    s = (text or "").strip()
    return s[:14] if len(s) > 14 else s


def quick_replies_for(lang: str):
    base_ko = ["계속 얘기할래요", "지금 할 수 있는 1분 행동 알려줘", "짧게 요약해줘"]
    base_en = ["Tell me more", "Give me a 1‑minute step", "Summarize briefly"]
    return base_en if lang == "English 🇺🇸" else base_ko

# ================= AI Response Function =================

def is_crisis(text: str) -> bool:
    t = (text or "").lower()
    for k in CRISIS_KEYWORDS:
        if k.lower() in t:
            return True
    return False


def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = (
                "You're talking to someone who came here because they're hurting. Not as a therapist, "
                "but as a real person who genuinely cares. Default to 4–8 sentences; if the user writes "
                "a long message or asks for depth, go longer (up to ~10–12). Never diagnose or suggest "
                "medication. If they mention self‑harm or suicide, gently acknowledge their pain and suggest professional help."
            )
        else:
            system_prompt = (
                "[톤] 따뜻하고 인간적이며 존댓말. [길이] 기본 4~8문장, 필요 시 8~12문장까지 확장. "
                "[우선순위] 안전 최우선(자해/자살 언급 시 고통 인정 + 112/1393 등 안내). "
                "[하지 말 것] 진단·약물·법률 조언/가스라이팅/과도한 해결책 나열. "
                "[구성 힌트] 공감→감정명명→정상화→작은 제안(선택)→연결감."
            )

        user_memory = _get_user_memory(USER_ID)
        style, qtype = _next_style_and_qtype()

        if "last_starters" not in st.session_state:
            st.session_state["last_starters"] = []
        forbidden_starters = " | ".join(st.session_state["last_starters"][-4:])

        context_messages = [{"role": "system", "content": system_prompt}]
        context_messages.append({"role": "system", "content": f"Current style focus: {style}. Ask exactly one {qtype}-type question at the end."})
        if forbidden_starters:
            context_messages.append({"role": "system", "content": f"Avoid starting with these openings: {forbidden_starters}"})
        if user_memory:
            context_messages.append({"role": "system", "content": f"Personalization memory: {user_memory}"})

        for msg in st.session_state["chat_history"][-10:]:
            context_messages.append({"role": msg["role"], "content": msg["content"]})

        context_messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=context_messages,
            temperature=0.7,
            max_tokens=900,
            stream=True
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
                time.sleep(0.02)

        timestamp = datetime.utcnow().isoformat()

        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": full_text.strip(),
            "lang": language,
            "created_at": timestamp
        })

        st.session_state["chat_history"].append({"role": "user", "content": user_input, "timestamp": timestamp})
        st.session_state["chat_history"].append({"role": "assistant", "content": full_text.strip(), "timestamp": timestamp})

        try:
            st.session_state["last_starters"].append(_starter(full_text))
            st.session_state["last_starters"] = st.session_state["last_starters"][-5:]
        except Exception:
            pass

        st.session_state["quick_replies"] = quick_replies_for(language)
        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Paywall Guard =================

def show_paywall():
    st.warning(TEXT["paywall"])  # 언어별 문구
    wallet_label = TEXT["wallet"]
    redeem_label = TEXT["redeem"]
    note = f"- **{CREDIT_PACK_SIZE}회 충전 코드 = ${CREDIT_PACK_PRICE_USD}**  \n- 이미 코드를 갖고 있다면 **사이드바 → ‘{wallet_label}’ → ‘{redeem_label}’**에서 적용하세요."
    st.markdown(note)


def charge_if_needed(user_input: str, free_used: int, free_limit: int):
    if is_crisis(user_input):
        return True, False
    if free_used < free_limit:
        return True, False
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
    else:
        title_line = "#### 50회 이용권 3,000원 결제 의사 확인"
        btn_label = "💳 3,000원에 50회 이용권, 결제 의사가 있으신가요?"
        info_already = "💙 이미 결제 의사를 눌러주셨어요. 정말 감사합니다."
        success_msg = "결제 기능이 열리면 가장 먼저 알려드릴게요 💖"
        caption_text = f"지금까지 {total_intents}명이 결제 의사를 눌러주셨어요."
        plan_value = "50회_3000원"
        help_text = "지금 바로 이용하려면 사이드바(내 지갑)에서 코드를 충전하세요."

    st.markdown(title_line)

    if clicked:
        st.info(info_already)
    else:
        if st.button(btn_label):
            intent_ref.set({"uid": USER_ID, "plan": plan_value, "created_at": datetime.utcnow().isoformat()})
            st.success(success_msg)
            st.rerun()

    st.caption(caption_text)
    st.info(help_text)

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader(TEXT["feedback_title"])
        fb = st.text_area(label=" ", placeholder=TEXT["feedback_placeholder"])
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
                st.success(TEXT["feedback_sent"])}

    with col2:
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

# ================= Display Chat History =================

def display_chat_history():
    for idx, msg in enumerate(st.session_state["chat_history"]):
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

    qr = st.session_state.get("quick_replies", [])
    if qr:
        cols = st.columns(len(qr))
        for i, q in enumerate(qr):
            key_str = f"qr_{i}_{len(st.session_state.get('chat_history', []))}_{i}"
            if cols[i].button(q, key=key_str):
                st.session_state["pending_input"] = q
                st.rerun()

# ================= Chat Main Page =================

def render_chat_page():
    ensure_user(USER_ID)

    credits_now = int(st.session_state.get("credits", 0))
    usage = int(st.session_state.get("usage_count", 0))

    if usage < DAILY_FREE_LIMIT:
        left_display = DAILY_FREE_LIMIT - usage
        plan_label = TEXT["free"]
    else:
        left_display = credits_now
        plan_label = TEXT["paid"] if credits_now > 0 else TEXT["free"]

    st.markdown(
        f"<div class='status'>{plan_label} — {TEXT['status_left']} {max(left_display, 0)}회</div>",
        unsafe_allow_html=True
    )

    now = datetime.utcnow()
    try:
        last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    except Exception:
        last_reset = now

    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info(TEXT["reset"])
        usage = 0

    display_chat_history()

    preset = st.session_state.pop("pending_input", None)
    if preset:
        user_input = preset
    else:
        user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    proceed, used_credit = charge_if_needed(user_input, free_used=usage, free_limit=DAILY_FREE_LIMIT)
    if not proceed:
        st.session_state["show_payment"] = True
        st.rerun()
        return

    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

    reply = stream_reply(user_input)
    if reply:
        if not used_credit and usage < DAILY_FREE_LIMIT:
            persist_user({"usage_count": usage + 1})
        st.rerun()

# ================= Sidebar =================

st.sidebar.header("📜 History / 대화 기록")

total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(
    (
        "<div style=\"margin-top:12px;margin-bottom:16px;padding:8px 10px;border-radius:10px;"
        "background:rgba(255,255,255,0.03);font-size:13px;color:rgba(255,255,255,0.85);\">"
        f"🌍 <b>Total {total_visits:,}명</b><br>"
        f"☀️ <b>Today {daily_visits:,}명</b>"
        "</div>"
    ),
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
    code_input = st.text_input(label=" ", placeholder=TEXT["wallet_help"])  # 라벨 숨김
    ok = st.form_submit_button(TEXT["redeem"])
    if ok and code_input.strip():
        try:
            new_balance = redeem_voucher(code_input.strip(), USER_ID)
            persist_user({"credits": int(new_balance)})
            st.success(TEXT["voucher_ok"] + str(new_balance))
            st.rerun()
        except ValueError as e:
            msg = str(e)
            if msg == "INVALID_CODE":
                st.error(TEXT["voucher_bad"])
            elif msg == "ALREADY_USED":
                st.error(TEXT["voucher_used"])
            else:
                st.error("충전에 실패했어요. 잠시 후 다시 시도해주세요.")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

with st.sidebar.expander(TEXT["admin_gen"]):
    admin_key = st.text_input("Admin Key", type="password")
    if admin_key and admin_key in ADMIN_KEYS:
        st.session_state.is_admin = True
        st.success("관리자 모드 활성화")

    if st.session_state.is_admin:
        def gen_code(n: int = 8) -> str:
            return uuid.uuid4().hex[:n].upper()

        num = st.number_input("생성 개수", min_value=1, max_value=200, value=10)
        credits_each = st.number_input("코드당 크레딧", min_value=1, max_value=1000, value=CREDIT_PACK_SIZE)
        note = st.text_input("메모(선택)", f"{CREDIT_PACK_SIZE}회/${CREDIT_PACK_PRICE_USD}")
        if st.button(TEXT["admin_make"]):
            out_codes = []
            for _ in range(int(num)):
                c = gen_code(10)
                create_voucher(c, int(credits_each), note=note)
                out_codes.append(c)
            st.success("코드 생성 완료! 아래 목록을 보관하세요.")
            st.code("\n".join(out_codes))

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


