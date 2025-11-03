# ==========================================
# 💙 EOERWAY Simple Friend Chat v1.0
# 심심할 때 수다 떠는 AI 친구 (순수 채팅 버전)
# ==========================================

import os, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# ---------------------------
# BASIC CONFIG
# ---------------------------
st.set_page_config(
    page_title="💙 EOERWAY AI Friend Chat",
    page_icon="💙",
    layout="wide",
)

APP_VERSION = "friend-chat-v1.0"

# ---------------------------
# LOAD OPENAI
# ---------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY가 설정되지 않았어요. Streamlit secrets 또는 .env를 확인해 주세요.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# LANGUAGE TOGGLE
# ---------------------------
if "lang" not in st.session_state:
    st.session_state["lang"] = "한국어 🇰🇷"

col1, col2 = st.columns([5, 1])
with col2:
    lang_choice = st.radio(
        " ",
        ["한국어 🇰🇷", "English 🇺🇸"],
        horizontal=True,
        label_visibility="collapsed",
        index=0 if st.session_state["lang"] == "한국어 🇰🇷" else 1,
    )

st.session_state["lang"] = lang_choice
language = st.session_state["lang"]

# ---------------------------
# TEXT BY LANGUAGE
# ---------------------------
if language == "English 🇺🇸":
    TEXT = {
        "title": "💙 A Tiny AI Friend When You’re Bored",
        "subtitle": "Not a therapist, just a cozy AI buddy for chatting, jokes, and silly roleplay.",
        "input": "What do you feel like talking about right now? 💭",
        "empty_warn": "Type something to chat 💬",
        "system_hint": "You can talk about anything: boredom, random thoughts, jokes, small worries, or roleplay ideas.",
    }
else:
    TEXT = {
        "title": "💙 심심할 때 수다 떠는 작은 AI 친구",
        "subtitle": "심리상담사가 아니라, 그냥 가볍게 수다·농담·상황극 해주는 편한 친구예요.",
        "input": "지금 뭐에 대해 이야기하고 싶어요? 아무 말이나 괜찮아요 💭",
        "empty_warn": "대화를 위해 한 줄만 적어줘도 좋아요 💬",
        "system_hint": "심심함, 오늘 있었던 일, 작은 고민, 농담, 상황극 아이디어까지 뭐든 편하게 이야기해도 돼요.",
    }

# ---------------------------
# GLOBAL STYLE
# ---------------------------
st.markdown(
    """
<style>
html, body, [class*="css"] {
  font-size: 18px;
}
.block-container {
  max-width: 900px;
  padding-top: 2rem;
  padding-bottom: 3rem;
}
body {
  background: radial-gradient(circle at top, #1f2937 0, #020617 55%, #000 100%);
  color: #e5e7eb;
}
.hero-card {
  padding: 18px 22px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(15,23,42,.95), rgba(15,23,42,.85));
  border: 1px solid rgba(148,163,184,.45);
  box-shadow: 0 18px 40px rgba(15,23,42,.8);
  margin-bottom: 18px;
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
  line-height:1.9;
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
.small-hint {
  font-size:13px;
  opacity:0.8;
  margin-bottom:6px;
}
.version-tag {
  font-size:12px;
  opacity:0.6;
  margin-top:4px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------
# HERO
# ---------------------------
st.markdown(
    f"""
<div class="hero-card">
  <div class="hero-title">{TEXT["title"]}</div>
  <div class="hero-subtitle">{TEXT["subtitle"]}</div>
  <div class="version-tag">EOERWAY · {APP_VERSION}</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"<div class='small-hint'>{TEXT['system_hint']}</div>",
    unsafe_allow_html=True,
)

# ---------------------------
# SESSION STATE (CHAT)
# ---------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []  # [{"role": "user"/"assistant", "content": str}, ...]

# 처음 들어왔을 때 한 번만 인사
if not st.session_state["messages"]:
    if language == "English 🇺🇸":
        greeting = (
            "Hey, I’m your small AI friend 💙\n\n"
            "You can just dump your thoughts here when you’re bored, lonely, or want a silly conversation. "
            "What kind of mood are you in right now?"
        )
    else:
        greeting = (
            "안녕, 나는 네가 심심할 때 편하게 이야기 걸 수 있는 AI 친구예요 💙\n\n"
            "오늘 있었던 일, 아무 의미 없는 생각, 농담, 상황극… 뭐든지 좋아요. "
            "지금 마음 상태를 한 단어로 표현하면 어떤 느낌인지부터 말해볼까요?"
        )
    st.session_state["messages"].append({"role": "assistant", "content": greeting})

# ---------------------------
# SYSTEM PROMPT
# ---------------------------
def get_system_prompt(lang: str) -> str:
    if lang == "English 🇺🇸":
        return """
You are a playful, warm AI friend.

You are NOT a therapist or doctor.
You are just a cozy chat buddy for when the user is:
- bored
- lonely
- wants to joke around
- wants to do light roleplay
- wants to talk about small worries in a gentle way.

Rules:
1. Reply in about 7–11 sentences, like a small story bubble.
2. Use casual, friendly language and a few emojis (not too many).
3. Keep everything light and kind. You can be a bit silly, but never mean.
4. Sometimes refer back to earlier messages in this session
   (“you said earlier that…”), so it feels like you remember.
5. At the end of each reply, ask a tiny follow-up question so the chat can continue.
6. Do not give medical, legal, or financial advice.
7. If the user talks about self-harm or suicide, gently say that you are only
   an AI friend, not a professional, and encourage them to seek real-world help
   or hotlines.

Tone:
- cozy, safe, playful, caring, like a friend on Discord/DM.
""".strip()
    else:
        return """
너는 이용자가 심심하거나 외로울 때 편하게 말을 걸 수 있는, 다정하고 장난기 있는 AI 친구예요.

중요한 점:
- 너는 심리상담사나 의사가 아니에요.
- 진단, 약, 치료 이야기는 하지 말고,
  그냥 친한 친구처럼 수다, 농담, 가벼운 고민 나눔, 상황극을 함께해줘요.

규칙:
1. 항상 7~11문장 정도로 대답해서, 하나의 짧은 이야기처럼 느껴지게 해줘요.
2. 말투는 따뜻하고 친근한 존댓말이고, 모든 문장은 ‘요’로 끝나요.
3. 가끔만 이모지를 사용해요 (예: 😊, 💙, 🌷, 😂) 너무 많이 쓰지는 말아요.
4. 같은 세션 안에서 이용자가 전에 말한 내용을 적당히 기억해서,
   필요하면 “아까 ~라고 해주셨잖아요”처럼 자연스럽게 다시 언급해요.
5. 답변 마지막에는 항상 짧은 꼬리 질문을 붙여서
   대화를 이어갈 수 있게 도와줘요.
6. 의학, 정신과 진단, 약 복용, 법률, 투자 조언은 절대 하지 말아요.
7. 만약 자해나 자살 이야기가 나오면,
   너는 AI 친구일 뿐 전문가는 아니라는 점을 솔직하게 말하고,
   지금 당장은 주변 사람이나 전문 상담 기관, 위기 전화 같은
   현실의 도움을 받는 게 중요하다고 부드럽게 알려줘요.

전체 분위기:
- “너는 혼자가 아니에요”라는 느낌을 주는,
  포근하고 장난도 칠 줄 아는 친구처럼 이야기해줘요.
""".strip()

# ---------------------------
# CALL OPENAI (STREAMING)
# ---------------------------
def generate_reply(user_text: str) -> str:
    system_prompt = get_system_prompt(language)

    # 최근 몇 개만 히스토리로 사용 (토큰 절약)
    history = st.session_state["messages"][-10:]

    messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_text})

    # 입력에 따라 타이핑 속도 살짝 다르게
    text_lower = user_text.lower()
    slow_ko = ["죽고싶", "자살", "우울", "불안", "무기력", "힘들", "포기", "눈물", "괴롭"]
    slow_en = ["suicide", "kill myself", "die", "depressed", "depression",
               "anxious", "anxiety", "panic", "hopeless", "worthless"]
    fast_ko = ["심심", "농담", "웃긴", "웃겨", "재밌", "게임", "상황극"]
    fast_en = ["bored", "joke", "funny", "lol", "haha", "game", "roleplay", "rp"]

    if any(k in user_text for k in slow_ko) or any(k in text_lower for k in slow_en):
        delay = 0.06
    elif any(k in user_text for k in fast_ko) or any(k in text_lower for k in fast_en):
        delay = 0.015
    else:
        delay = 0.03

    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.9,
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
                f"<div class='bot-bubble'>{full_text} 💫</div>",
                unsafe_allow_html=True,
            )
            time.sleep(delay)

    return full_text.strip()

# ---------------------------
# RENDER CHAT HISTORY
# ---------------------------
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

# ---------------------------
# USER INPUT
# ---------------------------
user_input = st.chat_input(TEXT["input"])

if user_input is not None:
    if not user_input.strip():
        st.warning(TEXT["empty_warn"])
    else:
        # 유저 메시지 저장 + 표시
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.markdown(
            f"<div class='user-bubble'>{user_input}</div>",
            unsafe_allow_html=True,
        )

        # AI 답변 생성
        reply = generate_reply(user_input)
        if reply:
            st.session_state["messages"].append({"role": "assistant", "content": reply})
