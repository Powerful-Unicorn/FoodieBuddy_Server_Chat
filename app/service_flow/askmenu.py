import base64
import imghdr
import os
import re
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.collaborative_filtering import get_user_info

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
INGREDIENTS_API_KEY = os.getenv("INGREDIENTS_API_KEY")


def search_ingredients(dish_name):
    model = ChatOpenAI(model="gpt-4o")

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Translate a korean dish name in korean without any explanation. Your answer MUST be a one korean word. Examples - Q:Kimchi Jjigae (Kimchi Stew) A:김치찌개, Q:Samgyeopsal (Grilled Pork Belly) A:삼겹살"),
        ("user", "Q:{dish_name} A:"),
    ])

    chain = chat_prompt | model | StrOutputParser()

    response = chain.invoke({"dish_name": f"{dish_name}", })

    url = 'http://apis.data.go.kr/1390802/AgriFood/FdFood/getKoreanFoodFdFoodList'
    myKey = INGREDIENTS_API_KEY
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


def dishimg_gen(dish_name):
    dish_name = dish_name.replace("[", "").replace("]", "")
    sd_prompt = f"A realistic image of {dish_name}"

    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
        headers={
            "authorization": f"{STABILITY_API_KEY}",
            "accept": "image/*"
        },
        files={"none": ''},
        data={
            "prompt": sd_prompt,
            "output_format": "png",
        },
    )

    if response.status_code == 200:
        filename = dish_name.lower().replace(" ", "")
        with open(f"./{filename}_test.png", 'wb') as file:
            file.write(response.content)

    else:
        raise Exception(str(response.json()))


def gen_get_img_response_prompt(param_dict):
    system_message = "You are a kind korean cuisine expert. Create a list of dish names in the image."

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


def get_img_response(image_byte, str_user_diet):
    model = ChatOpenAI(model="gpt-4o")

    # image_binary = base64.b64decode(image_data)
    extension = imghdr.what(None, h=image_byte)  # image_data의 확장자 확인
    print(f"Detected extension: {extension}")
    # print(f"image_url : data:image/{extension};base64,{image_data}")
    image_base64 = base64.b64encode(image_byte).decode('utf-8')  # 인코딩된 결과는 bytes이므로, 이를 문자열로 변환해 줍니다.

    chain = gen_get_img_response_prompt | model | StrOutputParser()
    response = chain.invoke({"diet": str_user_diet,
                             "image_url": f"data:image/{extension};base64,{image_base64}"
                             }
                            )
    return response


async def askmenu_chat(user_id: int, websocket: WebSocket):
    # 1. 채팅 상호작용 시작 전
    model = ChatOpenAI(model="gpt-4o")
    chat_history = ChatMessageHistory()

    str_user_diet = get_user_info(user_id)

    await websocket.send_text("Please upload an image of a menu board! :)")  # 챗봇이 한 말 send
    # 1) 이미지 데이터 받기
    image_byte = await websocket.receive_bytes()

    menu_explain = get_img_response(image_byte, str_user_diet)
    system_message = SystemMessage(content=menu_explain)

    chat_history.add_message(system_message)

    # askmenu용 프롬프트
    askmenu_prompt = f"""
  You are a kind expert in Korean cuisine. You will chat with a user in English to help them choose a dish at a restaurant based on the user's dietary restrictions.
  The user's dietary restrictions are {str_user_diet}.
  
  Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
  For example, "**Kimchi Stew(Kimchi Jjigae)**", "**Grilled Pork Belly(Samgyeopsal)**".
  
  Everytime you ask a question use linebreaks before the question.
  
  If the user asks any questions during the conversation, kindly answer them and continue the dialogue.
  
  Follow the steps below:
  1. You will be given a list of dish names. Start the conversation by briefly explaining each dish in one sentence. Make sure there is \n between 'a name of a dish' and 'it's explanation'.
  2. Ask the user which dish they want to order or want to know.
  3. Reform the user's choice as below:
     "[The pronunciation of the korean dish name (The dish name in English)]"
     For example, "[Kimchi Jjigae (Kimchi Stew)]"
  4. After you get the system's message about the ingredients, explain the chosen dish. 
     YOU MUST SAY ONLY IN THE FORM BELOW INCLUDING LINEBREAKS.:
     "**The dish name in English(The pronunciation of its korean name)**
     The basic information of the dish in one sentence.
     
     The main ingredients of the dish in one sentence. The information related to the user's dietary restrictions in one sentence.
     
     Several hashtags related to the dish."
     
     For example, "**Kimchi Stew(Kimchi Jjigae)**
     It is a classic Korean dish that's perfect for those who enjoy a spicy and warming meal.
     
     It's made with fermented kimchi, tofu, and various vegetables, simmered together to create a rich and flavorful broth. It's traditionally made with pork, but it can easily be adapted to fit your dietary restrictions by leaving out the meat.
     
     #spicy #polular #warm"
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

        while True:
            response = chain.invoke({"messages": chat_history.messages})
            chat_history.add_ai_message(response.content)

            if response.content.startswith("["):
                dish_name = re.search(r'\[([\D]+)\]', response.content).group(1)

                ingredients = search_ingredients(dish_name)
                ingredients_message = SystemMessage(content=ingredients)
                chat_history.add_message(ingredients_message)

                response = chain.invoke({"messages": chat_history.messages})
                chat_history.add_ai_message(response.content)

                image_bytes = dishimg_gen(dish_name)
                try:
                    await websocket.send_bytes(image_bytes)  # 바이너리 데이터 전송 (텍스트 전송이랑 순서 바꾸기?)
                except Exception as e:
                    await websocket.send_text(f"Error: {str(e)}")

            await websocket.send_text(response.content)  ## 텍스트 전송

            user_message = await websocket.receive_text()  # 유저가 한 말 receive
            if user_message.lower() == 'x':
                await websocket.send_text("Chat ended.")  # 챗봇이 한 말 send
                break
            chat_history.add_user_message(user_message)

        return chat_history.messages

    except WebSocketDisconnect:
        print("Client disconnected")
