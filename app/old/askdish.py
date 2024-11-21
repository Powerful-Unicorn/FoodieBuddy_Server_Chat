import base64
import imghdr
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_img_response_prompt(param_dict):
    system_message = """You are a kind expert in Korean cuisine. You will explain a user in English to help the user understand a dish at a korean restaurant.
  Your explanation must be based on the user's dietary restrictions. Explain it in 3 or 4 sentences.
  YOU MUST SAY IT SIMPLY BUT KINDLY.
  
  First Sentence: Explain the name and the category of the dish.
  Second Sentence: Explain the ingredients based on the user's dietary restrictions.
  Third Sentence: Let the user know if the user can eat it of not.
  (If there are any cautions, Fourth Sentence: Let the user know which ingredients the user should check.)
  """
    human_message = [
        {
            "type": "text",
            "text": f"{param_dict['question']}",

        },
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
    # 밑반찬 답변 모델 - 파인 튜닝하면 여기에 쓸 모델 id가 바뀜
    model = ChatOpenAI(model="gpt-4o")

    extension = imghdr.what(None, h=image_byte)  # image_data의 확장자 확인
    print(f"Detected extension: {extension}")
    # print(f"image_url : data:image/{extension};base64,{image_data}")
    image_base64 = base64.b64encode(image_byte).decode('utf-8')  # 인코딩된 결과는 bytes이므로, 이를 문자열로 변환해 줍니다.

    chain = get_img_response_prompt | model | StrOutputParser()
    response = chain.invoke({"diet": str_user_diet,
                             "image_url": f"data:image/{extension};base64,{image_base64}"
                             }
                            )
    return response
