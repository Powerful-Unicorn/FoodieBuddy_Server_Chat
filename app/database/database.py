import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor

load_dotenv()  # .env 파일에서 환경 변수 로드


def get_rds_connection():
    return pymysql.connect(
        host='foodiebuddy.clo8m062s7ci.ap-northeast-2.rds.amazonaws.com',
        port=3306,
        user='admin',
        password='powerfulunicorn11!',
        database='foodiebuddy',
        cursorclass=DictCursor
    )


# def get_sshtunnel_connection():
#     # EC2 연결 설정
#     ssh_host = os.getenv('SSH_HOST')
#     ssh_user = os.getenv('SSH_USER')
#     ssh_key_file = os.getenv('SSH_KEY_FILE')
#
#     # RDS 데이터베이스 설정
#     rds_host = os.getenv('RDS_HOST')
#     rds_port = 3306
#
#     server = SSHTunnelForwarder(
#         (ssh_host, 22),
#         ssh_username=ssh_user,
#         ssh_pkey=ssh_key_file,
#         remote_bind_address=(rds_host, rds_port),
#         local_bind_address=('127.0.0.1', 3307)  # 로컬 머신에서 3307 포트를 통해 연결
#     )
#
#     try:
#         server.start()
#         # print(f"SSH 터널이 열렸습니다. 로컬 포트 {server.local_bind_port}을 통해 RDS에 연결할 수 있습니다.")
#     except Exception as e:
#         print(f"SSH 터널을 여는 동안 오류가 발생했습니다: {e}")
#         import traceback
#         traceback.print_exc()
#
#     connection = pymysql.connect(
#         host='127.0.0.1',  # 로컬 호스트에서 접근
#         user=os.getenv('RDS_USER'),
#         password=os.getenv('RDS_PASSWORD'),
#         db=os.getenv('RDS_NAME'),
#         port=server.local_bind_port  # SSH 터널의 포트 (server.local_bind_port 사용)
#     )
#
#     return connection


def fetch_user():
    connection = get_rds_connection()
    # connection = get_localdb_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM foodiebuddy.user")  # user: 테이블 이름
            result = cursor.fetchall()
            print(result)
            return result
    finally:
        connection.close()


def fetch_user_diet(user_id):
    connection = get_rds_connection()
    # connection = get_localdb_connection()
    # connection = get_sshtunnel_connection()
    try:
        with connection.cursor() as cursor:
            # cursor.execute("SELECT * FROM foodiebuddy.user")
            query = (
                "SELECT user_id, username, dairy, egg, fruit, gluten, meat, nut, other, religion, seafood, vegetable, vegetarian "
                "FROM foodiebuddy.user "
                f"WHERE (user_id = {user_id}) "
                "AND ((dairy IS NOT NULL AND dairy != '') "  # WHERE (user_id IS {user_id})
                "OR (egg IS NOT NULL AND egg != '' AND egg != FALSE) "
                "OR (fruit IS NOT NULL AND fruit != '') "
                "OR (gluten IS NOT NULL AND gluten != '' AND gluten != FALSE) "
                "OR (meat IS NOT NULL AND meat != '') "
                "OR (nut IS NOT NULL AND nut != '') "
                "OR (other IS NOT NULL AND other != '') "
                "OR (religion IS NOT NULL AND religion != '') "
                "OR (seafood IS NOT NULL AND seafood != '') "
                "OR (vegetable IS NOT NULL AND vegetable != '') "
                "OR (vegetarian IS NOT NULL AND vegetarian != ''));")
            print(query)
            cursor.execute(query)
            result = cursor.fetchall()
            print(result)
            return result
    finally:
        connection.close()


def fetch_diet():
    connection = get_rds_connection()
    # connection = get_localdb_connection()
    try:
        with connection.cursor() as cursor:
            # cursor.execute("SELECT * FROM foodiebuddy.user")
            query = (
                "SELECT user_id, username, dairy, egg, fruit, gluten, meat, nut, other, religion, seafood, vegetable, vegetarian "
                "FROM foodiebuddy.user "
                "WHERE (dairy IS NOT NULL AND dairy != '') "
                "OR (egg IS NOT NULL AND egg != '' AND egg != FALSE) "
                "OR (fruit IS NOT NULL AND fruit != '') "
                "OR (gluten IS NOT NULL AND gluten != '' AND gluten != FALSE) "
                "OR (meat IS NOT NULL AND meat != '') "
                "OR (nut IS NOT NULL AND nut != '') "
                "OR (other IS NOT NULL AND other != '') "
                "OR (religion IS NOT NULL AND religion != '') "
                "OR (seafood IS NOT NULL AND seafood != '') "
                "OR (vegetable IS NOT NULL AND vegetable != '') "
                "OR (vegetarian IS NOT NULL AND vegetarian != '');")
            print(query)
            cursor.execute(query)
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

            count = cursor.execute(
                f"SELECT * FROM foodiebuddy.menu WHERE pronunciation = '{menu_pronunciation}' AND user_id = '{user_id}';")

            result = cursor.fetchall()
            # print(result)

            if count != 0:
                print(f"'{menu_name}', '{menu_pronunciation}', user_id: {user_id} exists in database")
                print(result)
                result_str = str(result[0])  # 리스트의 첫번째 아이템을 문자열로 변환
                menu_id = result_str.split(',')[0] + '}'
                print(menu_id)
                return menu_id
            else:
                cursor.execute(
                    f"INSERT INTO foodiebuddy.menu (is_bookmarked, name, pronunciation, star, user_id) VALUES (false, '{menu_name}', '{menu_pronunciation}', 0, {user_id})")
                connection.commit()
                print(f"'{menu_name}', '{menu_pronunciation}', user_id: {user_id} added to database")
                cursor.execute(
                    f"SELECT * FROM foodiebuddy.menu WHERE pronunciation = '{menu_pronunciation}' AND user_id = '{user_id}';")
                result = cursor.fetchall()
                print(result)
                result_str = str(result[0])  # 리스트의 첫번째 아이템을 문자열로 변환
                menu_id = result_str.split(',')[0] + '}'
                print(menu_id)
                return menu_id

    finally:
        connection.commit()
        connection.close()
