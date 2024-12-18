
## 👩‍💻 Prerequisites
이 레포지토리는 `FastAPI` 기반으로 구현된 애플리케이션으로, `requirements.txt`에 적힌 라이브러리 설치가 사전에 이루어져야 합니다.
```bash
pip install -r requirements.txt
```

## 🔧 How to build
Git clone 을 통한 FastAPI 프로젝트 생성<br>
   ```
   https://github.com/Powerful-Unicorn/FoodieBuddy_Server_Chat.git
   ```
별도의 빌드는 필요하지 않습니다.


## 🔓 .env file
레포지토리를 git clone 한 후, 다음과 같은 형식의 `.env 파일`을 foodiebuddy 폴더에 위치시킵니다. 
```
OPENAI_API_KEY= ...
INGREDIENTS_API_KEY= ...
STABILITY_API_KEY= ...
SERP_API_KEY= ...

RDS_USER= ...
RDS_PASSWORD= ...
RDS_HOST= ...
RDS_PORT=3306
RDS_NAME=foodiebuddy

DB_USER_LOCAL= //로컬 db의 유저네임
DB_PASSWORD_LOCAL= //로컬 db의 패스워드
DB_HOST_LOCAL=localhost
DB_PORT_LOCAL=3306
DB_NAME_LOCAL=foodiebuddy

```

##  🚀 How to run
위의 과정을 모두 완료한 뒤, 다음 명령어로 `8000`번 포트에서 실행 가능합니다.
```bash
uvicorn app.main:app --reload
```


