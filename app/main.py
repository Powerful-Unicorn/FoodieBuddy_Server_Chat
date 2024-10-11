from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import openai
import os
import re
import requests
import xml.etree.ElementTree as ET
from starlette.middleware.cors import CORSMiddleware

from app.config import app  # 여기서 app을 import
from app.chatbot import get_chat_response

from bs4 import BeautifulSoup

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
ingredients_api_key = os.getenv("INGREDIENTS_API_KEY")
serp_api_key = os.getenv("SERP_API_KEY")
stability_api_key = os.getenv("STABILITY_API_KEY")


def search_ingredients(dish_name):
    print("search_ingredients>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    model = ChatOpenAI()

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Translate a korean dish name in korean without any explanation. Your answer MUST be a one korean word. Examples - Q:Kimchi jjigae A:김치찌개, Q:Tteokbokki A:떡볶이"),
        ("user", "Q:{dish_name} A:"),
    ])

    chain = chat_prompt | model | StrOutputParser()

    response = chain.invoke({"dish_name": f"{dish_name}", })

    url = 'http://apis.data.go.kr/1390802/AgriFood/FdFood/getKoreanFoodFdFoodList'
    myKey = 'API key'
    params = {'serviceKey': f'6KMoh6rjEGBq/v8QvaX/3/KAj0DppT17EgLbwzR1IrrWDX+yiTuMtBEgo35a9fgZHz+5aW/wzd0Kv4RDo7Zuyg==',
              'service_Type': 'xml', 'Page_No': '1', 'Page_Size': '20', 'food_Name': response}

    ingredients_response = requests.get(url, params=params)

    xml_data = ingredients_response.content
    root = ET.fromstring(xml_data)

    result_msg_element = root.find('.//result_Msg')

    if result_msg_element is not None and result_msg_element.text == '요청 데이터 없음':
        return ""
    else:
        item = root.find('body/items').findall('item')[0]
        food_List = item.find('food_List').findall('food')

        ingredients = ""
        count_item = 0

        for food in food_List:
            fd_Eng_Nm = food.find('fd_Eng_Nm').text
            ingredient = fd_Eng_Nm.split(',')[0]

            if count_item == 0:
                ingredients = ingredient
            else:
                ingredients = ingredients + ", " + ingredient
                if count_item == 4: break

            count_item += 1

        print("search_ingredients<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        return "Main ingredients are " + ingredients


def google_search(query):
    print("google_search>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    search_url = f"https://serpapi.com/search.json?q={query}&api_key={serp_api_key}"
    response = requests.get(search_url)
    print("google_search<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    return response.json()


def scrape_website(url):
    print("scrape_website>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    directions_section = soup.find('h2', string='Directions')  # 'Directions' 섹션 찾기
    recipe_list = directions_section.find_all_next('ol')  # 모든 <ol> 찾기
    recipe = ""

    if directions_section is not None:
        recipe_list = directions_section.find_all_next('ol')  # 모든 <ol> 찾기

        for i in range(len(recipe_list)):
            if i == len(recipe_list) - 1: break
            list_items = recipe_list[i].find_all('li')  # <ol> 안의 모든 <li> 추출
            recipe += f"\n#{i + 1}"
            for i, item in enumerate(list_items, 1):
                recipe += f"\n{i}. {item.get_text(strip=True)}"

    print("scrape_website<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    return recipe


def search_recipe(dish_name):
    print("search_recipe>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    search_results = google_search(f"How to cook {dish_name}")

    print("print(search_results)>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(search_results)  # search_results가 반환하는 데이터를 확인합니다. 디버깅용 출력
    print("print(search_results)<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

    url = next((result['link'] for result in search_results['organic_results'] if
                result['link'].startswith('https://www.maangchi.com')), None)

    if url is None:
        print("search_recipe<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        return ""

    recipe = scrape_website(url)
    print("search_recipe<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    return "Generate the image based on the recipe below:" + recipe


def dishimg_gen(dish_name) -> bytes:  # 바이트 스트림 타입을 return
    print("dishimg_gen>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    dish_name = dish_name.replace("[", "").replace("]", "")  # dish_name에서 대괄호 제거
    sd_prompt = f"A realistic image of {dish_name}"  # 프롬프트

    # sd_prompt에 재료 및 레시피 추가
    sd_prompt += search_ingredients(dish_name)
    sd_prompt += search_recipe(dish_name)

    print("print(sd_prompt)>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(sd_prompt)  # 디버깅용 출력
    print("print(sd_prompt)<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    # Stability AI API 요청
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
        headers={
            "authorization": f"{stability_api_key}",
            "accept": "image/*"
        },
        files={"none": ''},
        data={
            "prompt": sd_prompt,
            # "output_format": "png",
        },
    )

    if response.status_code == 200:  # 응답이 성공적이면 바이트 스트림을 바로 return (파일로 변환한 후 저장하는 코드 x)
        print("dishimg_gen<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        return response.content
    # filename = dish_name.lower().replace(" ", "")
    # with open(f"./{filename}_test.txt", 'wb') as file:
    #   file.write(response.content)

    else:
        print("dishimg_gen<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        raise Exception(str(response.json()))



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
         In this step, YOU MUST START YOUR OUTPUT WITH "[THE DISH NAME IN ENGLISH]". Then explain the dish in detail. For example, "[Kimchi Stew] Kimchi Stew(Kimchi Jjigae) is ...(continue)...."
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

            if response.content.startswith("["):  # 메뉴 이미지 생성하는 코드
                dish_name = re.search(r'\[([\D]+)\]', response.content).group(1)
                image_bytes = dishimg_gen(dish_name)
                response.content = response.content[len(dish_name) + 2:].lstrip()

                try:
                    await websocket.send_bytes(image_bytes)  # 바이너리 데이터 전송
                except Exception as e:
                    await websocket.send_text(f"Error: {str(e)}")

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
