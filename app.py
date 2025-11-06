# ==========================================
# 💙 EOERWAY AI Therapy v2.8
# (Default: English, Small Language Toggle Button)
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
# ⚠️ MUST be the first Streamlit call before any other st.* usage
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.8"
DAILY_FREE_LIMIT = 7          # 무료 상담 횟수 (4시간 기준)
RESET_INTERVAL_HOURS = 4      # 무료 상담 리셋 주기 (시간)
MODEL_NAME = "gpt-4o-mini"    # 원하는 모델로 변경 가능

load_dotenv()
client = OpenAI()

# ================= Firebase / Firestore Init =================
db = None
try:
    if not firebase_admin._apps:
        cred_obj = None

        # 1) Streamlit Secrets 에 객체로 들어있는 경우
        if "FIREBASE_SERVICE_ACCOUNT" in st.secrets:
            cred_obj = st.secrets["FIREBASE_SERVICE_ACCOUNT"]
        else:
            # 2) 환경변수에 JSON 문자열로 들어있는 경우
            cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
            if cred_json:
                cred_obj = json.loads(cred_json)

        if cred_obj:
            cred = credentials.Certificate(cred_obj)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
except Exception as e:
    # Firestore 연결 실패해도 앱은 동작하게 두기
    db = None


# ================= Visitor Counter (총 방문자 / 오늘 방문자) =================
def increase_visit_counts():
    """페이지에 접속할 때마다 방문자수 +1."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 🔹 Firestore가 없는 경우: 세션 기준 임시 카운트
    if db is None:
        if "visit_total" not in st.session_state:
            st.session_state["visit_total"] = 0
            st.session_state["visit_today"] = 0
            st.session_state["visit_date"] = today_str

        if st.session_state["visit_date"] != today_str:
            st.session_state["visit_date"] = today_str
            st.session_state["visit_today"] = 0

        st.session_state["visit_total"] += 1
        st.session_state["visit_today"] += 1
        return

    # 🔹 Firestore 사용 (stats / visitors)
    stats_ref = db.collection("stats").document("visitors")
    doc = stats_ref.get()
    data = doc.to_dict() if doc.exists else {}

    total = data.get("total", 0)
    today = data.get("today", 0)
    saved_date = data.get("today_date")

    if saved_date != today_str:
        today = 0  # 날짜 바뀌면 오늘 방문자수 리셋

    stats_ref.set(
        {
            "total": total + 1,
            "today": today + 1,
            "today_date": today_str,
        },
        merge=True,
    )


def get_visit_counts():
    """총 방문자수, 오늘 방문자수 반환."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    if db is None:
        if "visit_total" not in st.session_state:
            return 0, 0
        # 날짜가 바뀌었으면 오늘 방문자는 0으로 보고 표시
        if st.session_state.get("visit_date") != today_str:
            return st.session_state.get("visit_total", 0), 0
        return (
            st.session_state.get("visit_total", 0),
            st.session_state.get("visit_today", 0),
        )

    stats_ref = db.collection("stats").document("visitors")
    doc = stats_ref.get()
    data = doc.to_dict() if doc.exists else {}
    return data.get("total", 0), data.get("today", 0)


# ================= Free Usage Limit (4시간당 7회) =================
def init_usage_state():
    if "free_count" not in st.session_state:
        st.session_state["free_count"] = 0
        st.session_state["last_reset_ts"] = time.time()

    now = time.time()
    last = st.session_state.get("last_reset_ts", 0)
    if now - last > RESET_INTERVAL_HOURS * 3600:
        st.session_state["free_count"] = 0
        st.session_state["last_reset_ts"] = now


# ================= Chat / Language Helpers =================
def get_system_prompt(lang: str) -> str:
    if lang == "ko":
        return (
            "너는 EOERWAY AI Therapy라는 따뜻한 심리상담 AI야. "
            "상담자는 불안, 외로움, 돈 걱정, 인생 고민을 가지고 올 수 있어. "
            "항상 다정하고 공감해 주고, 사용자를 비난하지 마. "
            "짧고 부드럽게, 마치 친한 언니처럼 이야기해 줘. "
            "필요할 때만 아주 간단한 행동 팁(호흡, 작은 할 일 등)을 제안하고, "
            "전문적인 진단이나 약 처방은 절대 하지 마."
        )
    else:
        return (
            "You are EOERWAY AI Therapy, a warm, kind, non-judgmental AI friend. "
            "People come to you with anxiety, loneliness, money worries, and life confusion. "
            "Always respond gently, with lots of empathy and emotional validation. "
            "Keep your answers short and soft, like a caring friend. "
            "You may suggest very small, practical steps (breathing, tiny tasks), "
            "but do not give medical diagnoses or medication advice."
        )


def get_ai_reply(history, lang: str) -> str:
    system_message = {"role": "system", "content": get_system_prompt(lang)}
    messages = [system_message] + history

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.7,
    )
    return resp.choices[0].message.content


def get_user_id() -> str:
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = str(uuid.uuid4())
    return st.session_state["user_id"]


# ================= Main App =================
def main():
    # 방문자수 카운트 먼저
    increase_visit_counts()
    total_visits, today_visits = get_visit_counts()

    init_usage_state()
    user_id = get_user_id()

    # 언어 기본값: 영어
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"

    # ------- 상단 레이아웃 -------
    top_left, top_right = st.columns([4, 1])

    with top_left:
        st.markdown("## 💙 EOERWAY AI Therapy")
        st.caption(f"Warm AI Friend for Lonely & Anxious Minds · v{APP_VERSION}")

    with top_right:
        lang_toggle = st.toggle(
            "한국어로 보기",
            value=(st.session_state["lang"] == "ko"),
            help="끄면 English, 켜면 한국어",
        )
        st.session_state["lang"] = "ko" if lang_toggle else "en"

    lang = st.session_state["lang"]

    # 방문자수 표시
    if lang == "ko":
        st.markdown(
            f"**총 방문자수:** {total_visits}명 · **오늘 방문자수:** {today_visits}명"
        )
    else:
        st.markdown(
            f"**Total visitors:** {total_visits} · **Today:** {today_visits}"
        )

    # 무료 사용 남은 횟수
    remaining = max(0, DAILY_FREE_LIMIT - st.session_state["free_count"])
    if lang == "ko":
        st.info(
            f"⏳ 4시간마다 무료 상담 **{DAILY_FREE_LIMIT}회** 제공 · "
            f"현재 남은 횟수: **{remaining}회**"
        )
    else:
        st.info(
            f"⏳ You get **{DAILY_FREE_LIMIT} free messages every {RESET_INTERVAL_HOURS} hours.** "
            f"Remaining now: **{remaining} messages**"
        )

    # 채팅 히스토리 초기화
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # 기존 대화 출력
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 프롬프트 placeholder
    if lang == "ko":
        placeholder = "지금 어떤 마음인지 편하게 털어놔도 괜찮아요."
    else:
        placeholder = "Tell me how you're feeling right now. I'm here with you."

    user_input = st.chat_input(placeholder)

    if user_input:
        # 무료 횟수 체크
        if st.session_state["free_count"] >= DAILY_FREE_LIMIT:
            if lang == "ko":
                st.warning(
                    f"무료 상담 횟수를 모두 사용했어요 🥹\n"
                    f"{RESET_INTERVAL_HOURS}시간 후에 다시 **{DAILY_FREE_LIMIT}회**가 채워져요."
                )
            else:
                st.warning(
                    "You used all your free messages for now 🥹\n"
                    f"They will reset in {RESET_INTERVAL_HOURS} hours."
                )
        else:
            # 사용자 메시지 표시
            st.session_state["messages"].append(
                {"role": "user", "content": user_input}
            )
            with st.chat_message("user"):
                st.markdown(user_input)

            # AI 답변
            with st.chat_message("assistant"):
                with st.spinner("생각 중이에요... / I'm thinking..."):
                    reply = get_ai_reply(st.session_state["messages"], lang)
                    st.markdown(reply)

            st.session_state["messages"].append(
                {"role": "assistant", "content": reply}
            )
            st.session_state["free_count"] += 1

    # 하단 크레딧 (Created by web320)
    st.markdown(
        """
        <div style="position: fixed; right: 16px; bottom: 12px;
                    font-size: 11px; opacity: 0.7; color: #cccccc;">
            Created by web320
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
