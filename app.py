import os, uuid, json, time, random, io, re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v4.1"
DAILY_FREE_LIMIT = 7            # 무료 상담 횟수
RESET_INTERVAL_HOURS = 4        # 무료 상담 회복 주기(시간)
ADMIN_KEYS = ["2356"]

# 💳 크레딧/코드 과금 체계
CREDIT_PACK_SIZE = 50           # 50회
CREDIT_PACK_PRICE_USD = 3       # $3 (영문 표기)

# 리퍼럴
REF_BONUS = 5                   # 서로 +5회

# 워터마크/배너
LOW_BALANCE_THRESHOLD = 1
WATERMARK_TEXT = "Made with 💙 EOERWAY — Free 7 uses, crisis chats always free."
BASE_URL = st.secrets.get("BASE_URL") or "https://eoerway.com"

# 🚨 위기 키워드(차감/페이월 우회)
CRISIS_KEYWORDS = [
    "죽고싶", "자살", "해치고", "극단적", "고통스러워", "살기 싫", "포기하고 싶",
    "suicide", "self-harm", "kill myself", "end my life", "crisis", "panic", "공황"
]

# ================= ads.txt (for AdSense) =================
params_for_ads = getattr(st, "query_params", None) or st.experimental_get_query_params()
if "ads.txt" in params_for_ads:
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

# ================= UID & Query Params =================
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())
USER_ID = st.session_state["user_id"]
# URL에 uid 노출(선택): 새로고침 시 동일 세션 유지용
try:
    st.experimental_set_query_params(uid=USER_ID)
except Exception:
    pass

# ================= Language =================
if "lang" not in st.session_state:
    st.session_state["lang"] = "English 🇺🇸"

col_title, col_lang = st.columns([5, 1])
with col_lang:
    lang_choice = st.radio(" ", ["English 🇺🇸", "한국어 🇰🇷"], horizontal=True, label_visibility="collapsed",
                           index=0 if st.session_state["lang"] == "English 🇺🇸" else 1)
st.session_state["lang"] = lang_choice
language = st.session_state["lang"]

# ================= i18n Texts =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "❤️ A Warm AI Friend You Can Lean On",
        "free": "🌱 Free Trial",
        "paid": "💎 Premium User",
        "input": "How are you feeling right now?",
        "warn": "Please enter something 💬",
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

# ================= Title & CSS =================
st.title(TEXT["title"])
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
.user-bubble{
  background:#b91c1c;color:#fff;border-radius:14px;padding:10px 18px;margin:8px 0;display:inline-block;
  box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble{
  font-size:21px;line-height:1.8;border-radius:16px;padding:16px 20px;margin:10px 0;background:rgba(15,15,30,.85);
  color:#fff;border:2px solid transparent;border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00;animation:neon 1.6s ease-in-out infinite alternate;word-break:break-word;white-space:pre-wrap;
}
@keyframes neon{from{box-shadow:0 0 8px #ffaa00;}to{box-shadow:0 0 22px #ffcc33;}}
.status{font-size:15px;padding:8px 12px;border-radius:10px;display:inline-block;margin-bottom:8px;background:rgba(255,255,255,.06);}
</style>
""", unsafe_allow_html=True)

# ================= Defaults in Firestore / Session =================
defaults = {
    "usage_count": 0,                    # 무료 사용량
    "last_reset": datetime.utcnow().isoformat(),
    "credits": 0,                        # 유료 크레딧
    "purchased_packs": 0,
    "referred_by": None,
    "ref_bonus_applied": False,
}

def ensure_user(uid: str):
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if not snap.exists:
        ref.set(defaults, merge=True)
        return ref, defaults
    data = snap.to_dict() or {}
    # 누락 필드 보강
    need_merge = {k: v for k, v in defaults.items() if k not in data}
    if need_merge:
        ref.set(need_merge, merge=True)
        data.update(need_merge)
    return ref, data

user_ref, user_doc = ensure_user(USER_ID)
for k, v in (user_doc or {}).items():
    st.session_state.setdefault(k, v)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ================= Visitor Counter (유저당 1회만) =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    uv_ref = db.collection("user_visits").document(USER_ID)
    if uv_ref.get().exists: return
    uv_ref.set({"uid": USER_ID, "first_visit": datetime.utcnow().isoformat(), "day": today})

    total_ref = db.collection("stats").document("total")
    daily_ref = db.collection("stats").document(today)
    if total_ref.get().exists: total_ref.update({"count": firestore.Increment(1)})
    else: total_ref.set({"count": 1})
    if daily_ref.get().exists: daily_ref.update({"count": firestore.Increment(1)})
    else: daily_ref.set({"count": 1})

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

# ================= Crisis / Charging =================
def is_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in [k.lower() for k in CRISIS_KEYWORDS])

def decrement_credit(uid: str, amount: int = 1):
    user_ref = db.collection("users").document(uid)
    @firestore.transactional
    def _tx(tx):
        snap = user_ref.get(transaction=tx)
        if not snap.exists: raise ValueError("NO_USER")
        d = snap.to_dict() or {}
        curr = int(d.get("credits", 0))
        if curr < amount: raise ValueError("NO_CREDIT")
        tx.update(user_ref, {"credits": curr - amount, "updated_at": firestore.SERVER_TIMESTAMP})
        return curr - amount
    tx = db.transaction()
    return _tx(tx)

def charge_if_needed(user_input: str, free_used: int, free_limit: int):
    """무료 한도 초과 시 크레딧 1 차감. (위기는 우회)"""
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
        return False, False

# ================= Referral (서로 +5) =================
def sidebar_referral_box():
    st.sidebar.subheader("🎁 친구에게 5회 선물하기")
    if st.sidebar.button("초대 링크 생성", use_container_width=True):
        code = str(uuid.uuid4())[:8]
        db.collection("referral_codes").document(code).set({
            "inviter_uid": USER_ID,
            "created_at": firestore.SERVER_TIMESTAMP,
            "used_by": [],
        })
        link = f"{BASE_URL}?ref={code}"
        st.sidebar.success("이 링크를 친구에게 보내세요.")
        st.sidebar.code(link, language="text")

def apply_referral_from_query():
    params = getattr(st, "query_params", None) or st.experimental_get_query_params()
    ref_code = None
    if isinstance(params, dict):
        ref_code = params.get("ref")
        if isinstance(ref_code, list): ref_code = ref_code[0] if ref_code else None
    if not ref_code: return
    if st.session_state.get("referred_by"): return
    code_doc = db.collection("referral_codes").document(ref_code).get()
    if code_doc.exists:
        persist_user({"referred_by": ref_code})

def maybe_apply_referral_bonus(first_message: bool):
    if not first_message: return
    u = db.collection("users").document(USER_ID).get().to_dict() or {}
    if u.get("ref_bonus_applied") or not u.get("referred_by"): return
    code = u["referred_by"]
    code_ref = db.collection("referral_codes").document(code)
    code_snap = code_ref.get()
    inviter_uid = code_snap.to_dict().get("inviter_uid") if code_snap.exists else None
    batch = db.batch()
    # 초대한 사람
    if inviter_uid:
        inviter_ref = db.collection("users").document(inviter_uid)
        batch.update(inviter_ref, {"credits": firestore.Increment(REF_BONUS)})
        batch.update(code_ref, {"used_by": firestore.ArrayUnion([USER_ID])})
    # 나
    me_ref = db.collection("users").document(USER_ID)
    batch.update(me_ref, {"credits": firestore.Increment(REF_BONUS), "ref_bonus_applied": True})
    batch.commit()
    st.toast(f"초대 보너스 +{REF_BONUS}회가 추가되었습니다!")

# ================= UI Helpers =================
def free_remaining_and_reset():
    """사용자의 무료 남은 횟수 계산 + 리셋 처리"""
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    # 리셋 체크
    if now - last_reset >= timedelta(hours=RESET_INTERVAL_HOURS):
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info(TEXT["reset"])
    usage = int(st.session_state.get("usage_count", 0))
    free_left = max(0, DAILY_FREE_LIMIT - usage)
    return free_left

def maybe_show_low_balance_banner():
    free_left = free_remaining_and_reset()
    total_left = free_left + int(st.session_state.get("credits", 0))
    if total_left == LOW_BALANCE_THRESHOLD:
        st.warning("남은 1회예요. 끊기지 않게 이어가요 — **50회 = $3**")

def sidebar_payment_hint():
    st.sidebar.markdown(
        "💳 **50회 = $3**  \n"
        "결제 후 스크린샷을 **newnewtry6@gmail.com** 또는 인스타 **@Hawaiijelly**(Youtuber Hawaiijelly),  \n"
        "카톡 **jeuspo**로 보내주세요. 바우처 코드를 드립니다. 💙"
    )

def render_watermark():
    st.caption(WATERMARK_TEXT)

def feedback_3emoji(turn_idx: int):
    if turn_idx != 3: return
    st.markdown("**오늘 대화는 어땠나요?**")
    c1, c2, c3 = st.columns(3)
    clicked, reason = None, None
    with c1:
        if st.button("👍 좋았어요"): clicked = "up"
    with c2:
        if st.button("😐 보통이에요"): clicked = "neutral"
    with c3:
        if st.button("👎 별로였어요"): clicked = "down"
    if clicked:
        if clicked == "down":
            st.info("아쉬웠던 점을 골라주세요.")
            r1, r2, r3 = st.columns(3)
            if r1.button("로봇 같았음"): reason = "robotic"
            if r2.button("반복적임"): reason = "repetitive"
            if r3.button("도움 안 됨"): reason = "not_helpful"
        db.collection("users").document(USER_ID).collection("feedback").add({
            "ts": firestore.SERVER_TIMESTAMP, "rating": clicked, "reason": reason
        })
        st.success("소중한 의견 고마워요 💙")

def download_session_report(history, next_step="내일 3분 호흡루틴 해보기"):
    lines = [
        "EOERWAY — 오늘 감정 리포트",
        f"생성시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "", "— 대화 요약(최근 10개):"
    ]
    for m in history[-10:]:
        prefix = "🙋" if m["role"]=="user" else "💙"
        lines.append(f"{prefix} {m['content']}")
    lines += ["", f"— 내일의 한 걸음: {next_step}", "", "EOERWAY | Free 7 uses — https://eoerway.com"]
    buf = io.BytesIO("\n".join(lines).encode("utf-8"))
    st.download_button("🧾 세션 리포트 저장(.txt)", buf, file_name="eoerway_report.txt")

def wow_moment_box():
    st.info("지금 제일 힘든 감정을 골라주세요. 60초 안에 한숨 돌리게 도와드릴게요.")
    cols = st.columns(5)
    for i, lab in enumerate(["불안", "외로움", "수면", "공허", "분노"]):
        if cols[i].button(lab):
            st.success(f"'{lab}'에 도움이 되는 루틴: 들숨4-멈춤4-날숨6 ✨")
            st.button("⏱️ 3분 타이머 시작", type="secondary")

# ================= Long-term Memory (읽기만) =================
def _get_user_memory(uid: str) -> str:
    doc = db.collection("users").document(uid).collection("memory").document("profile").get()
    if doc.exists:
        return (doc.to_dict() or {}).get("text", "")
    return ""

# ================= Display Chat History =================
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def display_chat_history():
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

# ================= AI Response (Streaming) =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = (
                "You are a warm, human, supportive AI friend. Listen first, name the feeling, "
                "normalize it, and gently suggest one tiny optional action. Avoid diagnosis/meds. "
                "If self-harm/suicide mentioned, prioritize safety and suggest professional help."
            )
        else:
            system_prompt = (
                "당신은 따뜻하고 인간적인 상담 AI입니다. 먼저 공감하고 감정을 구체적으로 이름 붙인 뒤, "
                "정상화하고 원하면 지금 당장 가능한 아주 작은 선택지 1가지만 부드럽게 제안하세요. "
                "자해·자살 언급 시 안전을 우선하고 112/1393 등 즉각적 도움을 제시하세요."
            )

        # 메모리(선택)
        user_memory = _get_user_memory(USER_ID)
        messages = [{"role": "system", "content": system_prompt}]
        if user_memory:
            messages.append({"role": "system", "content": f"User themes: {user_memory}"})

        for m in st.session_state["chat_history"][-10:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
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
                placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
                time.sleep(0.03)

        timestamp = datetime.utcnow().isoformat()
        # Firestore: 간단 기록
        db.collection("chats").add({
            "uid": USER_ID, "input": user_input, "reply": full_text.strip(),
            "lang": language, "created_at": timestamp
        })
        # 세션 기록
        st.session_state["chat_history"] += [
            {"role": "user", "content": user_input, "timestamp": timestamp},
            {"role": "assistant", "content": full_text.strip(), "timestamp": timestamp},
        ]
        return full_text.strip()
    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Payment & Feedback =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])

    intent_ref = db.collection("purchase_intent").document(USER_ID)
    intent_doc = intent_ref.get()
    already = intent_doc.exists
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
            "📸 **After completing payment, please send a screenshot to:**\n"
            "- ✉️ **newnewtry6@gmail.com**\n"
            "- 📸 Instagram **@youtuberhawaiijelly**\n"
            "- 💬 KakaoTalk **jeuspo** (KR)\n"
        )
    else:
        title_line = "#### 50회 이용권 3,000원 결제 의사 확인"
        btn_label = "💳 3,000원에 50회 이용권, 결제 의사가 있으신가요?"
        info_already = "💙 이미 결제 의사를 눌러주셨어요. 감사합니다."
        success_msg = "결제 기능이 열리면 가장 먼저 알려드릴게요 💖"
        caption_text = f"지금까지 {total_intents}명이 결제 의사를 눌러주셨어요."
        plan_value = "50회_3000원"
        help_text = "지금 바로 이용하려면 사이드바(내 지갑)에서 코드를 충전하세요."
        payment_notice = (
            "📸 **결제 완료 후 스크린샷을 아래로 보내주세요.**\n"
            "- ✉️ **newnewtry6@gmail.com**\n"
            "- 📸 인스타 **@youtuberhawaiijelly**\n"
            "- 💬 카카오톡 **jeuspo**\n"
        )

    st.markdown(title_line)
    if already:
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
                st.success(TEXT["admin_success"])
                # 관리자 즉시 50회 충전(데모용)
                persist_user({"credits": int(st.session_state.get("credits", 0)) + 50})
            else:
                st.error(TEXT["admin_wrong"])

    with col2:
        st.markdown("### 💳 Direct Payment")
        st.link_button("💳 PayPal ($3 / 50 uses)", "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG")
        st.markdown("---")
        st.markdown(payment_notice)

# ================= Wallet / Voucher =================
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
    def _tx(tx):
        v_snap = voucher_ref.get(transaction=tx)
        if not v_snap.exists: raise ValueError("INVALID_CODE")
        v = v_snap.to_dict()
        if v.get("used_by"): raise ValueError("ALREADY_USED")

        u_snap = user_ref.get(transaction=tx)
        if not u_snap.exists: tx.set(user_ref, defaults); u = {"credits": 0, "purchased_packs": 0}
        else: u = u_snap.to_dict() or {}

        new_credits = int(u.get("credits", 0)) + int(v.get("credits", 0))
        new_packs = int(u.get("purchased_packs", 0)) + 1
        tx.update(user_ref, {
            "credits": new_credits,
            "purchased_packs": new_packs,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        tx.update(voucher_ref, {"used_by": uid, "used_at": firestore.SERVER_TIMESTAMP})
        return new_credits
    tx = db.transaction()
    return _tx(tx)

# ================= Chat Page =================
def render_chat_page():
    # 상태 라벨(무료 남은 횟수 + 크레딧)
    free_left = free_remaining_and_reset()
    credits_now = int(st.session_state.get("credits", 0))
    plan_label = TEXT["free"] if free_left > 0 else (TEXT["paid"] if credits_now > 0 else TEXT["free"])
    left_display = free_left if free_left > 0 else credits_now
    st.markdown(f"<div class='status'>{plan_label} — {TEXT['status_left']} {max(left_display,0)}회</div>", unsafe_allow_html=True)

    maybe_show_low_balance_banner()

    # 기존 채팅 기록
    display_chat_history()

    # 입력
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    # 리퍼럴 보너스: 첫 메시지에만
    first_turn = (len([m for m in st.session_state["chat_history"] if m['role']=='user']) == 0)
    maybe_apply_referral_bonus(first_turn)

    # 무료/유료 과금 가드
    usage = int(st.session_state.get("usage_count", 0))
    proceed, used_credit = charge_if_needed(user_input, free_used=usage, free_limit=DAILY_FREE_LIMIT)
    if not proceed:
        st.session_state["show_payment"] = True
        st.rerun()
        return

    # 사용자 메시지 출력
    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

    # 답변
    reply = stream_reply(user_input)
    if reply:
        # 무료분이면 usage+1, 유료 크레딧 사용이면 이미 차감됨
        if not used_credit and usage < DAILY_FREE_LIMIT and not is_crisis(user_input):
            persist_user({"usage_count": usage + 1})

        # 만족도(3번째 사용자 메시지에 1회)
        user_turns = len([m for m in st.session_state["chat_history"] if m["role"]=="user"])
        feedback_3emoji(user_turns)

        # 워터마크/리포트
        render_watermark()
        download_session_report(st.session_state["chat_history"])

        st.rerun()

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(
    f"""
    <div style="margin-top:12px;margin-bottom:16px;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.03);font-size:13px;color:rgba(255,255,255,0.85);">
        🌍 <b>Total {total_visits:,}명</b><br>
        ☀️ <b>Today {daily_visits:,}명</b>
    </div>
    """,
    unsafe_allow_html=True
)

# 대화 기록 지우기
if st.sidebar.button(TEXT["clear_history"]):
    st.session_state["chat_history"] = []
    st.sidebar.success(TEXT["history_cleared"])
    st.rerun()

# 지갑
st.sidebar.markdown(f"### {TEXT['wallet']}")
user_snapshot = db.collection("users").document(USER_ID).get().to_dict() or {}
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
            if str(e) == "INVALID_CODE": st.error(TEXT["voucher_bad"])
            elif str(e) == "ALREADY_USED": st.error(TEXT["voucher_used"])
            else: st.error("충전에 실패했어요. 잠시 후 다시 시도해주세요.")

# 리퍼럴 & 결제안내
sidebar_payment_hint()
sidebar_referral_box()
apply_referral_from_query()

# 관리자: 바우처 생성기
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
with st.sidebar.expander(TEXT["admin_gen"]):
    admin_key = st.text_input("Admin Key", type="password")
    if admin_key and admin_key in ADMIN_KEYS:
        st.session_state.is_admin = True
        st.success("관리자 모드 활성화")
    if st.session_state.is_admin:
        def gen_code(n=10): return uuid.uuid4().hex[:n].upper()
        num = st.number_input("생성 개수", 1, 200, 10)
        credits_each = st.number_input("코드당 크레딧", 1, 2000, CREDIT_PACK_SIZE)
        note = st.text_input("메모(선택)", f"{CREDIT_PACK_SIZE}회/${CREDIT_PACK_PRICE_USD}")
        if st.button(TEXT["admin_make"]):
            out = []
            for _ in range(int(num)):
                c = gen_code()
                create_voucher(c, int(credits_each), note=note)
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

# ================= WOW & Main Render =================
wow_moment_box()
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
