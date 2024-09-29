from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import openai
import os
from starlette.middleware.cors import CORSMiddleware

from app.config import app  # 여기서 app을 import
from app.chatbot import get_chat_response


# main.py는 FastAPI 프로젝트의 전체적인 환경을 설정하는 파일
# 포트번호는 8000
app = FastAPI()

# 환경 변수 로드 (API 키 등)
openai.api_key = os.getenv("OPENAI_API_KEY")

# WebSocket 핸들러
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # ChatGPT API로 응답 가져오기
            response = await get_chat_response(data)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        print("Client disconnected")


origins = [ # 여기에 허용할 프론트 접근을 추가하면 되는듯
    "http://localhost:5173" ,  # 또는 "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/hello")  # /hello url로 요청이 발생하면 아래의 함수를 실행
def hello():
    return {"message": "안녕하세요 파이보"}  # <- 이건 딕셔너리 형식, 근데 자동으로 json 형태로 바뀌어서 response 보냄
