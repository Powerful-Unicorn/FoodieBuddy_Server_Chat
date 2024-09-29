from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./foodiebuddy.db" # 데이터베이스 접속 주소, db 파일은 프로젝트 루트에 저장

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# autocommit: db 저장에 커밋이 필요한지 여부 (false 설정시 커밋 필요o, 롤백 가능)
# create_engine은 컨넥션 풀을 생성한다. 컨넥션 풀이란 데이터베이스에 접속하는 객체를 일정 갯수만큼 만들어 놓고 돌려가며 사용하는 것을 말한다.
# declarative_base 함수에 의해 반환된 Base 클래스는 조금 후에 알아볼 데이터베이스 모델을 구성할 때 사용되는 클래스이다.

# 흠.. db 종류로는 sqlite그대로 사용..? 아니면 다른거 사용??