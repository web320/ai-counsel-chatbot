# ==========================================
# 💙 EOERWAY AI Therapy vX.0-MaxMonetize
# (Global Chatbot + Monetization Layer)
# ==========================================

import os, uuid, json, time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from deep_translator import GoogleTranslator
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------
# Config & Constants
# ---------------------------
st.set_page_config(page_title="💙 EOERWAY AI Therapy", layout="wide")
load_dotenv()
APP_VERSION = "vX.0-MaxMonetize"
DAILY_FREE_LIMIT = 7                # 무료 상담 횟수
RESET_INTERVAL_HOURS = 4
BASIC_LIMIT = 50                    # 유료 사용자 상담 횟수
PAYPAL_URL = os.getenv("PAYPAL_URL") or "https://www.paypal.com/..." 
ADMIN_KEYS = ["4321"]
AFFILIATE_URL = os.getenv("AFFILIATE_URL") or "https://example.com/?ref=eoerway"   # 제휴 링크

# ---------------------------
# Firebase Init
# ---------------------------
def _firebase_config():
    raw = st.secrets.get("firebase")
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw)

if not firebase_admin._apps:
    cred = credentials.Certificate(_firebase_config())
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------------------
# OpenAI Client
# ---------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# Session & User Setup
# ---------------------------
uid = st.query_params.get("uid", [str(uuid.uuid4())])[0]
st.query_params = {"uid": uid}
USER_ID = uid

# ---------------------------
# Translation & Utility Functions
# ---------------------------
def detect_language(text):
    try:
        return GoogleTranslator(source='auto', target='en').detect(text)
    except:
        return "en"

def translate_to_en(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except:
        return text

def translate_from_en(text, lang):
    try:
        return GoogleTranslator(source='en', target=lang).translate(text)
    except:
        return text

def analyze_emotion(text):
    # 단순 버전: 감정 스코어 계산
    sad = sum(text.lower().count(k) for k in ["sad","tired","lonely","무기력","슬퍼","외로"])
    happy = sum(text.lower().count(k) for k in ["happy","love","기뻐","좋아","감사"])
    return max(0, min(100, 50 + (happy - sad)*10))

# ---------------------------
# Monetization Hooks
# ---------------------------
def maybe_show_ad():
    # 사용자 이용 패턴 기준으로 광고/제휴 링크 노출 가능
    # 예: 무료 사용자라면 X회 후 배너 혹은 제휴 추천
    pass

def handle_affiliate_click():
    # affiliate URL 클릭 로그 및 수익 추적
    db.collection("affiliate_clicks").add({
        "uid": USER_ID,
        "time": datetime.utcnow().isoformat()
    })

# ---------------------------
# Main Chat UI
# ---------------------------
st.title("💙 EOERWAY AI Therapy")
st.caption("Global Emotional AI Friend 🌍")

# 상태 표시
user_doc = db.collection("users").document(USER_ID).get()
if user_doc.exists:
    user_data = user_doc.to_dict()
else:
    user_data = {}

is_paid = user_data.get("is_paid", False)
usage_count = user_data.get("usage_count", 0)
remaining_paid = user_data.get("remaining_paid_uses", BASIC_LIMIT) if is_paid else None

if is_paid:
    st.markdown(f"💎 Premium User — Remaining {remaining_paid} chats")
else:
    st.markdown(f"🌱 Free Trial — Remaining {max(DAILY_FREE_LIMIT-usage_count,0)} chats")

# 무료 리셋 체크
last_reset = datetime.fromisoformat(user_data.get("last_reset", datetime.utcnow().isoformat()))
if (datetime.utcnow() - last_reset).total_seconds()/3600 >= RESET_INTERVAL_HOURS:
    db.collection("users").document(USER_ID).update({
        "usage_count": 0,
        "last_reset": datetime.utcnow().isoformat()
    })
    usage_count = 0
    st.info("⏰ Free sessions have been reset!")

# 사용자 입력
user_input = st.chat_input("How are you feeling right now? / 지금 기분을 말씀해 주세요")
if user_input:
    # 사용자 말풍선
    st.markdown(f"<div class='user-bubble'>{user_input}</div>", unsafe_allow_html=True)

    lang_code = detect_language(user_input)
    translated_input = translate_to_en(user_input)
    emotion_score = analyze_emotion(user_input)
    db.collection("emotions").add({
        "uid": USER_ID,
        "text": user_input,
        "score": emotion_score,
        "time": datetime.utcnow().isoformat()
    })

    # AI 응답
    system_prompt = ("You are a warm, empathetic counselor...")  # 생략
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":translated_input}
        ],
        temperature=0.9,
        max_tokens=700
    )
    answer_en = resp.choices[0].message.content
    answer = translate_from_en(answer_en, lang_code)

    # 봇 말풍선
    st.markdown(f"<div class='bot-bubble'>{answer}💫</div>", unsafe_allow_html=True)

    # 저장
    db.collection("chats").add({
        "uid": USER_ID,
        "input": user_input,
        "reply": answer,
        "lang": lang_code,
        "emotion_score": emotion_score,
        "created_at": datetime.utcnow().isoformat()
    })

    # 사용량 차감 + 유료유도
    if is_paid:
        db.collection("users").document(USER_ID).update({
            "remaining_paid_uses": remaining_paid-1
        })
    else:
        db.collection("users").document(USER_ID).update({
            "usage_count": usage_count+1
        })

    # 제휴/광고 노출 조건 체크
    maybe_show_ad()

# ---------------------------
# Footer with Payment & Affiliate
# ---------------------------
st.markdown("---")
st.markdown(f"""
<div style='text-align:center; opacity:0.9'>
    💌 To upgrade: <a href="{PAYPAL_URL}" target="_blank">PayPal</a> & send screenshot.<br>
    🌐 Or check our partner offer: <a href="{AFFILIATE_URL}" target="_blank">See special benefit</a><br>
    Version {APP_VERSION} • Built with caring heart 💙
</div>
""", unsafe_allow_html=True)
