from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import openai
import os
from starlette.middleware.cors import CORSMiddleware

from app.config import app  # 여기서 app을 import
from app.chatbot import get_chat_response

# 랭체인 관련 import들
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# main.py는 FastAPI 프로젝트의 전체적인 환경을 설정하는 파일
# 포트번호는 8000
app = FastAPI()

# 환경 변수 로드 (API 키 등)
openai.api_key = os.getenv("OPENAI_API_KEY")


# WebSocket 핸들러
@app.websocket("/recommendation")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # 웹소켓 연결 accept

    #########

    user_sample = [
        {"name": "John",
         "diet": {"meat": ["red meat", "other meat"],
                  "dairy": ["milk"],
                  "seafood": ["shrimp"],
                  "gluten(wheat)": []
                  }},
        {"name": "Julia",
         "diet": {"meat": ["red meat"],
                  "dairy": ["milk", "cheese"],
                  "honey": [],
                  "nuts": ["peanuts"],
                  "gluten(wheat)": [],
                  "vegetables": ["tomato"]
                  }},
    ]

    user_diet = user_sample[0]["diet"]
    str_user_diet = ""

    for category in user_diet:
        str_user_diet += category + ":"
        for i in user_diet[category]:
            str_user_diet += i + ","

    ###########

    # 1. 채팅 상호작용 시작 전
    model = ChatOpenAI(model="gpt-4o")
    chat_history = ChatMessageHistory()

    recommend_prompt = f"""
      ## Instructions
      You are a kind expert in Korean cuisine. You will chat with a user in English to recommend a dish to the user based on the user's dietary restrictions and additional information.
      The user's dietary restrictions are {str_user_diet}. 

      Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
      For example, "Kimchi Stew(Kimchi Jjigae)", "Grilled Pork Belly(Samgyeopsal)".

      Follow the steps below:
      1. Start the conversation and ask which type of dish the user wants to try.
      2. Based on the user's answer and user's dietary restrictions, suggest a dish what the user can eat for the meal. 
         In this step, YOU MUST START YOUR OUTPUT WITH "[THE DISH NAME IN ENGLISH]". For example, "[Kimchi Stew]"". Then explain the dish in detail.
      3. If the user don't like the suggestion, go back to step 2.
      4. If the user decide what to eat, end the conversation.  
      """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", recommend_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    chain = prompt | model

    # 2. 채팅 상호작용 시작 (while문 안에서 ai 와 user 가 메시지 주고받는 과정 반복)
    try:
        while True:
            response = chain.invoke({"messages": chat_history.messages})  # recommendation 플로우에선 챗봇이 먼저 말함
            chat_history.add_ai_message(response.content)

            # if response.content.startswith("["):
            #     dish_name = re.search(r'\[([\D]+)\]', response.content).group(1)
            #     dishimg_gen(dish_name)
            #     response.content = response.content[len(dish_name) + 2:].lstrip()

            await websocket.send_text(response.content)  # 챗봇이 한 말 send

            user_message = await websocket.receive_text()  # 유저가 한 말 receive
            if user_message.lower() == 'x':
                await websocket.send_text("Chat ended.")  # 챗봇이 한 말 send
                break
            chat_history.add_user_message(user_message)
            # return chat_history.messages

    except WebSocketDisconnect:
        print("Client disconnected")


origins = [  # 여기에 허용할 프론트 접근을 추가하면 되는듯
    "http://localhost:5173",  # 또는 "http://127.0.0.1:5173"
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
