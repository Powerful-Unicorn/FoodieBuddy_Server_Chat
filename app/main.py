import os
import re

import openai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# 랭체인 관련 import들
from langchain_openai import ChatOpenAI
from starlette.middleware.cors import CORSMiddleware

from app.chat.recommendation import dishimg_gen
from app.database import fetch_user

# main.py는 FastAPI 프로젝트의 전체적인 환경을 설정하는 파일
# 포트번호는 8000
app = FastAPI()

# 환경 변수 로드 (API 키 등)
openai.api_key = os.getenv("OPENAI_API_KEY")
ingredients_api_key = os.getenv("INGREDIENTS_API_KEY")
serp_api_key = os.getenv("SERP_API_KEY")
stability_api_key = os.getenv("STABILITY_API_KEY")

#########
# 이부분 db의 dietary restriction을 가져오는 코드로 수정해야함
user_sample = [
    {"name": "John",
     "diet": {"meat": ["red meat", "other meat"],
              "seafood": ["shrimp"],
              "gluten(wheat)": []
              }},
    {"name": "Julia",
     "diet": {"meat": ["red meat"],
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

####################################################################################################################################

# WebSocket 핸들러
@app.websocket("/recommendation")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # 웹소켓 연결 accept

    # 1. 채팅 상호작용 시작 전
    model = ChatOpenAI(model="gpt-4o")
    chat_history = ChatMessageHistory()

    recommend_prompt = f"""
      ## Instructions
      You are a kind expert in Korean cuisine. You will chat with a user in English to recommend a dish to the user based on the user's dietary restrictions and additional information.
      The user's dietary restrictions are {str_user_diet}. 

      Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
      For example, "**Kimchi Stew(Kimchi Jjigae)**", "**Grilled Pork Belly(Samgyeopsal)**".

      Everytime you ask a question use linebreaks before the question.
      For example, "Hello! I'm excited to help you explore some delicious Korean cuisine. Please let me know what type of dish you're interested in trying!

      Are you looking for something spicy, mild, savory, or maybe a specific type like a soup or a noodle dish?"
      Or, "Hello! I'm excited to help you explore some delicious Korean cuisine. 

      Could you please let me know what type of dish you're interested in trying today?"

      Follow the steps below:
      1. Start the conversation and ask which type of dish the user wants to try.
      2. Based on the user's answer and user's dietary restrictions, suggest a dish what the user can eat for the meal. 
         YOU MUST SAY ONLY IN THE FORM BELOW INCLUDING LINEBREAKS.:
         "[The pronunciation of the korean dish name(The dish name in English)] **The dish name in English(The pronunciation of its korean name)**
         The basic information of the dish in one sentence.

         The main ingredients of the dish in one sentence. The information related to the user's dietary restrictions in one sentence.

         Several hashtags related to the dish."

         For example, "[Kimchi Jjigae(Kimchi Stew)] **Kimchi Stew(Kimchi Jjigae)**
         It is a classic Korean dish that's perfect for those who enjoy a spicy and warming meal.

         It's made with fermented kimchi, tofu, and various vegetables, simmered together to create a rich and flavorful broth. It's traditionally made with pork, but it can easily be adapted to fit your dietary restrictions by leaving out the meat.

         #spicy #polular #warm"
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

            if response.content.startswith("["):  # 메뉴 이미지 생성하는 코드
                dish_name = re.search(r'\[([\D]+)\]', response.content).group(1)
                image_bytes = dishimg_gen(dish_name)
                response.content = response.content[len(dish_name) + 2:].lstrip()

                try:
                    await websocket.send_bytes(image_bytes)  # 바이너리 데이터 전송
                except Exception as e:
                    await websocket.send_text(f"Error: {str(e)}")

            await websocket.send_text(response.content)  # 챗봇이 한 말 send
            chat_history.add_ai_message(response.content)

            user_message = await websocket.receive_text()  # 유저가 한 말 receive
            if user_message.lower() == 'x':
                await websocket.send_text("Chat ended.")  # 챗봇이 한 말 send
                break
            chat_history.add_user_message(user_message)
        # return chat_history.messages

    except WebSocketDisconnect:
        print("Client disconnected")


@app.websocket("/askdish")
async def websocket_endpoint(websocket: WebSocket):  # askdish
    await websocket.accept()  # 웹소켓 연결 accept

    # 1. 채팅 상호작용 시작 전
    model = ChatOpenAI(model="gpt-4o")
    chat_history = ChatMessageHistory()

    # askdish용 프롬프트
    askdish_prompt = f"""
    ## Instructions
    You are a kind expert in Korean cuisine. You will chat with a user in English to help them understand a dish at a restaurant based on the user's dietary restrictions.
    The user's dietary restrictions are {str_user_diet}. 

    First, explain the dish from the image.
    Next, check if the user have any question. If user ask any questions about the dish, explain it kindly.
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", askdish_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    chain = prompt | model

    # 2. 채팅 상호작용 시작 (while문 안에서 ai 와 user 가 메시지 주고받는 과정 반복)
    try:
        await websocket.send_text("Please upload an image of a dish! :)")  # 챗봇이 한 말 send
        image_data = await websocket.receive_text()

        # 대화 시작 멘트 - 밑반찬 설명
        from app.chat.askdish import get_img_response
        dish_explain = get_img_response(image_data, str_user_diet)
        await websocket.send_text(dish_explain)
        chat_history.add_ai_message(dish_explain)

        while True:
            user_message = await websocket.receive_text()  # 유저가 한 말 receive
            if user_message.lower() == 'x':
                await websocket.send_text("Chat ended.")  # 챗봇이 한 말 send
                break
            chat_history.add_user_message(user_message)

            response = chain.invoke({"messages": chat_history.messages})
            await websocket.send_text(response.content)  # 챗봇이 한 말 send
            chat_history.add_ai_message(response.content)
        # return chat_history.messages



    except WebSocketDisconnect:
        print("Client disconnected")


@app.websocket("/askmenu")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # 웹소켓 연결 accept

    # 1. 채팅 상호작용 시작 전
    model = ChatOpenAI(model="gpt-4o")
    chat_history = ChatMessageHistory()

    # askmenu용 프롬프트
    askmenu_prompt = f"""
    You are a kind expertin Korean cuisine. You will chat with a user in English to help them choose a dish at a restaurant based on the user's dietary restrictions.
    The user's dietary restrictions are {str_user_diet}.
    If the user asks any questions during the conversation, kindly answer them and continue the dialogue.
    Using the instructions below, perform the following steps:

    1. You will be given a list of dish names. Start the conversation by briefly explaining each dish in one sentence.
    2. Ask the user which dish they want to order and wait for their response.
    3. Based on the user's choice, you must start your output with "[the dish name(English)]" and explain the dish in detail, considering the user's dietary restrictions.
    4. Ask if the user would like to order the dish.
    5. If the user wants to order the dish, continue to step 6. If not, return to step 2 and provide the list and brief explanations again.
    6. Ask if the user has any questions about the dish.
    7. End the conversation.
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", askmenu_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    chain = prompt | model

    # 2. 채팅 상호작용 시작 (while문 안에서 ai 와 user 가 메시지 주고받는 과정 반복)
    try:
        await websocket.send_text("Please upload an image of a menu board! :)")  # 챗봇이 한 말 send
        # 1) 이미지 데이터 받기
        image_data = await websocket.receive_text()
        from app.chat.askmenu import get_img_response
        menu_explain = get_img_response(image_data, str_user_diet)

        # 2) 이미지 데이터 -> 이미지 인식 ~ 메뉴 설명 내용 생성 -> chat_history에 전달 (!!!챗봇으로 출력은 XXX!!!)
        system_message = SystemMessage(content=menu_explain)
        chat_history.add_message(system_message)
        print(chat_history.messages)  # 챗봇으로 출력하는 내용 아님. chat_history에만 저장

        while True:
            response = chain.invoke({"messages": chat_history.messages})
            await websocket.send_text(response.content)  ## 텍스트 전송
            chat_history.add_ai_message(response.content)

            if response.content.startswith("["):
                dish_name = re.search(r'\[([\D]+)\]', response.content).group(1)
                image_bytes = dishimg_gen(dish_name)  ## send
                try:
                    await websocket.send_bytes(image_bytes)  # 바이너리 데이터 전송 (텍스트 전송이랑 순서 바꾸기?)
                except Exception as e:
                    await websocket.send_text(f"Error: {str(e)}")

            user_message = await websocket.receive_text()  # 유저가 한 말 receive

            if user_message.lower() == 'x':
                await websocket.send_text("Chat ended.")  # 챗봇이 한 말 send
                break
            chat_history.add_user_message(user_message)

        # return chat_history.messages

    except WebSocketDisconnect:
        print("Client disconnected")


####################################################################################################################################

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


@app.get(("/user"))
def get_user():
    fetch_user()
