import streamlit as st
from datetime import datetime, timedelta

# 2시간 후 시각 계산
unlock_time = datetime.utcnow() + timedelta(hours=2)
unlock_str = unlock_time.strftime("%Y-%m-%d %H:%M:%S UTC")

# 언어 선택 (원하는대로 바꾸세요)
language = st.radio("Select Language / 언어 선택", ["English 🇺🇸", "한국어 🇰🇷"], horizontal=True)

if language == "English 🇺🇸":
    st.title("⚠️ Please Wait a Moment")
    st.markdown(
        f"""
        The system is currently undergoing maintenance.  
        Please come back after approximately 4 hours, at **{unlock_str}**.  

        We apologize for the inconvenience.  
        We'll be back soon with a better experience 💙
        """,
        unsafe_allow_html=True,
    )
else:
    st.title("⚠️ 잠시만 기다려 주세요")
    st.markdown(
        f"""
        현재 시스템 점검 중입니다.  
        약 4시간 후인 **{unlock_str}** 에 다시 찾아와 주세요.  

        불편을 드려 정말 죄송합니다.  
        곧 더 좋은 모습으로 찾아뵐게요 💙
        """,
        unsafe_allow_html=True,
    )
