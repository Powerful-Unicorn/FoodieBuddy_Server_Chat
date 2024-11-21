import re

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain_core.messages import SystemMessage
from starlette.middleware.cors import CORSMiddleware

from app.collaborative_filtering import collaborative_filtering
from app.database.database import fetch_user, add_user, fetch_user_diet

# main.py는 FastAPI 프로젝트의 전체적인 환경을 설정하는 파일
# 포트번호는 8000
app = FastAPI()

load_dotenv()


# 환경 변수 로드 (API 키 등)
# openai.api_key = os.getenv("OPENAI_API_KEY")
# ingredients_api_key = os.getenv("INGREDIENTS_API_KEY")
# serp_api_key = os.getenv("SERP_API_KEY")
# stability_api_key = os.getenv("STABILITY_API_KEY")


#######################################################################################################################

@app.websocket("/recommendation/{user_id}")
async def recommendation_endpoint(user_id: int, websocket: WebSocket):
    await websocket.accept()  # 웹소켓 연결 accept

    cf_prompt = collaborative_filtering(user_id)
    print("cf_prompt: " + cf_prompt)

    from app.service_flow.recommendation import recommendation_chat
    await recommendation_chat(user_id, cf_prompt, websocket)


@app.websocket("/askdish/{user_id}")
async def askdish_endpoint(user_id: int, websocket: WebSocket):
    await websocket.accept()  # 웹소켓 연결 accept

    from app.service_flow.askdish import askdish_chat
    await askdish_chat(user_id, websocket)

    # # 1. 채팅 상호작용 시작 전
    # model = ChatOpenAI(model="gpt-4o")
    # chat_history = ChatMessageHistory()

    # # askdish용 프롬프트
    # askdish_prompt = f"""
    # ## Instructions
    # You are a kind expert in Korean cuisine. You will chat with a user in English to help them understand a dish at a restaurant based on the user's dietary restrictions.
    # The user's dietary restrictions are {str_user_info}.
    #
    # First, explain the dish from the image.
    # Next, check if the user have any question. If user ask any questions about the dish, explain it kindly.
    # """

    # prompt = ChatPromptTemplate.from_messages(
    #     [
    #         ("system", askdish_prompt),
    #         MessagesPlaceholder(variable_name="messages"),
    #     ]
    # )

    # chain = prompt | model

    # 2. 채팅 상호작용 시작 (while문 안에서 ai 와 user 가 메시지 주고받는 과정 반복)
    # try:
    # await websocket.send_text("Please upload an image of a dish! :)")  # 챗봇이 한 말 send
    # image_byte = await websocket.receive_bytes()

    # # 대화 시작 멘트 - 밑반찬 설명
    #

    # from app.old.askdish import get_img_response
    # dish_explain = get_img_response(image_byte, str_user_info)
    #     await websocket.send_text(dish_explain)
    #     chat_history.add_ai_message(dish_explain)

    # while True:
    # user_message = await websocket.receive_text()  # 유저가 한 말 receive
    # if user_message.lower() == 'x':
    #     await websocket.send_text("Chat ended.")  # 챗봇이 한 말 send
    #     break
    # chat_history.add_user_message(user_message)

    # response = chain.invoke({"messages": chat_history.messages})
    # await websocket.send_text(response.content)  # 챗봇이 한 말 send
    # chat_history.add_ai_message(response.content)
    # return chat_history.messages

    # except WebSocketDisconnect:
    #     print("Client disconnected")


@app.websocket("/askmenu/{user_id}")
async def askmenu_endpoint(user_id: int, websocket: WebSocket):
    await websocket.accept()  # 웹소켓 연결 accept

    from app.service_flow.askmenu import askmenu_chat
    await askmenu_chat(user_id, websocket)

    # # 1. 채팅 상호작용 시작 전
    # model = ChatOpenAI(model="gpt-4o")
    # chat_history = ChatMessageHistory()

    # str_user_info = get_user_diet(user_id)
    # print("user_info: " + str_user_info)

    # askmenu용 프롬프트
    # askmenu_prompt = f"""
    # You are a kind expertin Korean cuisine. You will chat with a user in English to help them choose a dish at a restaurant based on the user's dietary restrictions.
    # The user's dietary restrictions are {str_user_info}.
    # If the user asks any questions during the conversation, kindly answer them and continue the dialogue.
    # Using the instructions below, perform the following steps:
    #
    # 1. You will be given a list of dish names. Start the conversation by briefly explaining each dish in one sentence.
    # 2. Ask the user which dish they want to order and wait for their response.
    # 3. Based on the user's choice, you must start your output with "[the dish name(English)]" and explain the dish in detail, considering the user's dietary restrictions.
    # 4. Ask if the user would like to order the dish.
    # 5. If the user wants to order the dish, continue to step 6. If not, return to step 2 and provide the list and brief explanations again.
    # 6. Ask if the user has any questions about the dish.
    # 7. End the conversation.
    # """

    # prompt = ChatPromptTemplate.from_messages(
    #     [
    #         ("system", askmenu_prompt),
    #         MessagesPlaceholder(variable_name="messages"),
    #     ]
    # )

    chain = prompt | model

    # 2. 채팅 상호작용 시작 (while문 안에서 ai 와 user 가 메시지 주고받는 과정 반복)
    try:
        await websocket.send_text("Please upload an image of a menu board! :)")  # 챗봇이 한 말 send
        # 1) 이미지 데이터 받기
        image_byte = await websocket.receive_bytes()

        from app.service_flow.askmenu import get_img_response
        menu_explain = get_img_response(image_byte, str_user_info)

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

                from app.service_flow.askmenu import dishimg_gen
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
# 이 아래는 전부 CORS 등과 관련된 설정 및 테스트용 http 메서드


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
    return fetch_user()


@app.get("/user/diet/{user_id}")
def get_user_diet(user_id: int):
    data_list = fetch_user_diet(user_id)

    # 결과를 저장할 리스트
    results = []
    print(data_list)

    # 리스트의 각 딕셔너리에 대해 처리
    for data in data_list:
        # 결과 문자열을 저장할 리스트
        result = []

        # 각 항목을 확인하며 조건에 맞는 항목을 문자열로 추가
        for key, value in data.items():
            if value not in [None, "\u0000", "", b'\x00']:  # None 또는 \u0000은 무시
                if value == b'\x01':  # \u0001이면 key만 추가
                    result.append(key)
                else:  # 그 외의 경우 key: value 형식으로 추가
                    result.append(f"{key}: {value}")

        # 하나의 사용자에 대한 결과를 저장
        results.append(", ".join(result))
        # print(result)
    # print(results)
    for string in results:
        print(string)
        return string


@app.post("/user")
def post_user():
    add_user()
