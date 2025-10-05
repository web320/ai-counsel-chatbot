# app.py — AI 심리상담 챗봇 (네온 + 따뜻한 상담 포맷)
import os, uuid, json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ===== OpenAI =====
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== Firebase =====
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

# ===== 스타일 =====
st.set_page_config(page_title="ai심리상담 챗봇", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px; color: white; }
h1 { font-size: 42px !important; } h2 { font-size: 28px !important; } h3 { font-size: 22px !important; }

.chat-message { 
    font-size: 22px; 
    line-height: 1.8; 
    white-space: pre-wrap;
    border-radius: 16px;
    padding: 16px 20px;
    margin: 10px 0;
    background: rgba(20,20,35,0.75);
    border: 2px solid transparent;
    border-image: linear-gradient(90deg, #ff00ff, #00ffff, #ff00ff) 1;
    animation: neon-glow 1.8s ease-in-out infinite alternate;
}
@keyframes neon-glow {
  from { box-shadow: 0 0 5px #ff00ff, 0 0 10px #00ffff; }
  to { box-shadow: 0 0 20px #ff00ff, 0 0 40px #00ffff, 0 0 60px #00ffff; }
}

.advice-box {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 18px;
    margin-top: 15px;
}
.advice-box strong {
    color: #ffd166;
}
</style>
""", unsafe_allow_html=True)

st.title("💙 ai심리상담 챗봇")
st.caption("마음편히 얘기해")

# ===== 세션 =====
if "uid" not in st.session_state:
    st.session_state["uid"] = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

USER_ID = st.session_state["uid"]
user_ref = db.collection("users").document(USER_ID)

# ===== 모드 감지 =====
DANGEROUS = ["자살","죽고","죽고싶","해치","폭력","범죄","불법","마약"]
VENT = ["우울","불안","외롭","지쳤","힘들","짜증","화나","무기력"]
COACH = ["방법","추천","계획","습관","루틴","해결","수익","투자","사업"]

def decide_mode(text):
    if any(k in text for k in DANGEROUS): return "safety"
    if any(k in text for k in VENT): return "support"
    if any(k in text for k in COACH): return "coach"
    return "support"

# ===== 프롬프트 =====
def build_prompt(user_input):
    mode = decide_mode(user_input)
    base = """
너는 따뜻하고 차분한 심리상담사이자, 감정에 공감하며 현실적인 조언을 주는 코치이다.
답변 형식:
1. 짧은 공감 문장으로 시작
2. 감정에 대한 구체적 이해 표현
3. 2~3개의 실질적인 행동 제안 (숫자 목록)
4. 마지막에 따뜻한 위로 문장 포함
5. 한국어 존댓말 유지, 너무 딱딱하지 않게 부드럽고 다정하게

출력은 아래 HTML 포맷을 따라야 한다:
<div class='chat-message'>
  <p>공감 문장</p>
  <div class='advice-box'>
    <p>조언 문단</p>
    <ol>
      <li>행동 제안 1</li>
      <li>행동 제안 2</li>
      <li>행동 제안 3</li>
    </ol>
  </div>
  <p><strong>마무리 위로 문장</strong></p>
</div>
"""

    if mode == "safety":
        base += """
[안전 모드 지침]
- 자/타해 언급 시 절대 미화하지 말 것
- 1393, 112 등 도움 요청 권장
- 위험 인식과 전문기관 안내 중심
"""
    elif mode == "coach":
        base += """
[코칭 모드 지침]
- 목표와 실행 루틴 중심으로 명확히 제안
"""
    else:
        base += """
[감정 지지 모드 지침]
- 감정의 인정과 작은 회복 행동에 초점
"""
    usr = f"[사용자 입력]\n{user_input}\n위의 규칙에 따라 HTML 구조로 출력해줘."
    return [{"role":"system","content":base},{"role":"user","content":usr}]

# ===== 스트리밍 =====
def stream_reply(user_input):
    messages = build_prompt(user_input)
    return client.chat.completions.create(
        model="gpt-4o-mini", stream=True,
        temperature=0.6, max_tokens=700,
        messages=messages,
    )

# ===== UI =====
user_input = st.chat_input("마음편히 얘기해봐")
if user_input:
    st.markdown(f"<div class='chat-message'>{user_input}</div>", unsafe_allow_html=True)
    placeholder = st.empty()
    output = ""
    buffer = ""
    for chunk in stream_reply(user_input):
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            buffer += delta.content
            if len(buffer) > 40:
                output += buffer
                placeholder.markdown(output, unsafe_allow_html=True)
                buffer = ""
    output += buffer
    placeholder.markdown(output, unsafe_allow_html=True)

    st.session_state.chat_history.append((user_input, output))
    user_ref.set({"last_msg": user_input, "ts": datetime.utcnow().isoformat()}, merge=True)
