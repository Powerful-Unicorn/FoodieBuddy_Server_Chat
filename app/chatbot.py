# app/chatbot.py (기존 ChatGPT API 호출 로직 활용)
import openai
import os
from dotenv import load_dotenv
from app.config import app  # app을 다시 여기서 import할 수 있음

# 랭체인 관련 import들
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def get_chat_response(message: str) -> str: # 안쓰게 된 코드
    response = openai.ChatCompletion.create(  # ChatCompletion 사용
        model="gpt-4o",  # GPT-4o 모델 사용
        messages=[{"role": "user", "content": message}]  # 메시지 리스트 전달
    )
    return response['choices'][0]['message']['content']  # 응답의 메시지 부분 반환




