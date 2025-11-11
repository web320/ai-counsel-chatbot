# ==========================================
# 💙 EOERWAY AI Therapy v2.9
# (Conversations + Memory + Mode + Diversity + Feedback + Events)
# ==========================================

import os, uuid, json, time, random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from difflib import SequenceMatcher   # ADDED: similarity check

# ================= Streamlit Page Config =================
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.9"
DAILY_FREE_LIMIT = 15          # 무료 상담 횟수
BASIC_LIMIT = 50               # 유료 결제 제공 상담 횟수
RESET_INTERVAL_HOURS = 6       # 무료 상담 회복 주기
ADMIN_KEYS = ["2356"]          # 관리자 인증 비밀번호

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

# ================= Visitor Counter =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    user_visit_ref = db.collection("user_visits").document(USER_ID)
    if user_visit_ref.get().exists:
        return

    user_visit_ref.set({
        "uid": USER_ID,
        "first_visit": datetime.utcnow().isoformat(),
        "day": today,
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
        "admin_success": "🔓 Admin verified. Added 50 more uses!",
        "admin_already": "✅ Admin already unlocked.",
        "admin_wrong": "❌ Wrong admin password.",
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
  background:#b91c1c; color:#fff; border-radius:14px;
  padding:10px 18px; margin:8px 0; display:inline-block;
  box-shadow:0 0 10px rgba(255,0,0,0.3);
}
.bot-bubble {
  font-size:21px; line-height:1.8; border-radius:16px;
  padding:16px 20px; margin:10px 0; background:rgba(15,15,30,.85);
  color:#fff; border:2px solid transparent;
  border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;
  box-shadow:0 0 12px #ffaa00; animation:neon 1.6s ease-in-out infinite alternate;
  word-break:break-word; white-space:pre-wrap;
}
@keyframes neon { from { box-shadow:0 0 8px #ffaa00; } to { box-shadow:0 0 22px #ffcc33; } }
.status {
  font-size:15px; padding:8px 12px; border-radius:10px;
  display:inline-block; margin-bottom:8px; background:rgba(255,255,255,.06);
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

# ================= Conversations (Per-User) — ADDED =================
def _new_conversation_id():
    return datetime.utcnow().strftime("conv-%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]

_existing_cid = st.query_params.get("cid", [None])[0]
if "conversation_id" not in st.session_state:
    st.session_state["conversation_id"] = _existing_cid or _new_conversation_id()

st.query_params = {"uid": USER_ID, "cid": st.session_state["conversation_id"]}
CONV_ID = st.session_state["conversation_id"]
conv_ref = db.collection("users").document(USER_ID).collection("conversations").document(CONV_ID)
if not conv_ref.get().exists:
    conv_ref.set({
        "uid": USER_ID, "conversation_id": CONV_ID,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "title": None, "message_count": 0
    })

# ================= Long-term Memory Helpers — ADDED =================
def _get_user_memory(uid: str) -> str:
    doc = db.collection("users").document(uid).collection("memory").document("profile").get()
    if doc.exists:
        return (doc.to_dict() or {}).get("text", "")
    return ""

def _maybe_refresh_memory(uid: str, conv_ref):
    """대화 누적 시 주기적으로 요약해 메모리에 저장 (비차단)"""
    try:
        meta = conv_ref.get().to_dict() or {}
        if meta.get("message_count", 0) % 12 != 0:
            return

        msgs = list(
            conv_ref.collection("messages")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(80).stream()
        )
        transcript = []
        for m in reversed(msgs):
            d = m.to_dict() or {}
            transcript.append(f"{d.get('role','').upper()}: {d.get('content','')}")

        joined = "\n".join(transcript[-1500:])

        # 최근 피드백(감정/도움체감) 5개 반영
        try:
            fb = list(
                db.collection("session_feedback").where("uid","==",uid)
                .order_by("ts", direction=firestore.Query.DESCENDING).limit(5).stream()
            )
            fb_lines = [
                f"FB: affect={f.to_dict().get('affect')} helpful={f.to_dict().get('helpful')} note={f.to_dict().get('note','')}"
                for f in fb
            ]
            if fb_lines:
                joined = joined + "\n" + "\n".join(reversed(fb_lines))
        except Exception:
            pass

        sys = ("From the following chat transcript, extract durable user preferences, tone, "
               "recurring concerns, and useful facts to personalize future replies. "
               "Keep it under 180 words. Use bullet points.")
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": joined}],
            temperature=0.3, max_tokens=400
        )
        summary = res.choices[0].message.content.strip()
        db.collection("users").document(uid).collection("memory").document("profile").set({
            "text": summary,
            "updated_at": datetime.utcnow().isoformat(),
            "source_conversation": CONV_ID
        })
    except Exception:
        pass

# ================= Load conversation history into session — ADDED =================
def _load_conv_history_into_session(conv_ref, limit=50):
    try:
        msgs = conv_ref.collection("messages").order_by("created_at").limit(limit).stream()
        loaded = []
        for m in msgs:
            d = m.to_dict() or {}
            loaded.append({
                "role": d.get("role", "assistant" if d.get("role") != "user" else "user"),
                "content": d.get("content", ""),
                "timestamp": d.get("created_at", "")
            })
        if loaded:
            st.session_state["chat_history"] = loaded[-50:]
    except Exception:
        pass

if not st.session_state.get("chat_history"):
    _load_conv_history_into_session(conv_ref, limit=50)

# ================= Events Logger — ADDED =================
def log_event(name, payload=None):
    try:
        db.collection("events").add({
            "uid": USER_ID, "cid": CONV_ID, "name": name,
            "payload": payload or {}, "ts": datetime.utcnow().isoformat()
        })
    except Exception:
        pass

# ================= Diversity Helpers — ADDED =================
STYLE_HINTS = [
    "Mindfulness: 호흡과 감각 어휘 2개 이상, 현재 순간에 집중, 속도 느리게.",
    "행동활성화: 5~10분짜리 행동 1개만, 시작 신호(언제/어디)까지 구체화.",
    "인지재구성: 자동사고 1개 이름 붙이고, 부드럽게 재구성.",
    "가치정렬: 핵심가치 1개 상기 + 그에 맞는 미세행동 1개.",
    "커뮤니케이션: ‘나는~’ 메시지 1문장 + 경계설정 1문장.",
    "환경정리: 물리/디지털 마찰 1개 줄이는 행동 1개."
]
def _too_similar(a: str, b: str, thresh: float = 0.86) -> bool:
    if not a or not b: return False
    return SequenceMatcher(None, a, b).ratio() >= thresh

# ================= AI Response Function =================
def stream_reply(user_input: str):
    try:
        if language == "English 🇺🇸":
            system_prompt = """
You're a warm, human-like companion. Priorities: safety first, empathy, naming feelings, gentle normalization, one small optional step, and connection.
Avoid diagnoses/medication/legal advice. Use respectful, human tone (3–6 sentences recommended, flexible).
Diversity & specificity rules:
- Avoid repeating openings/closings from the last 5 replies.
- Mirror at least 2 concrete details the user mentioned (event/time/place/bodily cues/self-talk).
- Rotate one focus axis: Situation / Body / Thoughts / Values / Supports / Next step.
- Offer at most one suggestion, rotating among: Mindfulness / Behavioral activation / Cognitive reframing / Values alignment / Communication / Environment.
"""
        else:
            system_prompt = """
AI 심리상담 챗봇 역할 지침(요약)
- 안전>공감>감정명명>정상화>작은 실천(선택)>연결감. 진단/약물/법률 조언은 금지.
- 존댓말, 따뜻하고 인간적인 톤. 3~6문장 권장(유연).
[대화 가이드 — 권장(강제 아님)]
- 상황과 맥락에 맞게 자연스럽게 대화. 아래는 참고 예시일 뿐, 반드시 따를 필요 없음.
- 과장·훈계·가스라이팅·공허한 긍정 금지. 제안은 1가지만, “원하시면…”처럼 부드럽게.
[우선순위]
1) 자해/자살 언급 시 고통을 인정하고 안전 우선. 한국: 112/응급실/1393 안내.
2) 공감 → 감정명명 → 정상화 → 작은 실천(선택) → 연결감 (필요 시 일부만 사용).
[열린 질문 예시]
- “요즘 무엇이 가장 버겁게 느껴지셨어요?”
- “지금 몸에서 가장 큰 신호는 어디에 있나요?”
- “조금이라도 나아지도록 제가 어떻게 도와드리면 좋을까요?”
[상황별 응답 샘플(예시)]
- 가벼운 인사/막막·불안/우울·무기력/분노·좌절/자기비난/금전·진로/마무리 등은 사용자 맥락에 맞게 변주.
[하지 말 것]
- 진단·약물·법률 조언, 허위 확신, 해결책 남발, ‘~해야만 한다’ 훈계, 불필요한 개인정보 요구.
[선택적 확장]
- 사용자가 원하면 SMART하게 한 걸음만 제시. 이전 대화의 핵심을 1줄 상기하되 과도한 추측 금지.
[다양성·구체성 규칙 — 매우 중요]
- 최근 5개와 문장 시작/표현/마무리가 겹치지 않도록 변형.
- 사용자가 말한 구체어 2개 이상 반영(사건/시간/장소/몸감각/자기대화).
- 질문 바퀴에서 이번 턴엔 하나만: ①상황 ②몸감각 ③생각 ④가치 ⑤지지자원 ⑥다음 한 걸음.
- 제안 카테고리(1개): Mindfulness/행동활성화/인지재구성/가치정렬/커뮤니케이션/환경정리.
- 마무리는 ‘따뜻한 확인/작은 초대/함께감’ 중 변주.
"""

        # Long-term memory
        user_memory = _get_user_memory(USER_ID)

        # Build context
        context_messages = [{"role": "system", "content": system_prompt}]
        if user_memory:
            context_messages.append({
                "role": "system",
                "content": f"User profile & recurring themes:\n{user_memory}"
            })

        # Mode system hint (Soothe/Explore/Plan/Celebrate/Crisis)
        mode = st.session_state.get("mode", "Soothe")
        context_messages.append({
            "role":"system",
            "content": (
                f"[모드 규칙] 현재 모드: {mode}\n"
                "- Soothe: 3~4문장, 감정명명+정상화 중심\n"
                "- Explore: 열린 질문 2개 + 요약 1줄\n"
                "- Plan: 실행조건(언제/어디/몇분/시작신호)까지 1개\n"
                "- Celebrate: 성취 구체화 질문 1개 + 자기인정 1문장\n"
                "- Crisis: 안전 우선 문구 + 112/1393 안내, 구체 묘사 피함"
            )
        })

        # Recent history (in-session only)
        recent_history = st.session_state["chat_history"][-10:]
        for msg in recent_history:
            context_messages.append({"role": msg["role"], "content": msg["content"]})

        # Current user message
        context_messages.append({"role": "user", "content": user_input})

        # Stream main reply
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
                placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
                time.sleep(0.02)

        # === Diversity: re-generate if too similar to last 3 assistant replies
        recent_assistant = [m["content"] for m in st.session_state["chat_history"] if m["role"]=="assistant"][-3:]
        if any(_too_similar(full_text.strip(), prev) for prev in recent_assistant):
            try:
                alt_hint = random.choice(STYLE_HINTS)
                alt_messages = context_messages + [
                    {"role":"system","content": f"[대체 스타일 힌트]\n{alt_hint}"}
                ]
                alt = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=alt_messages,
                    temperature=0.9,
                    max_tokens=600,
                    stream=False,
                )
                alt_text = alt.choices[0].message.content.strip()
                if alt_text and not any(_too_similar(alt_text, prev) for prev in recent_assistant):
                    full_text = alt_text
                    placeholder.markdown(f"<div class='bot-bubble'>{full_text}💫</div>", unsafe_allow_html=True)
            except Exception:
                pass

        timestamp = datetime.utcnow().isoformat()

        # Legacy log
        db.collection("chats").add({
            "uid": USER_ID, "input": user_input, "reply": full_text.strip(),
            "lang": language, "created_at": timestamp
        })

        # Session state
        st.session_state["chat_history"].append({"role": "user","content": user_input,"timestamp": timestamp})
        st.session_state["chat_history"].append({"role": "assistant","content": full_text.strip(),"timestamp": timestamp})

        # Per-conversation storage
        try:
            batch = db.batch()
            msgs_ref = conv_ref.collection("messages")
            now_iso = timestamp
            user_doc = msgs_ref.document()
            bot_doc  = msgs_ref.document()
            batch.set(user_doc, {"role": "user", "content": user_input, "created_at": now_iso})
            batch.set(bot_doc,  {"role": "assistant", "content": full_text.strip(), "created_at": now_iso})

            conv_doc = conv_ref.get()
            meta_updates = {"updated_at": now_iso, "message_count": firestore.Increment(2)}
            if not conv_doc.exists or not (conv_doc.to_dict() or {}).get("title"):
                preview = (user_input[:32] + "…") if len(user_input) > 32 else user_input
                meta_updates["title"] = preview

            if conv_doc.exists:
                batch.update(conv_ref, meta_updates)
            else:
                batch.set(conv_ref, {**meta_updates, "uid": USER_ID, "conversation_id": CONV_ID}, merge=True)

            batch.commit()
            _maybe_refresh_memory(USER_ID, conv_ref)  # non-blocking
        except Exception:
            pass

        # Event log
        log_event("reply_generated", {"mode": mode, "length": len(full_text)})

        return full_text.strip()

    except Exception as e:
        st.error(f"{TEXT['reply_error']}: {e}")
        return None

# ================= Payment / Feedback Panel =================
def render_payment_and_feedback():
    st.markdown("---")
    st.subheader(TEXT["payment_title"])

    intent_ref = db.collection("purchase_intent").document(USER_ID)
    intent_doc = intent_ref.get()
    clicked = intent_doc.exists
    total_intents = len(list(db.collection("purchase_intent").stream()))

    st.markdown("#### 50회 이용권 3,000원 결제 의사 확인")

    if clicked:
        st.info("💙 이미 결제 의사를 눌러주셨어요. 정말 감사합니다.")
    else:
        if st.button("💳 3,000원에 50회 이용권, 결제 의사가 있으신가요?"):
            intent_ref.set({
                "uid": USER_ID,
                "plan": "50회_3000원",
                "created_at": datetime.utcnow().isoformat(),
            })
            st.success("결제 기능이 열리면 가장 먼저 알려드릴게요 💖")
            st.rerun()

    st.caption(f"지금까지 {total_intents}명이 결제 의사를 눌러주셨어요.")

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
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

# ================= Chat Main Page =================
def render_chat_page():
    if st.session_state.get("is_paid"):
        left = st.session_state.get("remaining_paid_uses", BASIC_LIMIT)
        plan = TEXT["paid"]
    else:
        left = DAILY_FREE_LIMIT - st.session_state["usage_count"]
        plan = TEXT["free"]

    st.markdown(f"<div class='status'>{plan} — {TEXT['status_left']} {max(left,0)}회</div>", unsafe_allow_html=True)

    # Reset cycle
    now = datetime.utcnow()
    last_reset = datetime.fromisoformat(st.session_state.get("last_reset"))
    if (now - last_reset).total_seconds() / 3600 >= RESET_INTERVAL_HOURS:
        persist_user({"usage_count": 0, "last_reset": now.isoformat()})
        st.info(TEXT["reset"])

    # ===== Mode Switch (ADDED)
    mode = st.radio(
        " ",
        ["Soothe", "Explore", "Plan", "Celebrate", "Crisis"],
        horizontal=True, label_visibility="collapsed", index=0
    )
    st.session_state["mode"] = mode

    # Existing history view
    display_chat_history()

    # User input
    user_input = st.chat_input(TEXT["input"])
    if not user_input:
        return

    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)
    reply = stream_reply(user_input)

    if reply:
        if st.session_state.get("is_paid"):
            persist_user({"remaining_paid_uses": max(0, st.session_state.get("remaining_paid_uses", BASIC_LIMIT) - 1)})
        else:
            persist_user({"usage_count": st.session_state["usage_count"] + 1})
        st.rerun()

# ================= Sidebar =================
st.sidebar.header("📜 History / 대화 기록")

total_visits, daily_visits = get_visit_counts()
st.sidebar.markdown(
    f"""
    <div style="margin-top: 12px; margin-bottom: 16px; padding: 8px 10px;
        border-radius: 10px; background: rgba(255,255,255,0.03);
        font-size: 13px; color: rgba(255,255,255,0.85);">
        🌍 <b>Total {total_visits:,}명</b><br>
        ☀️ <b>Today {daily_visits:,}명</b>
    </div>
    """,
    unsafe_allow_html=True
)

# Clear session chat history only (not DB)
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

# ===== Conversations Switcher (Sidebar) — ADDED
with st.sidebar.expander("🗂️ 대화 세션 관리", expanded=False):
    try:
        conv_stream = (
            db.collection("users").document(USER_ID).collection("conversations")
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(10).stream()
        )
        conv_items = []
        for doc in conv_stream:
            d = doc.to_dict() or {}
            label = (d.get("title") or d.get("conversation_id") or doc.id)
            updated = d.get("updated_at", "")
            conv_items.append((doc.id, f"{label} · {updated[:16]}"))

        if conv_items:
            labels = [lbl for _, lbl in conv_items]
            idx = 0
            for i, (cid, _) in enumerate(conv_items):
                if cid == CONV_ID:
                    idx = i
                    break
            choice = st.selectbox("대화 선택", labels, index=idx)
            selected_cid = conv_items[labels.index(choice)][0]
            if selected_cid != CONV_ID:
                st.session_state["conversation_id"] = selected_cid
                st.session_state["chat_history"] = []
                st.query_params = {"uid": USER_ID, "cid": selected_cid}
                st.rerun()

        if st.button("➕ 새 대화 시작"):
            new_cid = datetime.utcnow().strftime("conv-%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
            st.session_state["conversation_id"] = new_cid
            st.session_state["chat_history"] = []
            db.collection("users").document(USER_ID).collection("conversations").document(new_cid).set({
                "uid": USER_ID, "conversation_id": new_cid,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "title": None, "message_count": 0
            })
            st.query_params = {"uid": USER_ID, "cid": new_cid}
            st.rerun()
    except Exception:
        st.caption("세션 목록을 불러오는 중 문제가 발생했어요.")

# ===== Quick Satisfaction Feedback (Sidebar) — ADDED
with st.sidebar.expander("🪴 오늘 대화는 어땠나요? (10초)", expanded=False):
    try:
        affect = st.slider("마음 상태(불편→편안)", 1, 5, 3, key="affect_slider")
        helpful = st.slider("도움 정도(낮음→높음)", 1, 5, 3, key="helpful_slider")
        note = st.text_input("한 줄 메모 (선택)", "", key="note_input")
        if st.button("저장", key="save_feedback_btn"):
            db.collection("session_feedback").add({
                "uid": USER_ID, "cid": CONV_ID,
                "affect": affect, "helpful": helpful, "note": note,
                "mode": st.session_state.get("mode"),
                "ts": datetime.utcnow().isoformat()
            })
            st.success("고마워요! 더 맞춤형으로 배워갈게요.")
    except Exception:
        st.caption("피드백 저장 중 문제가 발생했어요.")

# ================= Main Render =================
if st.session_state.get("show_payment"):
    render_payment_and_feedback()
else:
    render_chat_page()
