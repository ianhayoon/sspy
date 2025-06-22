import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
import matplotlib
import requests
import re
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# 한글 폰트 설정
matplotlib.rcParams['font.family'] = 'Malgun Gothic'  # Windows 기본 한글 폰트

# 환경 변수 불러오기
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

st.set_page_config(page_title="SafeScope: AI 극단화 감지", layout="centered")
st.title("🔍 SafeScope: 극단화 위험 분석 챗봇")
st.markdown("청소년이 노출된 텍스트, 기사, 영상 콘텐츠를 입력하면 AI가 극단화 위험을 분석해줍니다.")

# 유튜브 링크에서 video_id 추출 함수
def extract_video_id(url):
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc:
        query = parse_qs(parsed.query)
        return query.get('v', [None])[0]
    elif 'youtu.be' in parsed.netloc:
        return parsed.path.lstrip('/').split('?')[0]
    return None

# 입력 탭 구성
tab1, tab2 = st.tabs(["📝 직접 입력", "🔗 기사/영상 링크"])

user_input = ""

with tab1:
    text_input = st.text_area("✍️ 분석할 텍스트 입력", height=200)
    if text_input.strip():
        user_input = text_input

with tab2:
    url_input = st.text_input("🔗 기사나 유튜브 영상 링크 입력")
    if url_input:
        if "youtube.com" in url_input or "youtu.be" in url_input:
            try:
                video_id = extract_video_id(url_input)
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = transcript_list.find_transcript(['ko', 'en'])
                transcript_text = " ".join([t.text for t in transcript.fetch()])
                user_input = transcript_text
                if not transcript_text.strip():
                    st.warning("⚠️ 자막이 비어 있습니다. 자막이 없는 영상일 수 있어요.")
                else:
                    st.success("🎬 유튜브 자막 추출 성공!")
            except Exception as e:
                st.error("자막을 불러오는 데 실패했습니다: " + str(e))
        else:
            try:
                page = requests.get(url_input)
                if page.ok:
                    soup = BeautifulSoup(page.text, "html.parser")
                    paragraphs = soup.find_all("p")
                    user_input = " ".join([p.text for p in paragraphs])
                    st.success("📰 기사 본문 추출 성공!")
            except Exception as e:
                st.error("페이지에서 텍스트를 추출할 수 없습니다: " + str(e))

# 분석 함수
def analyze_text(text):
    prompt = f"""
    다음 콘텐츠에서 혐오, 이분법, 선동적 표현, 편향된 감정 등을 분석하여 극단화 가능성을 0~100점으로 평가해줘.

    콘텐츠:
{text}

    응답 형식:
    1. 극단화 점수 (0~100):
    2. 감정 요약:
    3. 위험 키워드:
    4. 조언:
    """
    response = model.generate_content(prompt)
    return response.text

# 분석 실행
if st.button("🔎 분석 시작"):
    if not user_input.strip():
        st.warning("내용을 입력하거나 링크를 제공해주세요.")
    else:
        with st.spinner("AI가 콘텐츠를 분석 중입니다..."):
            result = analyze_text(user_input)

        st.subheader("📋 분석 결과")
        st.markdown(result)

        try:
            score_match = re.search(r"극단화 점수.*?:\s*(\d{1,3})", result)
            score = int(score_match.group(1)) if score_match else 0

            st.subheader("📊 시각화: 극단화 점수")
            fig, ax = plt.subplots(figsize=(6, 2))
            bar_color = 'crimson' if score > 70 else 'orange' if score > 40 else 'green'
            ax.barh(["극단화 정도"], [score], color=bar_color)
            ax.set_xlim(0, 100)
            ax.set_xlabel("점수", fontsize=12)
            ax.tick_params(axis='y', labelsize=12)
            fig.tight_layout(pad=2.0)
            st.pyplot(fig)

        except Exception as e:
            st.info("시각화를 생성할 수 없습니다. 응답 형식을 확인해주세요.")
