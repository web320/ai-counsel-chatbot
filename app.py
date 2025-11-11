# ==========================================
# 💙 EOERWAY AI Therapy v2.9 (Chat History only / No Conversations, No Quick-Feedback)
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
DAILY_FREE_LIMIT = 15          # 무료 상담 횟수
BASIC_LIMIT = 50              # 유료 결제 후 제공되는 상담 횟수
RESET_INTERVAL_HOURS = 6      # 무료 상담 회복 주기
ADMIN_KEYS = ["2356"]         # 관리자(본인) 인증용 비밀번호

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
        "usedup": "🌙 You've used all 15 free sessions today!",
        "reset": "⏰ Free sessions reset! (Every 6 hours)",
        "reply_error": "AI response error",
        "feedback_placeholder": "e.g., The AI felt really comforting 💕",
        "feedback_sent": "💖 Feedback saved safely. Thank you!",
        "feedback_empty": "Please write something 💬",
        "payment_title": "💳 Payment Guide",
        "feedback_title": "💌 Service Feedback",
        "chat_return": "💬 Back to Chat",
        "chat_button": "💳 Open Payment & Feedback",
        "status_left": "remaining",
        "admin_success": "🔓 관리자 모드가 활성화되어 50회 무료 이용권이 추가되었습니다!",
        "admin_already": "✅ 이미 관리자 인증이 완료되어 있습니다.",
        "admin_wrong": "❌ 관리자 비밀번호가 틀렸습니다.",
        "clear_history": "🗑️ Clear Chat History",
        "history_cleared": "Chat history has been cleared!",
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
        "warn": "내용을 입력해주세요 💬",
        "usedup": "🌙 오늘의 무료 상담 15회를 모두 사용했어요!",
        "reset": "⏰ 무료 상담이 다시 가능해졌어요! (6시간마다 복구)",
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
    "is_paid": False,
    "usage_count": 0,
    "remaining_paid_uses": 0,
    "last_reset": datetime.utcnow().isoformat()
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

# ================= Long-term Memory (read-only; keeps as-is) =================
def _get_user_memory(uid: str) -> str:
    doc = db.collection("users").document(uid).collection("memory").document("profile").get()
    if doc.exists:
        return (doc.to_dict() or {}).get("text", "")
    return ""

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

Respond in 4-6 sentences, warm and human, never clinical. Never diagnose or suggest medication. If they mention self-harm or suicide, gently acknowledge their pain and suggest professional help."""
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
[다양성·구체성 규칙 — 매우 중요]
- 같은 회차/최근 5개 답변과 문장 시작·표현·마무리가 겹치지 않도록 변형하세요.
- 사용자가 말한 구체어(사건·시간·장소·몸감각·자기대화)를 2개 이상 정확히 반영하세요.
- 아래 질문 바퀴 중 이번 턴에 하나만 고르되, 직전과 다른 축을 쓰세요:
  ①상황 ②몸감각 ③생각/자기대화 ④가치/욕구 ⑤지지자원 ⑥다음 한 걸음
- 제안은 카테고리를 돌려가며 1가지만: Mindfulness / 행동활성화 / 인지재구성 / 가치정렬 / 커뮤니케이션 / 환경정리 중 하나.
- 마무리 문구는 고정하지 말고 ‘따뜻한 확인/작은 초대/함께감’ 중 하나를 변주하세요.
[질문 바퀴 예시]
- 상황: “오늘 가장 버거웠던 한 순간을 30초에 담아주실래요?”
- 몸감각: “지금 몸에서 가장 큰 신호는 어디에 있나요?”
- 생각/자기대화: “그 순간 머릿속에 자동으로 스친 문장은 무엇이었나요?”
- 가치/욕구: “이 상황에서 지키고 싶은 당신의 ‘가치’는 무엇일까요?”
- 지지자원: “도움이 될 만한 사람/장소/루틴이 하나 떠오르나요?”
- 다음 걸음: “5분 안에 가능한 아주 작은 행동 하나만 정해볼까요?”
[대체 스타일 힌트]
- Mindfulness: 호흡/감각 언어를 2개 이상 포함하고, 현재 순간에 고정.
- 행동활성화: 5~10분짜리 행동 1가지만, 시작 신호까지 구체화.
- 인지재구성: 자동사고 1개를 이름 붙이고, 부드럽게 재구성.
- 가치정렬: 사용자의 핵심가치 1개를 떠올리게 하고, 그에 맞는 미세행동 1개.
- 커뮤니케이션: “나는~” 메시지 1문장과 경계설정 문장 1개 제안.
- 환경정리: 물리/디지털 환경에서 마찰 1개 줄이는 행동 1개.
[모드 규칙]
- Soothe: 문장 3~4, 속도 느리게, 감정명명 + 정상화 중심.
- Explore/Clarify: 열린 질문 2개, 요약 1줄.
- Plan: 실행조건(언제/어디/몇 분/시작 신호)까지 1개.
- Celebrate: 성취 구체화 질문 1개 + 자기인정 1문장.
- Crisis: 안전 우선 문구 + 112/1393 안내, 구체 묘사는 피함.
보여주지 않고, 시스템에만 **“지난 대화에서 드러난 핵심(관성, 선호, 트리거, 효과 있던 방법)”**을 1~2줄로 주입하세요.

예) “이 사용자는 구체적 실행계획을 좋아하고, 아침 시간이 어렵다. 돈 걱정이 잦다.”

"""

        # 메모리(읽기만)
        user_memory = _get_user_memory(USER_ID)

        # 대화 컨텍스트 구성 (최근 10개 메시지만 사용)
        context_messages = [{"role": "system", "content": system_prompt}]
        if user_memory:
            context_messages.append({
                "role": "system",
                "content": f"User profile & recurring themes for personalization:\n{user_memory}"
            })

        # 세션에 저장된 최근 대화만 사용 (Firebase 읽기 없음)
        recent_history = st.session_state["chat_history"][-10:]
        for msg in recent_history:
            context_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # 현재 입력 추가
        context_messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=context_messages,
            temperature=0.7,
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
                    f"<div class='bot-bubble'>{full_text}💫</div>",
                    unsafe_allow_html=True
                )
                time.sleep(0.03)

        timestamp = datetime.utcnow().isoformat()

        # 대화 기록 저장 (Firebase - 1회 쓰기만)
        db.collection("chats").add({
            "uid": USER_ID,
            "input": user_input,
            "reply": full_text.strip(),
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
            "content": full_text.strip(),
            "timestamp": timestamp
        })

        # (REMOVED) per-user conversation 저장/메모리 요약 관련 코드

        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])

    intent_ref = db.collection("purchase_intent").document(USER_ID)
    intent_doc = intent_ref.get()
    clicked = intent_doc.exists
    total_intents = len(list(db.collection("purchase_intent").stream()))

    # 🔹 언어별 라벨/문구 분기
    is_en = (language == "English 🇺🇸")
    if is_en:
        title_line = "#### 50 uses for **$3** — Purchase intent"
        btn_label = "💳 $3 for 50 uses — I'm interested"
        info_already = "💙 You've already registered your interest. Thank you!"
        success_msg = "We'll notify you first when payments open 💖"
        caption_text = f"So far, **{total_intents}** people have shown interest."
        plan_value = "50_uses_$3"
    else:
        title_line = "#### 50회 이용권 3,000원 결제 의사 확인"
        btn_label = "💳 3,000원에 50회 이용권, 결제 의사가 있으신가요?"
        info_already = "💙 이미 결제 의사를 눌러주셨어요. 정말 감사합니다."
        success_msg = "결제 기능이 열리면 가장 먼저 알려드릴게요 💖"
        caption_text = f"지금까지 {total_intents}명이 결제 의사를 눌러주셨어요."
        plan_value = "50회_3000원"

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
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]

    st.markdown(
        f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>",
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

    usage = st.session_state["usage_count"]
    if not st.session_state.get("is_paid") and usage >= DAILY_FREE_LIMIT:
        st.warning(TEXT["usedup"])
        st.session_state["show_payment"] = True
        st.rerun()

    # 기존 채팅 기록 표시
    display_chat_history()

    # 사용자 입력
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    # 새 메시지 표시
    st.markdown(
        f"<div class='user-bubble'>{user_input}</div>",
        unsafe_allow_html=True
    )

    reply = stream_reply(user_input)

    if reply:
        if st.session_state.get("is_paid"):
            persist_user({
                "remaining_paid_uses": max(
                    0,
                    st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1
                )
            })
        else:
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

if st.session_state.get("show_payment"):
    if st.sidebar.button(TEXT["chat_return"]):
        st.session_state["show_payment"] = False
        st.rerun()
else:
    if st.sidebar.button(TEXT["chat_button"]):
        st.session_state["show_payment"] = True
        st.rerun()

# (REMOVED) Conversations Switcher / Quick Satisfaction Feedback

# ================= Main Render =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
