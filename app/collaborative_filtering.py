import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from app.database.database import get_rds_connection
from app.service_flow.recommendation import recommendation

# # EC2 연결 설정
# ssh_host = ''
# ssh_user = 'ubuntu'
# ssh_key_file = 'foodiebuddy-ec2-key.pem'

# RDS 데이터베이스 설정
# rds_host = ''
# rds_port = 3306
#
# server = SSHTunnelForwarder(
#     (ssh_host, 22),
#     ssh_username=ssh_user,
#     ssh_pkey=ssh_key_file,
#     remote_bind_address=(rds_host, rds_port),
#     local_bind_address=('127.0.0.1', 3307)  # 로컬 머신에서 3307 포트를 통해 연결
# )

# try:
#     server.start()
#     # print(f"SSH 터널이 열렸습니다. 로컬 포트 {server.local_bind_port}을 통해 RDS에 연결할 수 있습니다.")
# except Exception as e:
#     # print(f"SSH 터널을 여는 동안 오류가 발생했습니다: {e}")
#     import traceback
#
#     traceback.print_exc()

connection = get_rds_connection()

# 유저 한명 식이제한 불러오기
cursor = connection.cursor()
cursor.execute("SHOW COLUMNS FROM user")
diets_list = cursor.fetchall()

cursor.execute("SELECT * FROM user Where user_id = 1")
result = cursor.fetchall()
user_diets = list(result[0])
user_info = {}

for i in range(len(diets_list)):
    if diets_list[i][0] not in ('user_id', 'email', 'password', 'username'):
        user_info[diets_list[i][0]] = user_diets[i]

str_user_diet = f"Religion: {user_info['religion']}, Vegetarian: {user_info['vegetarian']}. Details: "
for k, v in user_info.items():
    if k == 'vegetarian' or k == 'religion':
        continue
    if v is None or v == b'\x00':
        continue

    if v == b'\x01':
        str_user_diet += k + ', '
    else:
        str_user_diet += k + ':' + v + ', '

str_user_diet = str_user_diet[:-2] + '.'

# 유저 한명에 대해 collaborative filtering 계산
user_id = 1

query = f"""
SELECT user_id
FROM user
WHERE 
    dairy = (SELECT dairy FROM user WHERE user_id = {user_id}) 
    OR (dairy IS NULL AND (SELECT dairy FROM user WHERE user_id = {user_id}) IS NULL)
    AND (CASE 
        WHEN (SELECT egg FROM user WHERE user_id = {user_id}) = 0 THEN 
            egg = 0 OR egg = 1
        WHEN (SELECT egg FROM user WHERE user_id = {user_id}) = 1 THEN 
            egg = 1
        ELSE FALSE
    END)
    AND (CASE 
        WHEN (SELECT fruit FROM user WHERE user_id = {user_id}) IS NULL THEN 
            TRUE
        ELSE fruit LIKE CONCAT('%', (SELECT fruit FROM user WHERE user_id = {user_id}), '%')
    END)
    AND (CASE 
        WHEN (SELECT gluten FROM user WHERE user_id = {user_id}) = 0 THEN 
            gluten = 0 OR gluten = 1
        WHEN (SELECT gluten FROM user WHERE user_id = {user_id}) = 1 THEN 
            gluten = 1
        ELSE FALSE
    END)
    AND (CASE 
        WHEN (SELECT meat FROM user WHERE user_id = {user_id}) IS NULL THEN 
            meat IS NULL OR meat LIKE 'all kinds%'
        WHEN (SELECT meat FROM user WHERE user_id = {user_id}) LIKE 'all kinds except%' THEN 
            meat = 'all kinds' OR meat = (SELECT meat FROM user WHERE user_id = {user_id})
        WHEN (SELECT meat FROM user WHERE user_id = {user_id}) = 'all kinds' THEN 
            meat = 'all kinds'
        ELSE FALSE
    END)
    AND (CASE 
        WHEN (SELECT nut FROM user WHERE user_id = {user_id}) IS NULL THEN 
            True
        WHEN (SELECT nut FROM user WHERE user_id = {user_id}) LIKE 'all kinds' THEN 
            nut = 'all kinds'
        WHEN (SELECT nut FROM user WHERE user_id = {user_id}) = 'tree nuts' THEN 
            nut = 'all kinds' OR nut = 'tree nuts'
        WHEN (SELECT nut FROM user WHERE user_id = {user_id}) = 'peanuts' THEN 
            nut = 'all kinds' OR nut = 'peanuts'
        ELSE FALSE
    END)
    AND (CASE 
        WHEN (SELECT other FROM user WHERE user_id = {user_id}) IS NULL THEN 
            TRUE
        ELSE other LIKE CONCAT('%', (SELECT other FROM user WHERE user_id = {user_id}), '%')
    END)
    AND (CASE 
        WHEN (SELECT seafood FROM user WHERE user_id = {user_id}) IS NULL THEN 
            TRUE
        ELSE seafood LIKE CONCAT('%', (SELECT seafood FROM user WHERE user_id = {user_id}), '%')
    END)
    AND (CASE 
        WHEN (SELECT vegetable FROM user WHERE user_id = {user_id}) IS NULL THEN 
            TRUE
        ELSE vegetable LIKE CONCAT('%', (SELECT vegetable FROM user WHERE user_id = {user_id}), '%')
    END)
    AND (CASE 
        WHEN (SELECT vegetarian FROM user WHERE user_id = {user_id}) IS NULL THEN 
            TRUE
        ELSE vegetarian LIKE CONCAT('%', (SELECT vegetarian FROM user WHERE user_id = {user_id}), '%')
    END);
"""
# Execute with the user_id value passed as a parameter.
cursor.execute(query)

user_ids_from_db = cursor.fetchall()
user_ids = tuple(user_id[0] for user_id in user_ids_from_db)
cursor.execute("SELECT user_id FROM user WHERE user_id IN %s", (user_ids,))

# print(cursor.fetchall()) 이건 겹치는 유저 확인용

cursor.execute("SELECT user_id, pronunciation, star FROM menu WHERE user_id IN %s", (user_ids,))
menu_ratings = cursor.fetchall()

df = pd.DataFrame(menu_ratings, columns=['user_id', 'pronunciation', 'star'])
user_menu_matrix = df.pivot_table(index='user_id', columns='pronunciation', values='star')

# 결측치를 0으로 채우고 유사도 계산
user_similarity = cosine_similarity(user_menu_matrix.fillna(0))
user_similarity_df = pd.DataFrame(user_similarity, index=user_menu_matrix.index, columns=user_menu_matrix.index)

# 특정 유저(user_id=1)의 유사한 유저를 찾고 추천할 메뉴 결정
target_user_id = 1
similar_users = user_similarity_df[target_user_id].sort_values(ascending=False).index[1:4]  # 자신 제외 3명

# 유사한 유저들이 별점 준 메뉴 중, target_user_id가 평가하지 않은 메뉴 추출
target_user_ratings = user_menu_matrix.loc[target_user_id]
similar_user_ratings = user_menu_matrix.loc[similar_users]

recommendations = (similar_user_ratings.mean(axis=0)
                   .drop(target_user_ratings.dropna().index)
                   .sort_values(ascending=False))
filtered_recommendations = recommendations[recommendations >= 4]

recommended_menus = ""
for menu, rating in filtered_recommendations.items():
    recommended_menus += f" {menu}({rating}/5.0),"

recommended_menus = recommended_menus[:-1] + "."

cf_prompt = f"The list of menus that similar users liked, but the user didn't try before is{recommended_menus}"

recommend_history = recommendation(str_user_diet, cf_prompt)
