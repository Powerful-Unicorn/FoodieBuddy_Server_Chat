import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
# 랭체인 관련 import들
from langchain_openai import ChatOpenAI


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
    params = {'serviceKey': '',
              'service_Type': 'xml', 'Page_No': '1', 'Page_Size': '20', 'food_Name': response}

    ingredients_response = requests.get(url, params=params)

    xml_data = ingredients_response.content
    root = ET.fromstring(xml_data)

    result_msg_element = root.find('.//result_Msg')

    if result_msg_element is None or result_msg_element.text == '요청 데이터 없음':
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
        return "\nMain ingredients are " + ingredients


def google_search(query):
    print("google_search>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    search_url = f"https://serpapi.com/search.json?q={query}&api_key=d123f6ebd427f365cdab180754399edcd536d81fa81a13454ae4c17f4d700f04"
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
    return "\nGenerate the image based on the recipe below:" + recipe


def dishimg_gen(dish_name) -> bytes:  # 바이트 스트림 타입을 return
    print("dishimg_gen>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    dish_name = dish_name.replace("[", "").replace("]", "")  # dish_name에서 대괄호 제거
    if dish_name == "Patbingsu": dish_name = "Bingsu"
    sd_prompt = f"A realistic image of {dish_name}"  # 프롬프트

    # sd_prompt에 재료 및 레시피 추가
    # sd_prompt += search_ingredients(dish_name)
    # sd_prompt += search_recipe(dish_name)

    print("print(sd_prompt)>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(sd_prompt)  # 디버깅용 출력
    print("print(sd_prompt)<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    # Stability AI API 요청
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
        headers={
            "authorization": "",
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
