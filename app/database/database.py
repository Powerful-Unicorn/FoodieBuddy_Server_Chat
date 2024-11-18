import os

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor
from sqlalchemy.ext.declarative import declarative_base

# .env 파일에서 환경 변수 로드
load_dotenv()


def get_rds_connection():
    return pymysql.connect(
        host=os.getenv('RDS_HOST'),
        port=3306,
        user=os.getenv('RDS_USER'),
        password=os.getenv('RDS_PASSWORD'),
        database=os.getenv('RDS_DATABASE'),
        cursorclass=DictCursor
    )


def get_localdb_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST_LOCAL'),
        port=3306,
        user='root',
        password=os.getenv('DB_PASSWORD_LOCAL'),
        database=os.getenv('DB_NAME_LOCAL'),
        cursorclass=DictCursor
    )


def fetch_user():
    connection = get_rds_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM foodiebuddy.user")  # user: 테이블 이름
            result = cursor.fetchall()
            print(result)
            return result
    finally:
        connection.close()


def add_user():
    connection = get_rds_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO foodiebuddy.user (dairy, egg, email, fruit, gluten, meat, nut, other, password, religion, seafood, username, vegetable, vegetarian) VALUES (null, null, 'aaa@aaaa', null, true, null, null, null, 'aaa', '', null, null, 'garlic', '')")
            result = cursor.fetchall()
            print(result)
            return result
    finally:
        connection.commit()
        connection.close()


def add_menu(menu_info, user_id):
    # **와 (랑 )를 기준으로 문자열 자르기
    import re
    split_text = re.split(r'\*\*|\(|\)', menu_info)

    # 결과에서 빈 문자열 제거
    split_text = [part for part in split_text if part]
    menu_name = split_text[0]
    menu_pronunciation = split_text[1]

    print(menu_name)
    print(menu_pronunciation)
    print(user_id)

    # connection = get_localdb_connection()
    connection = get_rds_connection()

    try:
        with connection.cursor() as cursor:

            # query = "INSERT INTO foodiebuddy.menu (menu, quantity) VALUES (%s, %s, %s)"
            # values = ("Fried Rice", "Kimchi Bokkeumbap", 1)
            # cursor.execute(query, values)

            count = cursor.execute(
                f"SELECT * FROM foodiebuddy.menu WHERE pronunciation = '{menu_pronunciation}';")

            result = cursor.fetchall()
            # print(result)

            if count != 0:
                print(f"'{menu_name}', '{menu_pronunciation}' exists in database")
                print(result)
                result_str = str(result[0])  # 리스트의 첫번째 아이템을 문자열로 변환
                menu_id = result_str.split(',')[0] + '}'
                print(menu_id)
                return menu_id
            else:
                cursor.execute(
                    f"INSERT INTO foodiebuddy.menu (is_bookmarked, name, pronunciation, star, user_id) VALUES (false, '{menu_name}', '{menu_pronunciation}', 0, {user_id})")
                print(f"'{menu_name}', '{menu_pronunciation}', user_id: {user_id} added to database")
                cursor.execute(
                    f"SELECT * FROM foodiebuddy.menu WHERE pronunciation = '{menu_pronunciation}';")
                result = cursor.fetchall()
                print(result)
                result_str = str(result[0])  # 리스트의 첫번째 아이템을 문자열로 변환
                menu_id = result_str.split(',')[0] + '}'
                print(menu_id)
                return menu_id
            # result = cursor.fetchall()
            # return result
    finally:
        connection.commit()
        connection.close()


# SQLALCHEMY_DATABASE_URL = "sqlite:///./foodiebuddy.db" # 데이터베이스 접속 주소, db 파일은 프로젝트 루트에 저장
#
# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
# )
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# autocommit: db 저장에 커밋이 필요한지 여부 (false 설정시 커밋 필요o, 롤백 가능)
# create_engine은 컨넥션 풀을 생성한다. 컨넥션 풀이란 데이터베이스에 접속하는 객체를 일정 갯수만큼 만들어 놓고 돌려가며 사용하는 것을 말한다.
# declarative_base 함수에 의해 반환된 Base 클래스는 조금 후에 알아볼 데이터베이스 모델을 구성할 때 사용되는 클래스이다.

# 흠.. db 종류로는 sqlite그대로 사용..? 아니면 다른거 사용??
