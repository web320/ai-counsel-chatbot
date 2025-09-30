# app.py — UX 업그레이드(채팅내 가격/FAQ/문의 + Q&A 오류 수정 + 환불/플랜 유지)
import os, uuid, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# ========= OpenAI =========
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========= Firebase =========
import firebase_admin
from firebase_admin import credentials, firestore

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

# ========= 전역 스타일 =========
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
h1 { font-size: 40px !important; } h2 { font-size: 28px !important; } h3 { font-size: 22px !important; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
.chat-message { font-size: 22px; line-height: 1.7; white-space: pre-wrap; }
.hero { padding: 12px 16px; border-radius: 14px; background: rgba(80,120,255,0.08); margin-bottom: 8px; }
.badges { font-size: 15px; opacity: 0.9; }
.badge { display:inline-block; padding:4px 8px; border-radius:8px; margin-right:6px; background:#1e293b; color:#fff; }
.small { font-size: 14px; opacity: 0.9; }
.quickbar { position: sticky; top: 0; z-index: 9; padding:10px 12px; border-radius:12px;
            background: rgba(2,6,23,0.65); backdrop-filter: blur(6px); margin-bottom:10px; }
.quickpill { display:inline-block; padding:6px 10px; border-radius:999px; margin-right:8px; border:1px solid #334155; }
.card { padding:14px; border:1px solid #334155; border-radius:14px; }
</style>
""", unsafe_allow_html=True)

st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# ========= UID — URL 저장 =========
uid = st.query_params.get("uid")
if uid:
    USER_ID = uid
else:
    USER_ID = str(uuid.uuid4())
    st.query_params["uid"] = USER_ID

# ========= 상태 기본값 =========
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("is_paid", False)
st.session_state.setdefault("limit", 4)
st.session_state.setdefault("usage_count", 0)
st.session_state.setdefault("plan", None)
st.session_state.setdefault("purchase_ts", None)
st.session_state.setdefault("refund_until_ts", None)
st.session_state.setdefault("sessions_since_purchase", 0)
st.session_state.setdefault("refund_count", 0)
st.session_state.setdefault("refund_requested", False)

# ========= Firestore 사용자 로딩 =========
user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict()
    for k, v in {
        "usage_count":0,"limit":4,"is_paid":False,"plan":None,
        "purchase_ts":None,"refund_until_ts":None,
        "sessions_since_purchase":0,"refund_count":0,"refund_requested":False
    }.items():
        st.session_state[k] = snap.to_dict().get(k, v)
else:
    data = {
        "usage_count": 0, "limit": 4, "is_paid": False,
        "purchase_ts": None, "refund_until_ts": None,
        "sessions_since_purchase": 0, "refund_count": 0, "refund_requested": False,
        "plan": None
    }
    user_ref.set(data)

# ========= 의도/안전 간단 감지 =========
DANGEROUS = ["자살","죽고","죽고싶","해치","폭력","때리","살해","범죄","불법","마약","음란","노골적"]
COACH_KW = ["어떻게","방법","계획","추천","정리","수익","창업","투자","마케팅","습관","루틴","해결"]
VENT_KW  = ["힘들","불안","우울","외롭","걱정","짜증","화나","무기력","멘탈","지쳤"]
KEYWORD_HINTS = {
    "불안":"네가 불안하다고 말한 부분",
    "외로움":"외로움이 마음을 꽉 채우는 느낌",
    "돈":"돈에 대한 걱정",
    "미래":"미래가 흐릿하게 느껴지는 점",
}

def decide_mode(text: str) -> str:
    if any(k in text for k in DANGEROUS): return "safety"
    if any(k in text for k in COACH_KW):  return "coach"
    if any(k in text for k in VENT_KW):   return "support"
    return "coach"

def build_prompt(user_input: str):
    mode = decide_mode(user_input)
    hint = next((v for k, v in KEYWORD_HINTS.items() if k in user_input), "")
    base = """
너는 따뜻하고 다정하지만 과장하지 않는 상담사이자, 현실적인 재테크/수익화 코치다.
원칙:
- 답변은 4~7문장 정도로 조금 길게, 자연스럽고 이해하기 쉽게.
- 사용자가 방금 쓴 표현/키워드 1개 이상을 자연스럽게 포함.
- 상투적 위로나 불필요한 칭찬은 줄이고, 맥락에 맞는 공감과 제안을 섞는다.
- 필요할 때만 다음 단계/선택지를 제안(강제 아님). 확인 질문은 최대 1개.
"""
    if mode == "safety":
        sys = base + """
[안전 모드]
- 자/타해·불법·폭력·노골적 성적 내용엔 '경계 + 안전 안내' 우선.
- 위기대응 불가 고지 + 즉시 도움 연결(국번없이 1393/112, 가까운 응급실/신뢰할 보호자).
- 미화/정당화 금지, 위로는 절제하고 구체적 탈출 행동 제시.
"""
    elif mode == "support":
        sys = base + """
[감정 지지 모드]
- 짧은 공감으로 시작하고, 현실적인 관점 전환과 작게 시도할 제안.
- 마지막 한 줄은 상황에 어울릴 때만 담백한 희망 멘트.
"""
    else:
        sys = base + """
[코칭 모드]
- 목표/옵션/우선순위를 분명히 하되 과한 과제로 압박하지 않는다.
- 바로 적용 가능한 팁 중심.
"""
    usr = f"""[사용자 입력]
{user_input}

[참고 힌트]
{hint}

위 지침에 맞춰 답해줘.
"""
    return sys, usr

def stream_reply(user_input: str):
    sys, usr = build_prompt(user_input)
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.35, top_p=0.9,
        frequency_penalty=0.2, presence_penalty=0.0,
        max_tokens=900, stream=True,
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
    )

# ========= 보조: 환불 가능여부 =========
def refund_eligible():
    if not st.session_state.is_paid or not st.session_state.purchase_ts:
        return False, "유료 결제 내역이 없습니다."
    if st.session_state.refund_requested:
        return False, "환불 요청이 이미 접수되었습니다."
    if st.session_state.refund_count >= 1:
        return False, "환불은 계정당 1회 가능합니다."

    try:
        until = (datetime.fromisoformat(st.session_state.refund_until_ts)
                 if isinstance(st.session_state.refund_until_ts, str)
                 else st.session_state.refund_until_ts)
    except Exception:
        until = None
    now = datetime.utcnow()
    if not until or now > until:
        return False, "환불 가능 기간(구매 후 7일)이 지났습니다."
    if st.session_state.sessions_since_purchase > 20:
        return False, "구매 후 20회 초과 사용 시 환불이 제한됩니다."
    return True, "환불 가능"

def get_payment_url(plan_key: str) -> str:
    default_url = "https://www.paypal.com/ncp/payment/SPHCMW6E9S9C4"
    pay = st.secrets.get("payments", {})
    if isinstance(pay, dict):
        return pay.get(f"{plan_key}_url", default_url)
    return default_url

# ========= 상단 히어로(간결) =========
with st.container():
    st.markdown("""
<div class='hero'>
  <h3>AI 고민상담, <b>3회 무료 체험</b></h3>
  <div class='badges'>
    <span class='badge'>월 3,900원</span>
    <span class='badge'>7일 전액 환불</span>
    <span class='badge'>언제든 해지</span>
    <span class='badge'>상담내용 암호화</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ========= 채팅 영역 QuickBar (채팅 내부에서 가격/FAQ/문의 접근) =========
remaining = ("∞" if st.session_state.is_paid else
             max(st.session_state.limit - st.session_state.usage_count, 0))
with st.container():
    st.markdown(
        f"<div class='quickbar'>"
        f"<span class='quickpill'>남은 무료: <b>{remaining}</b>회</span>"
        f"<span class='quickpill'>유료: {'예' if st.session_state.is_paid else '아니오'}</span>"
        f"<span class='small' style='margin-left:6px;'>아래에서 바로 가격·FAQ·문의 열림</span>"
        f"</div>",
        unsafe_allow_html=True
    )

# === 채팅 상단 카드: 가격/FAQ/문의 Expander(채팅 화면 안에 고정) ===
with st.container():
    c1, c2 = st.columns(2)
    with c1:
        with st.expander("💳 가격 / 결제 (60회 $3 · 140회 $6)", expanded=False):
            c11, c12 = st.columns(2)
            with c11:
                st.markdown("**⭐ 베이직** — 60회 / **$3**\n\n7일 전액 환불 · 언제든 해지", unsafe_allow_html=True)
                st.link_button("PayPal 결제 (60회)", get_payment_url("plan60"), use_container_width=True)
                if st.button("✅ 임시 적용(테스트)", key="apply60_inline", use_container_width=True):
                    now = datetime.utcnow()
                    st.session_state.is_paid = True
                    st.session_state.limit = 60
                    st.session_state.usage_count = 0
                    st.session_state.plan = "p60"
                    st.session_state.purchase_ts = now
                    st.session_state.refund_until_ts = now + timedelta(days=7)
                    st.session_state.sessions_since_purchase = 0
                    user_ref.update({
                        "is_paid": True, "limit": 60, "usage_count": 0,
                        "plan": "p60",
                        "purchase_ts": now, "refund_until_ts": now + timedelta(days=7),
                        "sessions_since_purchase": 0
                    })
                    st.success("베이직 60회 적용!")
            with c12:
                st.markdown("**💎 프로** — 140회 / **$6**\n\n7일 전액 환불 · 언제든 해지", unsafe_allow_html=True)
                st.link_button("PayPal 결제 (140회)", get_payment_url("plan140"), use_container_width=True)
                if st.button("✅ 임시 적용(테스트)", key="apply140_inline", use_container_width=True):
                    now = datetime.utcnow()
                    st.session_state.is_paid = True
                    st.session_state.limit = 140
                    st.session_state.usage_count = 0
                    st.session_state.plan = "p140"
                    st.session_state.purchase_ts = now
                    st.session_state.refund_until_ts = now + timedelta(days=7)
                    st.session_state.sessions_since_purchase = 0
                    user_ref.update({
                        "is_paid": True, "limit": 140, "usage_count": 0,
                        "plan": "p140",
                        "purchase_ts": now, "refund_until_ts": now + timedelta(days=7),
                        "sessions_since_purchase": 0
                    })
                    st.success("프로 140회 적용!")

            st.markdown("---")
            st.markdown("**↩️ 7일 환불 규정(악용 방지 포함)**")
            st.markdown("- 첫 결제 후 **7일 이내 100% 환불**.\n- **구매 후 사용 20회 이하**일 때 가능.\n- **계정당 1회** 환불 제한.\n- 응급·의료상담 대체 불가. 개인정보는 암호화 저장, 마케팅 미사용.")
            eligible, msg = refund_eligible()
            rcol1, rcol2 = st.columns([1,2])
            with rcol1:
                req = st.button("환불 요청", disabled=not eligible, key="refund_req_inline", use_container_width=True)
            with rcol2:
                st.info(f"환불 상태: {msg}")
            if req and eligible:
                st.session_state.refund_requested = True
                st.session_state.refund_count += 1
                user_ref.update({
                    "refund_requested": True,
                    "refund_count": st.session_state.refund_count
                })
                st.success("환불 요청 접수 완료(영업일 1~3일 내 처리).")

    with c2:
        with st.expander("❓ FAQ / 📮 문의", expanded=False):
            # FAQ
            with st.container():
                st.markdown("**FAQ**")
                with st.expander("사람 상담사가 보나요?"):
                    st.write("아니요. AI가 답변하며, 내용은 외부에 공유되지 않습니다.")
                with st.expander("무료 체험은 몇 회인가요?"):
                    st.write("3회입니다. 결제 전 충분히 확인하세요.")
                with st.expander("환불 규정은?"):
                    st.write("첫 결제 후 7일 이내 100% 환불(구매 후 사용 20회 이하, 계정당 1회).")
                with st.expander("언제든 해지되나요?"):
                    st.write("마이페이지에서 1클릭 해지(관리자 승인 처리).")
                with st.expander("개인정보는 안전한가요?"):
                    st.write("전송·저장 시 암호화되며, 마케팅에 사용되지 않습니다.")

            st.markdown("---")
            # Q&A — **폼으로 구현**(오류 방지)
            st.markdown("**문의 남기기**")
            with st.form("qna_form", clear_on_submit=True):
                q = st.text_area("무엇이 궁금하신가요? (운영자에게 전달됩니다)", key="qna_input", height=120)
                submitted = st.form_submit_button("보내기")
            if submitted:
                if q and q.strip():
                    db.collection("qna").add({
                        "user_id": USER_ID, "question": q.strip(), "ts": datetime.utcnow()
                    })
                    st.success("문의가 저장되었습니다. 가능한 빨리 답변드릴게요.")
                    # 폼 clear_on_submit=True 로 초기화. 그래도 혹시 모를 버전 이슈 대비:
                    if "qna_input" in st.session_state:
                        st.session_state["qna_input"] = ""
                    st.rerun()
                else:
                    st.warning("질문을 입력해주세요.")

# ========= 채팅 가능 여부 =========
can_chat = st.session_state.is_paid or (st.session_state.usage_count < st.session_state.limit)

# ========= 채팅 본문 =========
if can_chat:
    # 웰컴 카드(첫 진입시)
    if len(st.session_state.chat_history) == 0:
        st.markdown("""
<div class="card">
<b>환영합니다!</b> 3회 무료로 마음 정리를 시작해보세요. 결제 전 <i>충분히</i> 체험하고 결정할 수 있어요.
</div>
""", unsafe_allow_html=True)

    # 입력 및 스트리밍
    user_input = st.chat_input("마음편히 얘기해봐")
    if user_input:
        st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)
        placeholder, streamed = st.empty(), ""
        for chunk in stream_reply(user_input):
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                streamed += delta.content
                placeholder.markdown(f"<div class='chat-message'>{streamed}</div>", unsafe_allow_html=True)

        st.session_state.chat_history.append((user_input, streamed))

        # 사용량 카운트
        if not st.session_state.is_paid:
            st.session_state.usage_count += 1
            user_ref.update({"usage_count": st.session_state.usage_count})
        else:
            st.session_state.sessions_since_purchase += 1
            user_ref.update({"sessions_since_purchase": st.session_state.sessions_since_purchase})

        # 피드백 블록
        st.markdown("---")
        st.subheader("📝 이번 답변은 어떠셨나요?")
        fb_col1, fb_col2, fb_col3 = st.columns([1,1,3])
        with fb_col1:
            good = st.button("👍 도움 됨", key=f"fb_good_{len(st.session_state.chat_history)}", use_container_width=True)
        with fb_col2:
            bad  = st.button("👎 별로", key=f"fb_bad_{len(st.session_state.chat_history)}", use_container_width=True)
        with fb_col3:
            note = st.text_input("추가 피드백(선택)", key=f"fb_note_{len(st.session_state.chat_history)}")

        if good or bad:
            db.collection("feedback").add({
                "user_id": USER_ID,
                "msg_index": len(st.session_state.chat_history)-1,
                "thumbs": "up" if good else "down",
                "note": note or "",
                "ts": datetime.utcnow(),
                "plan": st.session_state.plan,
            })
            st.success("피드백이 저장되었어요. 고마워요!")
else:
    # 체험 종료 → 채팅 내부에서 곧바로 구매 가능
    st.subheader("🚫 무료 체험이 끝났습니다")
    st.markdown("아래에서 바로 **60회 $3 / 140회 $6**로 이어서 이용할 수 있어요.")
    with st.expander("💳 가격 / 결제 열기", expanded=True):
        c11, c12 = st.columns(2)
        with c11:
            st.markdown("**⭐ 베이직** — 60회 / **$3**\n\n7일 전액 환불 · 언제든 해지", unsafe_allow_html=True)
            st.link_button("PayPal 결제 (60회)", get_payment_url("plan60"), use_container_width=True)
        with c12:
            st.markdown("**💎 프로** — 140회 / **$6**\n\n7일 전액 환불 · 언제든 해지", unsafe_allow_html=True)
            st.link_button("PayPal 결제 (140회)", get_payment_url("plan140"), use_container_width=True)

# ========= 사이드바: 기록/관리 =========
st.sidebar.header("📜 대화 기록")
st.sidebar.caption("내 UID (URL에 저장됨)")
st.sidebar.text_input(" ", value=USER_ID, disabled=True, label_visibility="collapsed")
if st.session_state.chat_history:
    st.sidebar.markdown(f"**사용 횟수:** {st.session_state.usage_count}/{st.session_state.limit} · 유료:{st.session_state.is_paid}")
    for i, (q, _) in enumerate(st.session_state.chat_history):
        st.sidebar.markdown(f"**Q{i+1}:** {q[:20]}...")

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 관리자 메뉴")
admin_pw = st.sidebar.text_input("관리자 비밀번호", type="password")
col1, col2 = st.sidebar.columns(2)
if admin_pw == "4321":
    if col1.button("🔑 유료모드(60회)", use_container_width=True):
        now = datetime.utcnow()
        st.session_state.is_paid = True
        st.session_state.limit = 60
        st.session_state.usage_count = 0
        st.session_state.plan = "p60"
        st.session_state.purchase_ts = now
        st.session_state.refund_until_ts = now + timedelta(days=7)
        st.session_state.sessions_since_purchase = 0
        user_ref.update({
            "is_paid": True, "limit": 60, "usage_count": 0,
            "plan": "p60",
            "purchase_ts": now, "refund_until_ts": now + timedelta(days=7),
            "sessions_since_purchase": 0
        })
        st.sidebar.success("유료모드(60회) 적용!")
    if col2.button("🆕 새 UID(테스트)", use_container_width=True):
        new_uid = str(uuid.uuid4())
        st.query_params["uid"] = new_uid
        st.rerun()
else:
    st.sidebar.caption("관리자 전용")
