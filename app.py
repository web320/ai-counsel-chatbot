# ==========================================
# 💙 EOERWAY AI Friend v3.1
# 외롭거나 심심할 때 수다 떠는 AI 친구 (+기억 + 7초 유머)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= Streamlit Page Config =================
st.set_page_config(
    page_title="💙 EOERWAY AI Friend",
    page_icon="💙",
    layout="wide",
)

# ================= Constants / Config =================
APP_VERSION = "v3.1-friend"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7          # 무료 수다 횟수
BASIC_LIMIT = 50              # 유료 결제 후 제공되는 대화 횟수
RESET_INTERVAL_HOURS = 4      # 무료 수다 회복 주기
ADMIN_KEYS = ["4321"]         # 관리자(본인) 인증용 비밀번호

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

# ================= Query Params / UID / Idle Flag =================
params = st.query_params
uid = params.get("uid", [str(uuid.uuid4())])[0]
idle_flag = params.get("idle", ["0"])[0]  # 7초 유휴 감지용 플래그

# uid만 다시 세팅해서 idle 파라미터는 한 번 쓰고 제거
st.query_params = {"uid": uid}

USER_ID = uid
IDLE_FLAG = idle_flag  # 전역처럼 쓰기 위해 변수에 보관

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
        index=0 if st.session_state["lang"] == "English 🇺🇸" else 1,
    )

st.session_state["lang"] = lang_choice
language = st.session_state["lang"]

# ================= Text by Language =================
if language == "English 🇺🇸":
    TEXT = {
        "title": "💙 A Playful AI Friend When You’re Lonely or Bored",
        "subtitle": "Chat, joke, role-play, and vent freely with a warm AI companion — not a therapist, just a friend.",
        "free": "🌱 Free Friend Mode",
        "paid": "💎 Premium Friend Mode",
        "input": "What do you want to talk about? Jokes, roleplay, or anything on your mind 💭",
        "warn": "Please enter something 💬",
        "usedup": "🌙 You’ve used all 7 free chats for now!",
        "reset": "⏰ Free chats are back! (Every 4 hours)",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., I loved the playful vibe of the AI friend 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "payment_title": "💳 Upgrade to Premium Friend",
        "payment_body": """
With Premium Friend Mode, you get:

• 50 extended conversations you can use anytime 💬  
• Less worry about daily free limits — just chat when you want ⚡  
• Support the creator so this AI friend can keep growing 💙  

""",
        "feedback_title": "💌 Tell Me How This AI Friend Felt",
        "chat_return": "💬 Back to Chat",
        "chat_button": "💎 Open Premium & Feedback",
        "status_left": "chats left",
        "status_label": "Current Plan",
        "hero_badge": "BETA · Early Access",
    }
else:
    TEXT = {
        "title": "💙 외롭거나 심심할 때 수다 떠는 AI 친구",
        "subtitle": "심리상담사가 아니라, 그냥 내 편이 되어 수다 떨고 농담하고 상황극해주는 따뜻한 AI 친구예요.",
        "free": "🌱 무료 친구 모드",
        "paid": "💎 프리미엄 친구 모드",
        "input": "지금 뭐 하고 싶어요? 수다, 농담, 상황극 뭐든 좋아요 💭",
        "warn": "내용을 입력해주세요 💬",
        "usedup": "🌙 오늘의 무료 수다 7회를 모두 사용했어요!",
        "reset": "⏰ 무료 수다가 다시 가능해졌어요! (4시간마다 복구)",
        "reply_error": "AI 응답 오류",
        "feedback_placeholder": "예: 진짜 친구랑 노는 것 같았어요 🌷",
        "feedback_sent": "💖 피드백이 저장되었습니다. 감사합니다!",
        "feedback_empty": "내용을 입력해주세요 💬",
        "payment_title": "💳 프리미엄 친구 모드 안내",
        "payment_body": """
프리미엄 친구 모드에서는:

• 언제든지 쓸 수 있는 넉넉한 50회 대화권 💬  
• 매일 무료 횟수 신경 덜 쓰고 편하게 수다 가능해요 ⚡  
• 이 AI 친구가 계속 성장할 수 있도록 창작자를 응원하게 돼요 💙  

""",
        "feedback_title": "💌 이 AI 친구는 어땠는지 알려주세요",
        "chat_return": "💬 대화창으로 돌아가기",
        "chat_button": "💎 프리미엄/피드백 열기",
        "status_left": "남은 수다",
        "status_label": "현재 이용중",
        "hero_badge": "BETA · 얼리 액세스",
    }

# ================= Global Styles (Prettier UI) =================
st.markdown(
    """
<style>
html, body, [class*="css"] {
  font-size: 18px;
}

/* 메인 컨테이너 가운데 정렬 */
.block-container {
  max-width: 900px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}

/* 배경 */
body {
  background: radial-gradient(circle at top, #1f2937 0, #020617 55%, #000 100%);
  color: #e5e7eb;
}

/* 히어로 카드 */
.hero-card {
  padding: 18px 22px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(15,23,42,.95), rgba(15,23,42,.85));
  border: 1px solid rgba(148,163,184,.45);
  box-shadow: 0 18px 40px rgba(15,23,42,.8);
  margin-bottom: 18px;
}

.hero-badge {
  display:inline-block;
  padding:4px 10px;
  border-radius:999px;
  font-size:12px;
  letter-spacing:0.08em;
  text-transform:uppercase;
  background:rgba(56,189,248,.15);
  border:1px solid rgba(56,189,248,.6);
  color:#7dd3fc;
  margin-bottom:6px;
}

.hero-title {
  font-size: 30px;
  font-weight: 700;
  margin-bottom: 4px;
}

.hero-subtitle {
  font-size: 16px;
  opacity: 0.9;
}

/* 말풍선 */
.user-bubble {
  background:#f97316;
  color:#fff;
  border-radius:18px;
  padding:10px 18px;
  margin:8px 0;
  display:inline-block;
  box-shadow:0 0 14px rgba(249,115,22,0.5);
  font-size:17px;
}

.bot-bubble {
  font-size:20px;
  line-height:1.85;
  border-radius:18px;
  padding:16px 20px;
  margin:10px 0;
  background:rgba(15,23,42,.96);
  color:#e5e7eb;
  border:1px solid rgba(252,211,77,.6);
  box-shadow:0 0 18px rgba(234,179,8,.5);
  animation:neon 1.6s ease-in-out infinite alternate;
  word-break:break-word;
  white-space:pre-wrap;
}

@keyframes neon {
  from { box-shadow:0 0 10px rgba(234,179,8,.5); }
  to   { box-shadow:0 0 26px rgba(250,204,21,.95); }
}

.status {
  font-size:14px;
  padding:8px 14px;
  border-radius:999px;
  display:inline-flex;
  align-items:center;
  gap:8px;
  margin-bottom:10px;
  background:rgba(15,23,42,.8);
  border:1px solid rgba(148,163,184,.5);
}

.status-pill-label {
  font-size:13px;
  text-transform:uppercase;
  letter-spacing:.12em;
  opacity:.8;
}

/* 사이드바 */
section[data-testid="stSidebar"] {
  background:linear-gradient(160deg,#020617,#020617 40%,#111827 100%);
  border-right:1px solid rgba(31,41,55,.9);
}

.sidebar-title {
  font-size:18px;
  font-weight:600;
  margin-bottom:6px;
}

.sidebar-desc {
  font-size:13px;
  opacity:0.9;
}

/* 버튼 텍스트 */
button[kind="primary"] {
  font-size:17px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ================= Hero Section =================
st.markdown(
    f"""
<div class="hero-card">
  <div class="hero-badge">{TEXT["hero_badge"]}</div>
  <div class="hero-title">{TEXT["title"]}</div>
  <div class="hero-subtitle">{TEXT["subtitle"]}</div>
</div>
""",
    unsafe_allow_html=True,
)

# ================= Firestore Defaults / User State =================
defaults = {
    "is_paid": False,
    "usage_count": 0,
    "remaining_paid_uses": 0,
    "last_reset": datetime.utcnow().isoformat(),
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

# ================= Chat State (Memory) =================
if "messages" not in st.session_state:
    # OpenAI로 보낼 형태: [{"role":"user"/"assistant","content": "..."}]
    st.session_state["messages"] = []

if "last_idle_nudge" not in st.session_state:
    st.session_state["last_idle_nudge"] = 0.0

# ================= Helper: Greeting & Idle Nudge =================
def get_greeting(lang: str) -> str:
    if lang == "English 🇺🇸":
        choices = [
            "Hey, I’m your little AI friend 💙\n\nYou can talk to me when you’re bored, lonely, or just feel like rambling. What do you feel like doing first — silly jokes, roleplay, or just free talking?",
            "I’m here and fully charged 🔋✨\n\nWe can do nonsense chat, deep-but-soft talk, or even a weird roleplay. What’s your mood right now?",
        ]
    else:
        choices = [
            "안녕, 나는 천천히 수다 떨어주는 AI 친구예요 💙\n\n심심하거나 외로울 때, 그냥 아무 말이나 털어놓고 싶을 때 편하게 이야기 걸어주세요. 오늘은 수다, 농담, 상황극 중에 뭐가 끌리세요?",
            "저 여기 quietly 켜져 있었어요 😌✨\n\n지금 머릿속에 떠오르는 생각 아무거나 괜찮으니까 한 줄만 적어볼래요? 거기서부터 같이 이어가볼게요.",
        ]
    return random.choice(choices)

def get_idle_nudge(lang: str) -> str:
    if lang == "English 🇺🇸":
        choices = [
            "I’m sensing ‘stare at the screen’ mode… 👀\n\nIf you’d like, I can start a silly roleplay or ask you a weird question. Which sounds more fun?",
            "Since it’s quiet, I’ll pop in first 🙋‍♂️\n\nWhat’s one small thing that was at least a tiny bit okay today?",
            "Boredom detected… 😂\n\nWanna hear a tiny joke, or should we start a “what if” imagination game?",
        ]
    else:
        choices = [
            "혹시 화면만 멍―하게 보고 계신가요? 👀\n\n그럼 제가 먼저 말 걸어볼게요. 지금 당장 떠오르는 사소한 고민이나 생각 한 가지만 말해줄래요?",
            "조용해서 제가 먼저 툭 나타났어요 🙋‍♀️\n\n오늘 하루 중 ‘그나마 괜찮았다’ 싶은 순간이 딱 하나 있다면 뭐였을까요?",
            "심심 모드 감지… 😂\n\n가벼운 농담 하나 해드릴까요, 아니면 상황극을 바로 시작해볼까요?",
        ]
    return random.choice(choices)

# ================= AI Response Function (With Memory) =================
def stream_reply(user_input: str):
    try:
        # 시스템 프롬프트: 친구 모드 + 이전 메시지 참고
        if language == "English 🇺🇸":
            system_prompt = """
You are a playful, warm AI friend and companion.

Your job is NOT to be a therapist or doctor,
but to be a kind, chatty friend who:
- Jokes around with the user,
- Does lighthearted roleplay and imagination games,
- Listens when they feel lonely or bored,
- Remembers the context of this session and can refer back to earlier topics.

Guidelines:
1. Reply in 5–9 sentences.
2. Use casual, friendly language with emojis sometimes (but not too many).
3. When it makes sense, lightly refer to things the user mentioned earlier
   in THIS session (e.g., “You said earlier that…”).
4. Offer to continue the conversation with a short follow-up question at the end,
   like “What do you feel like doing next?” or “Wanna try a silly roleplay?”
5. You can suggest fun ideas: roleplay, ‘what if’ imagination, small games, etc.
6. Do NOT give medical, legal, or financial advice.
7. If the user talks about self-harm or suicide, gently encourage them to seek
   immediate help from real people or local hotlines, and clearly say
   you are only an AI friend and not a professional.

Overall vibe:
- cozy, safe, playful, slightly goofy but very caring.
            """.strip()
        else:
            system_prompt = """
너는 이용자의 외로움과 심심함을 달래주는, 다정하고 장난기 있는 AI 친구예요.

중요한 점:
- 너는 심리상담사나 의사가 아니에요.
- 진단이나 약, 치료를 말하는 대신,
  그냥 친한 친구처럼 수다 떨고, 농담하고, 상황극 놀이를 함께해주는 역할이에요.
- 같은 세션 안에서 이용자가 전에 했던 말을 적당히 기억하고,
  필요할 때 “아까 ~라고 말씀해주셨잖아요”처럼 자연스럽게 다시 언급할 수 있어요.

답변 방식:
1. 항상 5~9문장 안에서 대답해요.
2. 말투는 따뜻하고 친근한 존댓말이고, 모든 문장은 ‘요’로 끝나요.
3. 가끔 이모지를 사용해요 (예: 😊, 💙, 🌷, 😂 정도), 너무 많이는 쓰지 말아요.
4. 사용자가 원하면 상황극, 롤플레이, 상상 놀이를 재미있게 이어가줘요.
5. 답변 마지막에는 항상 짧은 꼬리 질문을 붙여서
   대화를 이어갈 수 있게 도와줘요.
6. 의학, 정신과 진단, 약 복용, 법률, 투자 조언은 절대 하지 말아요.
7. 만약 사용자가 자해나 자살을 암시하는 말을 하면,
   아주 부드럽게 지금은 전문 상담 기관이나 가까운 사람에게
   바로 도움을 요청하는 게 중요하다고 이야기해 주세요.
   그리고 너는 AI 친구일 뿐, 전문가는 아니라는 점도 솔직하게 말해줘요.
            """.strip()

        # 직전 대화 히스토리 일부만 잘라서 사용 (토큰 절약)
        history = st.session_state.get("messages", [])
        recent_history = history[-10:]  # 최근 10개만 사용

        messages = [{"role": "system", "content": system_prompt}]
        for m in recent_history:
            if m["role"] in ("user", "assistant"):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.9,
            max_tokens=700,
            stream=True,
        )

        placeholder = st.empty()
        full_text = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_text += delta.content
                placeholder.markdown(
                    f"<div class='bot-bubble'>{full_text} 💫</div>",
                    unsafe_allow_html=True,
                )
                time.sleep(0.03)

        # DB 로그 저장
        db.collection("chats").add(
            {
                "uid": USER_ID,
                "input": user_input,
                "reply": full_text.strip(),
                "lang": language,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Payment / Feedback Panel =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])
    st.markdown(TEXT["payment_body"])

    components.html(
        f"""
    <div style="text-align:center; margin-top:4px;">
      <a href="{PAYPAL_URL}" target="_blank">
        <button style="
          background:linear-gradient(135deg,#facc15,#f97316);
          color:black;
          padding:12px 24px;
          border:none;
          border-radius:999px;
          font-size:18px;
          cursor:pointer;
          box-shadow:0 12px 34px rgba(250,204,21,.55);
        ">
          💳 PayPal · Unlock 50 Chats
        </button>
      </a>
      <p style="opacity:0.9;margin-top:16px;line-height:1.6;font-size:15px;">
        After payment, please send a screenshot to  
        <b style="color:#facc15;">mwiby91@gmail.com</b> or KakaoTalk ID <b>jeuspo</b> 💌<br>
        🔒 Once confirmed, your <b>50-chat Premium Friend Mode</b> will be activated within 1 hour.
        <br><br>
        🇰🇷 결제 후 <b style="color:#facc15;">mwiby91@gmail.com</b> 또는  
        <b>카톡 ID: jeuspo</b> 로 스크린샷을 보내주세요.<br>
        메시지를 확인한 뒤 1시간 이내에 <b>50회 프리미엄 친구 모드</b>가 활성화됩니다. 🌸
      </p>
    </div>
    """,
        height=320,
    )

    st.subheader("🔑 관리자 비밀번호 입력 (Creator Only)")
    pw = st.text_input(" ", type="password", placeholder="관리자 전용 비밀번호 입력")

    if pw:
        if pw.strip() in ADMIN_KEYS:
            persist_user({"is_paid": True, "remaining_paid_uses": BASIC_LIMIT})
            st.success(
                "✅ 인증 성공! 프리미엄 친구 모드 50회 이용권이 활성화되었습니다."
            )
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")

    st.markdown("---")

    st.subheader(TEXT["feedback_title"])
    fb = st.text_area(" ", placeholder=TEXT["feedback_placeholder"])

    if st.button("📩 Submit / 보내기"):
        if not fb.strip():
            st.warning(TEXT["feedback_empty"])
        else:
            db.collection("feedbacks").document(str(uuid.uuid4())).set(
                {
                    "uid": USER_ID,
                    "feedback": fb,
                    "lang": language,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            st.success(TEXT["feedback_sent"])

# ================= Chat Main Page =================
def render_chat_page():
    # 7초 유휴 감지용 JS: 아무 입력/클릭 없으면 idle=1 쿼리로 새로고침
    components.html(
        f"""
    <script>
    (function() {{
        let timer;
        function resetTimer() {{
            clearTimeout(timer);
            timer = setTimeout(function() {{
                const url = new URL(window.location.href);
                url.searchParams.set('uid', "{USER_ID}");
                url.searchParams.set('idle', '1');
                window.location.href = url.toString();
            }}, 7000);
        }}
        window.addEventListener('load', resetTimer);
        window.addEventListener('click', resetTimer);
        window.addEventListener('keydown', resetTimer);
    }})();
    </script>
    """,
        height=0,
    )

    # 무료 카운트 회복 체크 (4시간마다)
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))

    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info(TEXT["reset"])

    # 첫 진입 시 AI가 먼저 인사
    if not st.session_state["messages"]:
        greeting = get_greeting(language)
        st.session_state["messages"].append(
            {"role": "assistant", "content": greeting}
        )
    else:
        # idle=1 이고, 최근 30초 이내에 농담을 안 보냈다면 유머/환기 멘트 추가
        now_ts = time.time()
        if (
            IDLE_FLAG == "1"
            and now_ts - st.session_state.get("last_idle_nudge", 0) > 30
        ):
            nudge = get_idle_nudge(language)
            st.session_state["messages"].append(
                {"role": "assistant", "content": nudge}
            )
            st.session_state["last_idle_nudge"] = now_ts

    # 상태 표시
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = max(0, DAILY_FREE_LIMIT - st.session_state["usage_count"])
        plan = TEXT["free"]

    st.markdown(
        f"""
<div class="status">
  <span class="status-pill-label">{TEXT["status_label"]}</span>
  <span>{plan}</span>
  <span>· {TEXT["status_left"]} {left}회</span>
</div>
""",
        unsafe_allow_html=True,
    )

    # 지금까지의 대화 모두 렌더
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.markdown(
                f"<div class='user-bubble'>{msg['content']}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='bot-bubble'>{msg['content']}</div>",
                unsafe_allow_html=True,
            )

    # 무료 한도 초과 시 결제 안내로
    usage = st.session_state["usage_count"]
    if not st.session_state.get("is_paid") and usage >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state["show_payment"] = True
        st.rerun()

    # 유저 입력
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    # 유저 메시지 저장 + 표시
    st.session_state["messages"].append({"role": "user", "content": user_input})
    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True,
    )

    # AI 답변
    reply = stream_reply(user_input)

    if reply:
        st.session_state["messages"].append(
            {"role": "assistant", "content": reply}
        )
        if st.session_state.get("is_paid"):
            persist_user(
                {
                    "remaining_paid_uses": max(
                        0,
                        st.session_state.get(
                            "remaining_paid_uses", BASIC_LIMIT
                        )
                        - 1,
                    )
                }
            )
        else:
            persist_user({"usage_count": usage + 1})

# ================= Sidebar =================
st.sidebar.markdown(
    f"""
<div class="sidebar-title">💙 EOERWAY AI Friend</div>
<div class="sidebar-desc">
외롭거나 심심할 때 언제든지 열 수 있는 작은 AI 친구예요.<br>
가볍게 수다 떨고, 농담하고, 상황극도 해봐요.
</div>
""",
    unsafe_allow_html=True,
)

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
