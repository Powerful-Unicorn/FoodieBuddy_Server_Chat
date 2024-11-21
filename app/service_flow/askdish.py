import base64
import imghdr
import os
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.database.database import get_rds_connection

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")


def search_ingredients(dish_name):
    model = ChatOpenAI()

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Translate a korean dish name in korean without any explanation. Your answer MUST be a one korean word. Examples - Q:Kimchi Jjigae (Kimchi Stew) A:김치찌개, Q:Samgyeopsal (Grilled Pork Belly) A:삼겹살"),
        ("user", "Q:{dish_name} A:"),
    ])

    chain = chat_prompt | model | StrOutputParser()

    response = chain.invoke({"dish_name": f"{dish_name}", })

    url = 'http://apis.data.go.kr/1390802/AgriFood/FdFood/getKoreanFoodFdFoodList'
    myKey = 'apikey'
    params = {'serviceKey': myKey, 'service_Type': 'xml', 'Page_No': '1', 'Page_Size': '20', 'food_Name': response}

    ingredients_response = requests.get(url, params=params)

    xml_data = ingredients_response.content
    root = ET.fromstring(xml_data)

    result_msg_element = root.find('.//result_Msg')

    if result_msg_element is None or result_msg_element.text == '요청 데이터 없음':
        return "No information"
    else:
        item = root.find('body/items').findall('item')[0]
        food_List = item.find('food_List').findall('food')

        ingredients = ""

        for food in food_List:
            fd_Eng_Nm = food.find('fd_Eng_Nm').text
            ingredient = fd_Eng_Nm.split(',')[0]

            if ingredients == "":
                ingredients = ingredient
            else:
                ingredients = ingredients + ", " + ingredient

        return f"Ingredients of {dish_name} are " + ingredients


def get_img_response_prompt(param_dict):
    system_message = """You are a kind expert in Korean cuisine. What is the name of the korean side dish in the image?
  
  YOU MUST USE THIS FORM: The dish name in English (The pronunciation of its korean name). 
  For example, "Kimchi Jjigae (Kimchi Stew)", "Samgyeopsal (Grilled Pork Belly)".
  """
    human_message = [
        {
            "type": "text",
            "text": f"{param_dict['diet']}",

        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"{param_dict['image_url']}",
            }
        }
    ]

    return [SystemMessage(content=system_message), HumanMessage(content=human_message)]


def get_img_response(image_byte, str_user_info):
    model = ChatOpenAI(model="gpt-4o")

    extension = imghdr.what(None, h=image_byte)  # image_data의 확장자 확인
    print(f"Detected extension: {extension}")
    image_base64 = base64.b64encode(image_byte).decode('utf-8')  # 인코딩된 결과는 bytes이므로, 이를 문자열로 변환해 줍니다.
    # print(f"image_url : data:image/{extension};base64,{image_base64}")  # 이 프린트문 출력 겁나 긺

    chain = get_img_response_prompt | model | StrOutputParser()
    response = chain.invoke({"diet": str_user_info,
                             "image_url": f"data:image/{extension};base64,{image_base64}"
                             }
                            )
    return response


async def askdish_chat(user_id: int, websocket: WebSocket):
    # 1. 채팅 상호작용 시작 전
    # 채팅 사용 모델 - 파인 튜닝하면 여기에 쓸 모델 id가 바뀜
    model = ChatOpenAI(model="gpt-4o")
    chat_history = ChatMessageHistory()

    str_user_info = get_user_info(user_id)

    # askdish용 프롬프트
    askdish_prompt = f"""
  ## Instructions
  You are a kind expert in Korean cuisine. You will chat with a user in English to explain a korean side dish to the user based on the user's dietary restrictions.
  The user is a foreigner visiting a Korean restaurant in Korea.
  The user's dietary restrictions are {str_user_info}. 
  
  Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
  For example, "**Kimchi Stew(Kimchi Jjigae)**", "**Grilled Pork Belly(Samgyeopsal)**".

  Follow the steps below:
  1. You will be given a dish name and the its ingredients from the system. Using these information, Explain the dish from the image.
     YOU MUST SAY ONLY IN THE FORM BELOW INCLUDING LINEBREAKS.:
     "The basic information of the dish in one sentence.
     
      The main ingredients of the dish in one sentence. The information related to the user's dietary restrictions in one sentence.
      Whether it is suitable for the user or not.
      
      Several hashtags related to the dish."
      For example, "This dish is Braised Burdock Root(Ueongjorim), a type of side dish made with burdock root.
      
      It typically includes burdock root, soy sauce, sugar, sesame oil, and sometimes garlic. Since you avoid gluten, you should check if the soy sauce used in this preparation is gluten-free. 
      If it contains regular soy sauce, it might not be suitable for you.
      
      #healthy #side_dish #vegetable"
  2. Check if the user have any question. If user ask any questions about the dish, explain it kindly.
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
        image_byte = await websocket.receive_bytes()  # 이미지 (바이너리) 수신

        # 대화 시작 멘트 - 밑반찬 설명
        dish_name = get_img_response(image_byte, str_user_info)
        system_message = SystemMessage(content=dish_name)
        chat_history.add_message(system_message)

        ingredients = search_ingredients(dish_name)
        ingredients_message = SystemMessage(content=ingredients)
        chat_history.add_message(ingredients_message)

        while True:
            response = chain.invoke({"messages": chat_history.messages})
            chat_history.add_ai_message(response.content)
            await websocket.send_text(response.content)

            user_message = await websocket.receive_text()  # 유저가 한 말 receive
            if user_message.lower() == 'x':
                await websocket.send_text("Chat ended.")  # 챗봇이 한 말 send
                break
            chat_history.add_user_message(user_message)

        return chat_history.messages

    except WebSocketDisconnect:
        print("Client disconnected")


def get_user_info(user_id: int):
    connection = get_rds_connection()
    # connection = get_localdb_connection()

    # 유저 한명 식이제한 불러오기
    cursor = connection.cursor()
    cursor.execute("SHOW COLUMNS FROM user")
    diets_list_dic = cursor.fetchall()

    # 변환 코드
    diets_list = tuple(
        (
            item['Field'],  # Field
            item['Type'],  # Type
            item['Null'],  # Null
            item['Key'],  # Key
            item['Default'],  # Default
            item['Extra']  # Extra
        )
        for item in diets_list_dic
    )

    cursor.execute(f"SELECT * FROM user Where user_id = {user_id}")
    result_dic = cursor.fetchall()
    result = (tuple(result_dic[0].values()),)
    user_diets = list(result[0])
    user_info = {}

    for i in range(len(diets_list)):
        if diets_list[i][0] not in ('user_id', 'email', 'password', 'username'):
            user_info[diets_list[i][0]] = user_diets[i]

    str_user_diet = f"Religion: {user_info['religion']}, Vegetarian: {user_info['vegetarian']}. Details: "
    for k, v in user_info.items():
        if k == 'vegetarian' or k == 'religion':
            continue
        if v is None or v == b'\x00':
            continue

        if v == b'\x01':
            str_user_diet += k + ', '
        else:
            str_user_diet += k + ':' + v + ', '

    str_user_diet = str_user_diet[:-2] + '.'

    return str_user_diet
