import os, uuid, json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components   # ✅ 추가
import firebase_admin
from firebase_admin import credentials, firestore

# ===== OPENAI =====
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== FIREBASE =====
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

# ===== QUERY PARAM =====
def _qp_get(name: str, default=None):
    val = st.query_params.get(name)
    if isinstance(val, list):
        return val[0] if val else default
    return val or default

uid = _qp_get("uid")
page = _qp_get("page", "chat")
if not uid:
    uid = str(uuid.uuid4())
    st.query_params = {"uid": uid, "page": page}

USER_ID = uid
PAGE = page

# ===== STYLE =====
st.set_page_config(page_title="당신을 기댈 수 있는 AI 친구", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; }
[data-testid="stSidebar"] * { font-size: 18px !important; }

.user-bubble {
    background: #b91c1c; color: white; border-radius: 12px;
    padding: 10px 16px; margin: 8px 0; display: inline-block;
}
.bot-bubble {
    font-size: 21px; line-height: 1.8; border-radius: 14px;
    padding: 14px 18px; margin: 10px 0;
    background: rgba(15,15,30,0.85); color: #fff;
    border: 2px solid transparent;
    border-image: linear-gradient(90deg, #ff8800, #ffaa00, #ff8800) 1;
    animation: neon-glow 1.8s ease-in-out infinite alternate;
}
@keyframes neon-glow {
  from { box-shadow: 0 0 5px #ff8800, 0 0 10px #ffaa00; }
  to   { box-shadow: 0 0 20px #ff8800, 0 0 40px #ffaa00, 0 0 60px #ff8800; }
}
</style>
""", unsafe_allow_html=True)

st.title("💙 마음을 기댈 수 있는 AI 친구")

# ===== SESSION =====
defaults = {
    "chat_history": [],
    "is_paid": False,
    "limit": 4,         # 무료 4회
    "usage_count": 0,
    "plan": None,
    "remaining_paid_uses": 0,
    "tone": "따뜻하게"
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

user_ref = db.collection("users").document(USER_ID)
snap = user_ref.get()
if snap.exists:
    data = snap.to_dict() or {}
    for k, v in defaults.items():
        st.session_state[k] = data.get(k, v)
else:
    user_ref.set(defaults)

# ===== GPT HELPER =====
def stream_reply(user_input: str, tone: str):
    sys_prompt = f"""
    너는 {tone} 말투의 심리상담사야.
    - 감정을 공감하고 → 구체적인 조언 → 실천 제안 순으로 3문단 이내로 답해.
    - 따뜻하고 현실적으로, 문장은 짧게 써줘.
    """
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=600,
        stream=True,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input}
        ]
    )

# ===== PAYPAL CTA =====
def show_paypal_button(message):
    st.warning(message)
    st.markdown(f"""
    <hr>
    <div style='text-align:center;'>
        <p>💙 단 3달러로 30회의 마음상담을 이어갈 수 있어요.</p>
        <a href='https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG' target='_blank'>
            <button style='background:#0070ba;color:white;padding:12px 20px;
            border:none;border-radius:10px;font-size:18px;cursor:pointer;'>
            💳 PayPal로 결제하기 ($3)
            </button>
        </a>
        <p style='opacity:0.75;margin-top:8px;'>결제 후 카카오톡 <b>jeuspo</b> 또는 이메일 <b>mwiby91@gmail.com</b>으로 스크린샷을 보내주세요. 관리자 비밀번호를 알려드립니다.</p>
    </div>
    """, unsafe_allow_html=True)

# ===== CHAT PAGE =====
def render_chat_page():
    st.caption("마음 편히 얘기해 💬")

    tone = st.radio(
        "🎭 상담 톤을 선택해주세요:",
        ["따뜻하게", "직설적으로", "철학적으로"],
        horizontal=True,
        index=["따뜻하게", "직설적으로", "철학적으로"].index(st.session_state.tone)
    )
    st.session_state.tone = tone
    user_ref.update({"tone": tone})

    # 이용 제한
    if st.session_state.is_paid:
        remaining = st.session_state.remaining_paid_uses
        st.caption(f"💎 남은 상담 횟수: {remaining}회 / {st.session_state.limit}회")
        if remaining <= 0:
            show_paypal_button("💳 이용권이 모두 소진되었습니다. 새로 결제 후 이용해주세요.")
            return
    else:
        if st.session_state.usage_count >= st.session_state.limit:
            show_paypal_button("무료 체험이 모두 끝났어요 💙")
            return
        st.caption(f"🌱 무료 체험 남은 횟수: {st.session_state.limit - st.session_state.usage_count}회")

    user_input = st.chat_input("지금 어떤 기분이야?")
    if not user_input:
        return

    # 가벼운 감정 피드백
    mood_hint = ""
    if any(k in user_input for k in ["힘들", "피곤", "짜증", "불안", "우울"]):
        mood_hint = "💭 지금 마음이 많이 지쳐 있네요... 그래도 괜찮아요."
    elif any(k in user_input for k in ["행복", "좋아", "괜찮", "고마워"]):
        mood_hint = "🌤️ 그 기분, 참 소중하네요."
    if mood_hint:
        st.markdown(f"<div class='bot-bubble'>{mood_hint}</div>", unsafe_allow_html=True)

    # 대화
    st.markdown(f"<div class='user-bubble'>😔 {user_input}</div>", unsafe_allow_html=True)
    placeholder, streamed = st.empty(), ""
    for chunk in stream_reply(user_input, tone):
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            streamed += delta.content
            placeholder.markdown(
                f"<div class='bot-bubble'>🧡 {streamed.replace('\n\n','<br><br>')}</div>",
                unsafe_allow_html=True
            )

    # 기록/차감
    st.session_state.chat_history.append((user_input, streamed))
    if st.session_state.is_paid:
        st.session_state.remaining_paid_uses -= 1
        user_ref.update({"remaining_paid_uses": st.session_state.remaining_paid_uses})
    else:
        st.session_state.usage_count += 1
        user_ref.update({"usage_count": st.session_state.usage_count})

    # 체험 끝 → CTA
    if not st.session_state.is_paid and st.session_state.usage_count >= st.session_state.limit:
        show_paypal_button("무료 체험이 끝났어요. 다음 대화부터는 유료 이용권이 필요해요 💳")

    # 피드백
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("📝 대화에 대한 피드백을 남겨주세요")
    fb = st.text_area("어떤 점이 좋았나요? 또는 개선했으면 하는 점이 있나요?",
                      placeholder="예: 대답이 따뜻했어요 / 답변이 조금 짧아요 / 디자인이 좋아요")
    if st.button("📩 피드백 제출"):
        if fb.strip():
            db.collection("feedbacks").add({
                "uid": USER_ID,
                "feedback": fb,
                "timestamp": datetime.now().isoformat()
            })
            st.success("감사합니다 💙 피드백이 소중히 전달되었어요!")
        else:
            st.warning("내용을 입력해주세요 😊")

# ===== PLANS PAGE (components.html로 안정 렌더링) =====
def render_plans_page():
    header_html = """
    <div style='text-align:center; padding-top:8px;'>
      <h2 style="margin:0 0 6px 0;">💙 마음을 기댈 수 있는 AI 친구</h2>
      <h3 style="margin:0;">💳 결제 안내</h3>
      <p style='opacity:.7;margin:6px 0 14px 0;'>현재는 예시 모드이며 실제 결제는 진행되지 않습니다.</p>
    </div>
    """
    cards_html = """
    <style>
      .pricing-wrap{display:flex;justify-content:center;gap:28px;flex-wrap:wrap;}
      .card{
        width:280px; border-radius:16px; padding:18px; color:#fff;
        background: rgba(255,255,255,0.05);
        box-shadow: 0 6px 22px rgba(0,0,0,.25);
      }
      .card.basic{border:2px solid #ffaa00;}
      .card.pro{border:2px solid #00d4ff;}
      .card h3{margin:0; font-weight:700;}
      .price{font-size:34px; margin:8px 0 2px 0;}
      .desc{opacity:.85;margin:0 0 6px 0;}
      .btn{
        margin-top:10px; padding:10px 18px; font-size:17px; border:none; border-radius:10px;
        cursor:pointer;
      }
      .btn.basic{background:#ffaa00; color:#000;}
      .btn.pro{background:#555; color:#ccc;}
      .howto{
        margin-top:24px; text-align:center; color:#ddd;
      }
      .idbox{display:inline-flex; gap:8px; align-items:center; margin-top:6px;}
      .copy{
        padding:4px 10px; border:1px solid rgba(255,255,255,.25); border-radius:8px;
        background:transparent; color:#ddd; cursor:pointer; font-size:14px;
      }
    </style>

    <div class="pricing-wrap">
      <div class="card basic">
        <h3 style="color:#ffaa00;">⭐ 베이직 플랜</h3>
        <div class="price">$3</div>
        <p class="desc">30회 상담 이용권</p>
        <p class="desc">따뜻한 위로가 필요할 때마다</p>
        <a href="https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG" target="_blank">
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
      <p style="margin:0;">💬 결제 후 아래로 인증해주세요:</p>
      <div class="idbox">
        <span>카톡: <b>jeuspo</b></span>
        <button class="copy" onclick="navigator.clipboard.writeText('jeuspo')">복사</button>
      </div>
      <div class="idbox">
        <span>이메일: <b>mwiby91@gmail.com</b></span>
        <button class="copy" onclick="navigator.clipboard.writeText('mwiby91@gmail.com')">복사</button>
      </div>
      <p style="opacity:.8;margin-top:8px;">결제 스크린샷을 보내주시면 <b>관리자 비밀번호</b>를 알려드립니다.</p>
    </div>
    """
    # ✅ components.html은 HTML을 100% 그대로 렌더링해줘서 "텍스트로 보이는" 문제가 사라짐
    components.html(header_html + cards_html, height=620, scrolling=False)

    # ---- 관리자 영역 (Streamlit 위젯) ----
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("🔐 관리자 모드")
    admin_pw = st.text_input("관리자 비밀번호", type="password")
    if admin_pw == "4321":
        st.success("관리자 인증 완료 ✅")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 베이직 30회 적용 ($3)"):
                st.session_state.update({
                    "is_paid": True, "limit": 30, "usage_count": 0,
                    "remaining_paid_uses": 30, "plan": "basic"
                })
                user_ref.update(st.session_state)
                st.success("🎉 베이직 30회 이용권이 적용되었어요!")
        with col2:
            if st.button("✅ 프로 100회 적용 ($6)"):
                st.session_state.update({
                    "is_paid": True, "limit": 100, "usage_count": 0,
                    "remaining_paid_uses": 100, "plan": "pro"
                })
                user_ref.update(st.session_state)
                st.success("💎 프로 100회 이용권이 적용되었어요!")

    if st.button("⬅ 채팅으로 돌아가기"):
        st.query_params = {"uid": USER_ID, "page": "chat"}
        st.rerun()

# ===== SIDEBAR =====
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

# ===== MAIN =====
if PAGE == "chat":
    render_chat_page()
elif PAGE == "plans":
    render_plans_page()
else:
    st.query_params = {"uid": USER_ID, "page": "chat"}
    st.rerun()

