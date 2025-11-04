# ==========================================
# 💙 EOERWAY AI Therapy v2.8
# (Default: English, Small Language Toggle Button + Fixed Visitor Counter)
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
st.set_page_config(page_title="💙 AI Therapy", layout="wide")

# ================= Constants / Config =================
APP_VERSION = "v2.8"
PAYPAL_URL = "https://www.paypal.com/ncp/payment/W6UUT2A8RXZSG"
DAILY_FREE_LIMIT = 7
BASIC_LIMIT = 50
RESET_INTERVAL_HOURS = 4
ADMIN_KEYS = ["4321"]

# ================= ads.txt =================
if "ads.txt" in st.query_params:
    st.write("google.com, pub-5846666879010880, DIRECT, f08c47fec0942fa0")
    st.stop()

# ================= OpenAI =================
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

# ================= Visitor Counter (Admin 제외) =================
def update_visit_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
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

ADMIN_UIDS = ["4321", "admin", "owner"]

if "visit_logged" not in st.session_state:
    if USER_ID not in ADMIN_UIDS:
        update_visit_stats()
    st.session_state["visit_logged"] = True

total_visits, daily_visits = get_visit_counts()

# ✅ 맨 위 헤더 고정 표시
st.markdown(
    f"""
    <div style="
        position:fixed;
        top:0;
        left:0;
        width:100%;
        text-align:center;
        background:rgba(0,0,0,0.5);
        padding:12px 0;
        font-size:18px;
        font-weight:600;
        color:#fff;
        z-index:9999;
        backdrop-filter:blur(8px);
        border-bottom:1px solid rgba(255,255,255,0.2);
    ">
        🌍 Total <b>{total_visits:,}명</b> &nbsp;&nbsp;|&nbsp;&nbsp; ☀️ Today <b>{daily_visits:,}명</b>
    </div>
    <br><br><br>
    """,
    unsafe_allow_html=True
)

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
    }
else:
    TEXT = {
        "title": "❤️ 마음을 기댈 수 있는 따뜻한 AI 친구",
        "free": "🌱 무료 체험중",
        "paid": "💎 유료 이용중",
        "input": "지금 어떤 기분이예요?",
    }

# ================= Title =================
st.title(TEXT["title"])

