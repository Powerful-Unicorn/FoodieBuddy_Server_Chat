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

async def get_chat_response(message: str) -> str:
    response = openai.ChatCompletion.create(  # ChatCompletion 사용
        model="gpt-4o",  # GPT-4o 모델 사용
        messages=[{"role": "user", "content": message}]  # 메시지 리스트 전달
    )
    return response['choices'][0]['message']['content']  # 응답의 메시지 부분 반환


async def get_chat_response1(message: str) -> str:
    model = ChatOpenAI(model="gpt-4o")
    chat_history = ChatMessageHistory()

    recommend_prompt = f"""
      ## Instructions
      You are a kind expert in Korean cuisine. You will chat with a user in English to recommend a dish to the user based on the user's dietary restrictions and additional information.
      The user's dietary restrictions are {str_user_diet}.

      You should start the conversation and ask which type of dish the user want to try.
      Based on the user's answer, suggest a dish what the user can eat for the meal. You must start your output with "[the dish name in English]". For example, "[Kimchi Stew]". Then explain the dish in detail.

      If the user don't like the suggestion, ask the reason and suggest another dish.
      If the user decide what to eat, end the conversation.
      """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", recommend_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    chain = prompt | model

    while True:
        response = chain.invoke({"messages": chat_history.messages})
        chat_history.add_ai_message(response.content)

        # if response.content.startswith("["):
        #     dish_name = re.search(r'\[([\D]+)\]', response.content).group(1)
        #     dishimg_gen(dish_name)
        #     response.content = response.content[len(dish_name) + 2:].lstrip()

        print(f"FoodieBuddy:{response.content}")

        user_message = input("You: ")
        if user_message.lower() == 'x':
            print("Chat ended.")
            break
        chat_history.add_user_message(user_message)

    return chat_history.messages


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

recommend_history = recommendation(str_user_diet)
