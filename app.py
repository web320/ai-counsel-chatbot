# ==========================================
# 💙 EOERWAY AI Therapy v6.0-Loyal
# (Retention + Safety + Monetization Optimized)
# ==========================================

import os, uuid, json, time, random, re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------------
# 🌐 Basic App Config
# ---------------------------------
st.set_page_config(
    page_title="💙 EOERWAY AI Therapy",
    layout="wide"
)

load_dotenv()

APP_VERSION = "v6.0-Loyal"
DAILY_FREE_LIMIT = 7          # 무료 상담 가능 횟수
BASIC_LIMIT = 50              # 유료(프리미엄) 남은 상담 횟수
RESET_INTERVAL_HOURS = 4      # 무료 상담 회복 주기
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
ADMIN_KEYS = ["4321"]         # 관리용 비밀번호

# ---------------------------------
# 🔐 OpenAI init
# ---------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------
# 🔥 Firebase init
# ---------------------------------
def _firebase_config():
    raw = st.secrets.get("firebase")
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw)

if not firebase_admin._apps:
    cred = credentials.Certificate(_firebase_config())
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------------
# 🧍 User Session (anonymous uid)
# ---------------------------------
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ---------------------------------
# 📢 ads.txt endpoint for AdSense
# ---------------------------------
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ---------------------------------
# 🎨 CSS
# ---------------------------------
st.markdown("""
<style>
html, body, [class*="css"] { font-size:18px; }

.user-bubble {
  background:#b91c1c;
  color:#fff;
  border-radius:14px;
  padding:10px 18px;
  margin:8px 0 4px 0;
  display:inline-block;
  box-shadow:0 0 10px rgba(255,0,0,0.3);
  max-width:90%;
  word-break:break-word;
}

.bot-bubble {
  font-size:20px;
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

.status-chip {
  font-size:15px;
  padding:8px 12px;
  border-radius:10px;
  display:inline-block;
  margin-bottom:8px;
  background:rgba(255,255,255,.06);
}

.emobar-wrap {
  margin-top:6px;
  width:100%;
  max-width:340px;
  background:#222;
  border-radius:10px;
  border:1px solid rgba(255,255,255,0.1);
  padding:8px 12px;
  color:#fff;
  font-size:15px;
  line-height:1.4;
}

.emobar-bar {
  height:10px;
  border-radius:6px;
  margin-top:6px;
  box-shadow:0 0 8px rgba(255,255,255,.4);
}

.history-box {
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:12px;
  padding:12px 16px;
  font-size:14px;
  line-height:1.5;
  max-height:250px;
  overflow-y:auto;
}

.history-item-me {
  color:#ffcccc;
  margin-bottom:6px;
  font-weight:500;
}

.history-item-ai {
  color:#fff;
  opacity:0.8;
  margin-bottom:12px;
  font-style:italic;
}

.panic-box {
  background:#2b0000;
  border:1px solid #ff4d4d;
  color:#fff;
  border-radius:12px;
  padding:16px;
  font-size:16px;
  line-height:1.6;
  box-shadow:0 0 12px rgba(255,0,0,.5);
  margin-top:12px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------
# 🧠 Firestore defaults / state
# ---------------------------------
defaults = {
    "is_paid": False,
    "usage_count": 0,
    "remaining_paid_uses": 0,
    "last_reset": datetime.utcnow().isoformat()
}

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data_from_db = snap.to_dict() or {}
    merged = {}
    for k, v in defaults.items():
        merged[k] = data_from_db.get(k, v)
    st.session_state.update(merged)
else:
    user_ref.set(defaults)
    st.session_state.update(defaults)

def persist_user(fields: dict):
    user_ref.set(fields, merge=True)
    st.session_state.update(fields)

# ---------------------------------
# 💬 Helper: language detection (simple heuristic)
# ---------------------------------
def detect_language_simple(text: str) -> str:
    # 매우 단순한 감지. 외부 번역 라이브러리 없이 동작
    if re.search(r"[가-힣]", text):
        return "ko"
    return "en"

# ---------------------------------
# 💗 Helper: emotion scoring + visual bar
# ---------------------------------
def emotion_score_block(text: str):
    sad_words = ["힘들", "지쳤", "무기력", "그만", "포기", "울고", "lonely", "tired", "empty", "sad", "worthless"]
    good_words = ["고마", "소중", "괜찮", "편안", "사랑", "appreciate", "grateful", "loved", "hope", "better"]

    sad_count = sum(text.lower().count(w.lower()) for w in sad_words)
    good_count = sum(text.lower().count(w.lower()) for w in good_words)

    # 기본값 50에서 감정 방향을 반영
    raw = 50 + (good_count * 10) - (sad_count * 10)
    score = max(0, min(100, raw))

    if score < 30:
        emoji = "💔"
        bar_color = "linear-gradient(90deg,#550000,#ff0033)"
        msg = "마음이 많이 무너진 상태에 가까워 보여요"
    elif score < 60:
        emoji = "🌙"
        bar_color = "linear-gradient(90deg,#332244,#8844ff)"
        msg = "지치고 예민해져 있는 순간일 수 있어요"
    else:
        emoji = "🌤️"
        bar_color = "linear-gradient(90deg,#00a86b,#b6ff66)"
        msg = "조금 숨 쉴 틈이 보이기 시작하고 있어요"

    return {
        "score": int(score),
        "emoji": emoji,
        "desc": msg,
        "bar_color": bar_color
    }

def render_emotion_block(result: dict):
    st.markdown(
        f"""
        <div class="emobar-wrap">
            <div><b>{result['emoji']} Emotion Status:</b> {result['desc']}</div>
            <div style="font-size:13px;opacity:.7;">Score: {result['score']} / 100</div>
            <div class="emobar-bar" style="width:{result['score']}%; background:{result['bar_color']};"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------
# 🚨 Crisis safety check
# ---------------------------------
def crisis_detect(text: str) -> bool:
    crisis_keywords = [
        "죽고 싶", "자살", "끝내고 싶", "살기 싫", "그만 살", "kill myself",
        "end it all", "suicide", "i don't want to live"
    ]
    for k in crisis_keywords:
        if k.lower() in text.lower():
            return True
    return False

def render_crisis_box(lang: str):
    if lang == "ko":
        st.markdown(
            """
            <div class="panic-box">
            지금 이 순간이 너무 벅차고, 정말로 혼자 못 버티겠다는 생각이 드신다면  
            지금 바로 도움을 받을 수 있는 안전한 창구가 있어요요.  
            한국에서는 24시간 가능한 자살 예방 상담전화 1393으로 전화하실 수 있어요요.  
            완전히 익명이고, 그냥 “저 좀 힘들어요”라고만 말해도 괜찮아요요.  
            혼자 견디지 않으셔도 괜찮아요요. 지금 이 순간 당신은 혼자가 아니예요요.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="panic-box">
            If you're feeling like you might hurt yourself or you can’t hold on alone,  
            you deserve immediate real human support right now.  
            Please reach out to your local crisis hotline or emergency services.  
            You are not a burden. You are worth staying.
            </div>
            """,
            unsafe_allow_html=True
        )

# ---------------------------------
# 🧠 Core counselor reply builder (OpenAI)
# ---------------------------------
def counselor_reply(user_text: str, lang: str) -> str:
    """
    lang == 'ko' -> 한국어 존댓말, 모든 문장 '요'로 끝나도록 요청
    lang == 'en' -> 부드러운 영어 톤
    OpenAI 호출 실패 시 fallback 답변 리턴
    """

    if lang == "ko":
        system_style = (
            "너는 마음이 매우 따뜻하고 공감 능력이 뛰어난 전문 심리 상담사예요.\n"
            "항상 존댓말을 쓰고 모든 문장은 반드시 '요'로 끝나요.\n"
            "반드시 6~9문장 안에서 대답해요.\n\n"
            "답변 구조는 항상 다음 네 가지 흐름을 모두 포함해야 해요:\n"
            "1) 부드러운 첫 인사와 안전감 주기 ('이렇게 솔직하게 말해주셔서 고마워요' 같은 식으로 시작해요)\n"
            "2) 사용자의 감정을 정확히 짚고 '그건 이상한 반응이 아니예요'라고 정상화해요\n"
            "3) 지금 바로 할 수 있는 아주 작은 안정 행동을 조심스럽게 제안해요 (예: '혹시 괜찮다면 어깨 힘을 조금만 풀어볼까요' 같이)\n"
            "4) 그 사람이 이미 충분히 잘 버티고 있고 가치 있는 존재라는 걸 진심으로 상기시켜줘요\n\n"
            "절대 의료적 조언이나 약물 언급, 진단명 언급은 하지 말아요.\n"
            "지금 사용자를 비난하거나 분석하지 말아요. 그냥 옆에서 같이 있는 사람처럼 말해요.\n"
        )
    else:
        system_style = (
            "You are a deeply gentle, emotionally safe, nonjudgmental mental health companion.\n"
            "Speak in warm, human, soft English. 6-9 sentences total.\n\n"
            "Your structure must always include:\n"
            "1) Thank them for sharing and make them feel safe.\n"
            "2) Name/validate their feelings and say it's understandable.\n"
            "3) Offer one tiny grounding or soothing action they can try right now (breathing, relaxing shoulders).\n"
            "4) Remind them they have worth, and that reaching out is already strength.\n\n"
            "Do NOT give medical or medication advice. Do NOT diagnose.\n"
            "Never judge or pressure. Be calm and reassuring.\n"
        )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_style},
                {"role": "user", "content": user_text},
            ],
            temperature=0.8,
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        if lang == "ko":
            return (
                "지금 마음을 이렇게 털어놔준 것만으로도 정말 큰 용기예요요. "
                "지금 순간을 혼자 버티는 게 얼마나 힘들 수 있는지 저는 이해하고 싶어요요. "
                "어깨랑 턱에 들어간 힘을 살짝만 풀고 천천히 길게 들이쉬고 내쉬는 숨을 세 번 해볼까요요. "
                "당신은 이미 무너지고 싶은 순간에도 계속 버티고 있는 분이예요요. "
                "그건 약한 게 아니라 정말 강한 거예요요."
            )
        else:
            return (
                "Thank you for opening up right now. You're not alone here. "
                "If your body is tight, try loosening your jaw and shoulders and take one slow breath in, then let it out longer than you took it in. "
                "You are already doing something strong by talking about this. "
                "You deserve kindness, especially from yourself."
            )

# ---------------------------------
# 📜 Recent chat history (for trust / retention)
# ---------------------------------
def get_recent_history(uid: str, limit: int = 10):
    # 최신순으로 limit개 가져와서 시간순 정렬로 다시 보여줌
    docs = (
        db.collection("chats")
        .where("uid", "==", uid)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    items = []
    for d in docs:
        obj = d.to_dict()
        items.append(obj)
    # 다시 오래된 것부터 출력되도록 reverse
    items.reverse()
    return items

def render_history_box(items):
    if not items:
        st.write("아직 대화 기록이 없어요. 지금 마음을 처음으로 들려주고 있어요 🌷")
        return
    st.markdown("<div class='history-box'>", unsafe_allow_html=True)
    for c in items:
        user_txt = c.get("input", "")
        bot_txt  = c.get("reply", "")
        st.markdown(f"<div class='history-item-me'>🙋‍♀️ {user_txt}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='history-item-ai'>💙 {bot_txt}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------
# 🧾 Load usage state / reset logic
# ---------------------------------
def ensure_reset_window():
    now = datetime.utcnow()
    last_reset_raw = st.session_state.get("last_reset")
    try:
        last_reset_dt = datetime.fromisoformat(last_reset_raw)
    except Exception:
        last_reset_dt = now
        persist_user({"last_reset": now.isoformat()})

    hours_passed = (now - last_reset_dt).total_seconds() / 3600
    if hours_passed >= RESET_INTERVAL_HOURS:
        # reset free usage counter
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info("⏰ 무료 상담 기회가 새로 충전되었어요 (4시간마다 복구돼요).")

ensure_reset_window()

# ---------------------------------
# 🏷 Status chip (plan / remaining)
# ---------------------------------
if st.session_state.get("is_paid"):
    plan_label = "💎 Premium User"
    left_count = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
else:
    plan_label = "🌱 Free Trial"
    left_count = DAILY_FREE_LIMIT - st.session_state["usage_count"]

st.markdown(
    f"<div class='status-chip'>{plan_label} — Remaining {max(left_count,0)} chats</div>",
    unsafe_allow_html=True
)

# ---------------------------------
# 📂 Sidebar: recent chat history + manual premium unlock
# ---------------------------------
with st.sidebar:
    st.markdown("### 📜 Your Comfort Record")
    render_history_box(get_recent_history(USER_ID, limit=10))

    st.markdown("---")
    st.markdown("### 💎 Premium Access (Manual)")
    st.caption("이미 결제하셨다면 아래 코드를 입력해 주세요.")
    pw = st.text_input("관리자 / 결제 확인 코드", type="password")
    if pw:
        if pw.strip() in ADMIN_KEYS:
            persist_user({
                "is_paid": True,
                "remaining_paid_uses": BASIC_LIMIT
            })
            st.success("프리미엄이 활성화되었어요. 50회 상담 가능해요 💎")
        else:
            st.error("코드가 맞지 않아요.")

    st.markdown("---")
    st.markdown("#### 💖 Upgrade & Support")
    st.write(
        f"• PayPal로 3달러 결제 후\n"
        f"  스크린샷을 `mwiby91@gmail.com` 또는 카카오 `jeuspo` 로 보내주세요.\n\n"
        f"• 확인되면 50회 이용권이 바로 열려요."
    )
    st.markdown(f"[💳 PayPal 결제 바로가기]({PAYPAL_URL})")

# ---------------------------------
# 🧊 If out of free usage → stop and upsell
# ---------------------------------
if (not st.session_state.get("is_paid")) and (st.session_state["usage_count"] >= DAILY_FREE_LIMIT):
    st.warning(
        "🌙 오늘의 무료 상담 7회를 모두 사용하셨어요.\n\n"
        "지금은 마음이 많이 무거울 수도 있어요. 쉬어가는 것도 정말 괜찮아요.\n\n"
        "조금 더 깊이 이야기하고 싶다면 프리미엄으로 전환하실 수 있어요 💎"
    )
    st.stop()

# ---------------------------------
# 📝 Main Chat Input
# ---------------------------------
st.title("🫧 Tell me what's on your mind")
st.caption("당신 얘기를 안전하게 들어줄 따뜻한 공간이에요. 익명이고, 판단하지 않아요.")

user_input = st.chat_input("지금 어떤 기분인지 편하게 적어주세요 / Type anything you're feeling 💬")
if not user_input:
    st.stop()

# 사용자 말풍선 먼저 출력
st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

# ---------------------------------
# ❤️ Emotion Block
# ---------------------------------
emo_info = emotion_score_block(user_input)
render_emotion_block(emo_info)

# ---------------------------------
# 🧠 Generate AI reply (personalized by language style)
# ---------------------------------
lang = detect_language_simple(user_input)
reply_text = counselor_reply(user_input, lang)

# AI 말풍선 출력
st.markdown(f"<div class='bot-bubble'>{reply_text} 💫</div>", unsafe_allow_html=True)

# ---------------------------------
# 🚨 Crisis box if needed
# ---------------------------------
if crisis_detect(user_input):
    render_crisis_box(lang)

# ---------------------------------
# 🗃 Save chat & usage
# ---------------------------------
now_iso = datetime.utcnow().isoformat()

db.collection("chats").add({
    "uid": USER_ID,
    "input": user_input,
    "reply": reply_text,
    "lang": lang,
    "emotion_score": emo_info["score"],
    "created_at": now_iso
})

# 감정 기록 별도 저장 (향후 감정 타임라인 / 리텐션 분석 가능)
db.collection("emotions").add({
    "uid": USER_ID,
    "score": emo_info["score"],
    "tag": emo_info["emoji"],
    "time": now_iso,
    "raw": user_input[:500]
})

# 사용량 차감
if st.session_state.get("is_paid"):
    persist_user({
        "remaining_paid_uses": max(
            0,
            st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1
        )
    })
else:
    persist_user({"usage_count": st.session_state["usage_count"] + 1})

# ---------------------------------
# 🌷 Gentle footer affirmations
# ---------------------------------
st.markdown("---")
if lang == "ko":
    st.markdown(
        f"""
        <div style='text-align:center;opacity:0.9;color:#fff;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;'>
        오늘 이렇게 마음을 표현했다는 건 이미 무너지는 대신 나를 지키려고 했다는 뜻이예요요.<br>
        그건 약함이 아니라 엄청난 강함이예요요.<br><br>
        버티고 있는 당신은 소중한 사람이예요요.
        <br><br>
        <small>EOERWAY v{APP_VERSION} • Built with 💙 Streamlit + OpenAI</small>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"""
        <div style='text-align:center;opacity:0.9;color:#fff;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;'>
        The fact that you reached out means you chose care instead of disappearing.<br>
        That's not weakness — that's real strength.<br><br>
        You matter more than you think.
        <br><br>
        <small>EOERWAY v{APP_VERSION} • Built with 💙 Streamlit + OpenAI</small>
        </div>
        """,
        unsafe_allow_html=True
    )

