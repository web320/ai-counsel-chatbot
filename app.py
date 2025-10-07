import os, uuid, json, hmac
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore

# ================= App Config =================
APP_VERSION = "v1.5.0"
PAYPAL_URL  = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
FREE_LIMIT  = 4
BASIC_LIMIT = 30
PRO_LIMIT   = 100
DEFAULT_TONE = "따뜻하게"  # 고정 톤

# ================= OpenAI =================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ================= Firebase Admin =================
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

# ================= Admin Keys (둘 다 허용 + Secrets 우선) =================
ADMIN_KEYS = []
for k in [st.secrets.get("ADMIN_KEY"), os.getenv("ADMIN_KEY"), "6U4urDCJLr7D0EWa4nST", "4321"]:
    if k and str(k) not in ADMIN_KEYS:
        ADMIN_KEYS.append(str(k))

def check_admin(pw: str) -> bool:
    p = (pw or "").strip()
    return any(hmac.compare_digest(p, key) for key in ADMIN_KEYS)

# ================= Query Params =================
def _qp_get(name: str, default=None):
    val = st.query_params.get(name)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

uid  = _qp_get("uid")
page = _qp_get("page", "chat")
if not uid:
    uid = str(uuid.uuid4())
    st.query_params = {"uid": uid, "page": page}
USER_ID = uid
PAGE     = page

# ================= Global Styles =================
st.set_page_config(page_title="당신을 기댈 수 있는 AI 친구", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
[data-testid="stSidebar"] * { font-size: 18px !important; }
.user-bubble { background:#b91c1c;color:#fff;border-radius:12px;padding:10px 16px;margin:8px 0;display:inline-block; }
.bot-bubble { font-size:21px;line-height:1.8;border-radius:14px;padding:14px 18px;margin:10px 0;background:rgba(15,15,30,.85);color:#fff;
  border:2px solid transparent;border-image:linear-gradient(90deg,#ff8800,#ffaa00,#ff8800) 1;animation:neon-glow 1.8s ease-in-out infinite alternate; }
@keyframes neon-glow { from{box-shadow:0 0 5px #ff8800,0 0 10px #ffaa00;} to{box-shadow:0 0 20px #ff8800,0 0 40px #ffaa00,0 0 60px #ff8800;} }
.status { font-size:15px; padding:8px 12px; border-radius:10px; display:inline-block; margin-bottom:8px; background:rgba(255,255,255,.06); }
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# ================= Session & User Doc =================
defaults = {
    "chat_history": [],
    "is_paid": False,
    "limit": FREE_LIMIT,
    "usage_count": 0,
    "plan": None,
    "remaining_paid_uses": 0,
    "is_admin": False,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        if data.get(k) is not None:
            st.session_state[k] = data.get(k)
else:
    user_ref.set(defaults)

# ================= Helpers =================
def persist_user(fields: dict) -> bool:
    """users/{USER_ID}에 필요한 필드만 merge 저장 + 저장 직후 재조회 검증"""
    try:
        user_ref.set(fields, merge=True)
        re = user_ref.get().to_dict() or {}
        ok = all(re.get(k) == v for k, v in fields.items())
        if not ok:
            st.error("저장 검증 실패: 다시 시도해주세요.")
            return False
        st.session_state.update(fields)
        return True
    except Exception as e:
        st.error("저장 중 오류")
        st.code(str(e))
        return False

def show_paypal_button(message: str):
    st.warning(message)
    st.markdown(f"""
    <hr>
    <div style='text-align:center;'>
        <p>💙 단 3달러로 30회의 마음상담을 이어갈 수 있어요.</p>
        <a href='{PAYPAL_URL}' target='_blank'>
            <button style='background:#0070ba;color:white;padding:12px 20px;border:none;border-radius:10px;font-size:18px;cursor:pointer;'>
              💳 PayPal로 결제하기 ($3)
            </button>
        </a>
        <p style='opacity:.75;margin-top:8px;'>
          결제 후 카카오톡 <b>jeuspo</b> 또는 이메일 <b>mwiby91@gmail.com</b>으로 스크린샷을 보내주세요.<br>
          관리자 비밀번호를 알려드려요.
        </p>
    </div>
    """, unsafe_allow_html=True)

def save_feedback(uid: str, text: str, page_name: str):
    try:
        content = (text or "").strip()
        if not content:
            st.warning("내용을 입력해주세요 😊")
            return None
        doc = {
            "user_id": uid,
            "feedback": content,
            "app_version": APP_VERSION,
            "page": page_name,
            "ts": datetime.now(timezone.utc).isoformat()
        }
        dr = db.collection("feedback").document()
        dr.set(doc)
        st.success("피드백이 저장되었어요 💙")
        st.info(f"문서 ID: {dr.id}")
        return dr.id
    except Exception as e:
        st.error("피드백 저장 실패")
        st.code(str(e))
        return None

def apply_plan_basic():
    fields = {
        "is_paid": True, "plan": "basic",
        "limit": BASIC_LIMIT,
        "usage_count": 0,
        "remaining_paid_uses": BASIC_LIMIT,
    }
    if persist_user(fields):
        st.success("베이직 30회 적용 완료! 채팅으로 이동합니다.")
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

def apply_plan_pro():
    fields = {
        "is_paid": True, "plan": "pro",
        "limit": PRO_LIMIT,
        "usage_count": 0,
        "remaining_paid_uses": PRO_LIMIT,
    }
    if persist_user(fields):
        st.success("프로 100회 적용 완료! 채팅으로 이동합니다.")
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

def reset_to_free():
    fields = {
        "is_paid": False, "plan": None,
        "limit": FREE_LIMIT,
        "usage_count": 0,
        "remaining_paid_uses": 0,
    }
    if persist_user(fields):
        st.success("무료 체험으로 초기화됐어요.")
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ================= OpenAI Stream =================
def stream_reply(user_input: str):
    if client is None:
        st.error("OPENAI_API_KEY가 설정되어 있지 않습니다.")
        return
    sys_prompt = f"""
    너는 {DEFAULT_TONE} 말투의 심리상담사야.
    - 공감 → 구체 조언 → 실천 제안, 3문단 이내.
    - 현실적이고 짧게.
    """
    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            max_tokens=600,
            stream=True,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0], "delta", None)
            if delta and getattr(delta, "content", None):
                yield delta.content
    except Exception as e:
        st.error("OpenAI 응답 오류")
        st.code(str(e))

# ================= UI Helpers =================
def status_chip():
    if st.session_state.get("is_paid"):
        st.markdown(
            f"<div class='status'>💎 유료({st.session_state.get('plan')}) — 남은 {st.session_state.get('remaining_paid_uses',0)}/{st.session_state.get('limit',0)}회</div>",
            unsafe_allow_html=True
        )
    else:
        left = int(st.session_state.get("limit", FREE_LIMIT)) - int(st.session_state.get("usage_count", 0))
        st.markdown(
            f"<div class='status'>🌱 무료 체험 — 남은 {max(left,0)}회</div>",
            unsafe_allow_html=True
        )

# ================= Pages =================
def render_chat_page():
    status_chip()

    # 제한 로직
    if st.session_state.get("is_paid"):
        remaining = int(st.session_state.get("remaining_paid_uses", 0))
        if remaining <= 0:
            show_paypal_button("💳 이용권이 모두 소진되었습니다. 새로 결제 후 이용해주세요.")
            return
    else:
        used = int(st.session_state.get("usage_count", 0))
        if used >= int(st.session_state.get("limit", FREE_LIMIT)):
            show_paypal_button("무료 체험이 모두 끝났어요 💙")
            return

    # 입력 & 라이트 힌트
    user_input = st.chat_input("지금 어떤 기분이야?")
    if not user_input:
        return
    if any(k in user_input for k in ["힘들", "피곤", "짜증", "불안", "우울"]):
        st.markdown("<div class='bot-bubble'>💭 많이 지쳐 있네요... 그래도 괜찮아요.</div>", unsafe_allow_html=True)
    elif any(k in user_input for k in ["행복", "좋아", "괜찮", "고마워"]):
        st.markdown("<div class='bot-bubble'>🌤️ 그 기분, 참 소중하네요.</div>", unsafe_allow_html=True)

    # 스트리밍
    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    placeholder, streamed = st.empty(), ""
    for token in stream_reply(user_input):
        streamed += token
        safe = streamed.replace("\n\n", "<br><br>")
        placeholder.markdown(f"<div class='bot-bubble'>🧡 {safe}</div>", unsafe_allow_html=True)

    # 기록/차감
    st.session_state.chat_history.append((user_input, streamed))
    if st.session_state.get("is_paid"):
        new_left = max(0, int(st.session_state.get("remaining_paid_uses", 0)) - 1)
        persist_user({"remaining_paid_uses": new_left})
    else:
        new_usage = int(st.session_state.get("usage_count", 0)) + 1
        persist_user({"usage_count": new_usage})

    # 체험 종료 CTA
    if (not st.session_state.get("is_paid")) and (st.session_state.get("usage_count", 0) >= st.session_state.get("limit", FREE_LIMIT)):
        show_paypal_button("무료 체험이 끝났어요. 다음 대화부터는 유료 이용권이 필요해요 💳")

    # 피드백
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("📝 대화에 대한 피드백을 남겨주세요")
    fb = st.text_area("좋았던 점/아쉬운 점을 적어주세요",
                      placeholder="예: 위로가 많이 됐어요 / 답변이 조금 짧았어요 / 결제 안내가 헷갈려요")
    if st.button("📩 피드백 제출"):
        if fb and fb.strip():
            save_feedback(USER_ID, fb, "chat")
        else:
            st.warning("내용을 입력해주세요 😊")

def render_plans_page():
    status_chip()

    header_html = """
    <div style='text-align:center; padding-top:8px;'>
      <h2 style="margin:0 0 6px 0;">💙 마음을 기댈 수 있는 AI 친구</h2>
      <h3 style="margin:0;">💳 결제 안내</h3>
    </div>
    """
    cards_html = f"""
    <style>
      .pricing-wrap{{display:flex;justify-content:center;gap:28px;flex-wrap:wrap;}}
      .card{{width:280px;border-radius:16px;padding:18px;color:#fff;background:rgba(255,255,255,.05);
             box-shadow:0 6px 22px rgba(0,0,0,.25);}}
      .card.basic{{border:2px solid #ffaa00;}}
      .card.pro{{border:2px solid #00d4ff;}}
      .card h3{{margin:0;font-weight:700;}}
      .price{{font-size:34px;margin:8px 0 2px 0;}}
      .desc{{opacity:.85;margin:0 0 6px 0;}}
      .btn{{margin-top:10px;padding:10px 18px;font-size:17px;border:none;border-radius:10px;cursor:pointer;}}
      .btn.basic{{background:#ffaa00;color:#000;}}
      .btn.pro{{background:#555;color:#ccc;}}
      .howto{{margin-top:24px;text-align:center;color:#ddd;}}
      .idbox{{display:inline-flex;gap:8px;align-items:center;margin-top:6px;}}
      .copy{{padding:4px 10px;border:1px solid rgba(255,255,255,.25);border-radius:8px;background:transparent;color:#ddd;cursor:pointer;font-size:14px;}}
    </style>

    <div class="pricing-wrap">
      <div class="card basic">
        <h3 style="color:#ffaa00;">⭐ 베이직 플랜</h3>
        <div class="price">$3</div>
        <p class="desc">30회 상담 이용권</p>
        <p class="desc">필요할 때마다 손쉽게</p>
        <a href="{PAYPAL_URL}" target="_blank">
          <button class="btn basic">💳 결제하기</button>
        </a>
      </div>

      <div class="card pro">
        <h3 style="color:#00d4ff;">💎 프로 플랜</h3>
        <div class="price">$6</div>
        <p class="desc">100회 상담 이용권</p>
        <p class="desc">오랫동안 함께하는 마음 친구</p>
        <button class="btn pro" disabled>준비 중</button>
      </div>
    </div>

    <div class="howto">
      <p style="margin:0;">💬 결제 후 인증:</p>
      <div class="idbox">
        <span>카톡: <b>jeuspo</b></span>
        <button class="copy" onclick="navigator.clipboard.writeText('jeuspo')">복사</button>
      </div>
      <div class="idbox">
        <span>이메일: <b>mwiby91@gmail.com</b></span>
        <button class="copy" onclick="navigator.clipboard.writeText('mwiby91@gmail.com')">복사</button>
      </div>
      <p style="opacity:.8;margin-top:8px;">스크린샷을 보내주시면 <b>관리자 비밀번호</b>를 알려드립니다.</p>
    </div>
    """
    components.html(header_html + cards_html, height=620, scrolling=False)

    # ---- 관리자 로그인/영역 (Form으로 안정 처리) ----
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("🔐 관리자 모드")

    if not st.session_state.get("is_admin"):
        with st.form("admin_login_form", clear_on_submit=True):
            pw = st.text_input("관리자 비밀번호", type="password")
            submitted = st.form_submit_button("🔑 관리자 로그인")
        if submitted:
            if check_admin(pw):
                st.session_state["is_admin"] = True
                st.success("관리자 인증 완료 ✅")
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        return

    # 로그인 후 관리자 대시보드
    st.caption("🧭 현재 사용자 상태 (Firestore 실시간 조회)")
    live = user_ref.get().to_dict() or {}
    st.json({
        "is_paid": live.get("is_paid"),
        "plan": live.get("plan"),
        "limit": live.get("limit"),
        "usage_count": live.get("usage_count"),
        "remaining_paid_uses": live.get("remaining_paid_uses"),
        "user_id": USER_ID
    })

    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1:
        if st.button("✅ 베이직 30회 적용 ($3)"):
            apply_plan_basic()
    with c2:
        if st.button("✅ 프로 100회 적용 ($6)"):
            apply_plan_pro()
    with c3:
        if st.button("🧹 무료 체험으로 초기화"):
            reset_to_free()
    with c4:
        if st.button("🔄 상태 새로고침"):
            st.rerun()

    st.markdown("---")
    st.subheader("🛠 수동 잔여횟수 설정")
    new_left = st.number_input("남은 상담 횟수", min_value=0, max_value=100000, value=int(live.get("remaining_paid_uses", 0)))
    if st.button("📌 잔여횟수 적용"):
        if persist_user({"remaining_paid_uses": int(new_left)}):
            st.success("잔여횟수가 업데이트 되었어요.")
            st.rerun()

    st.markdown("---")
    st.subheader("🧪 Firestore 진단 쓰기")
    if st.button("⚙️ diagnostics 문서 쓰기"):
        try:
            db.collection("diagnostics").add({
                "uid": USER_ID,
                "ts": datetime.now(timezone.utc).isoformat(),
                "note": "plans page ping"
            })
            st.success("진단 문서가 저장되었어요.")
        except Exception as e:
            st.error("진단 문서 저장 실패")
            st.code(str(e))

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ================= Sidebar & Routing =================
st.sidebar.header("📜 대화 기록")
st.sidebar.text_input(" ", value=USER_ID, disabled=True, label_visibility="collapsed")
if PAGE == "chat":
    if st.sidebar.button("💳 결제/FAQ 열기"):
        st.query_params = {"uid": USER_ID, "page": "plans"}
        st.rerun()
else:
    if st.sidebar.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()
