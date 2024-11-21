from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from starlette.middleware.cors import CORSMiddleware

from app.collaborative_filtering import collaborative_filtering
from app.database.database import fetch_user, add_user, fetch_user_diet

# main.py는 FastAPI 프로젝트의 전체적인 환경을 설정하는 파일
# 포트번호는 8000
app = FastAPI()

load_dotenv()


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


@app.websocket("/askmenu/{user_id}")
async def askmenu_endpoint(user_id: int, websocket: WebSocket):
    await websocket.accept()  # 웹소켓 연결 accept

    from app.service_flow.askmenu import askmenu_chat
    await askmenu_chat(user_id, websocket)


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
