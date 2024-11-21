import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from app.database.database import get_rds_connection


def collaborative_filtering(user: int):
    connection = get_rds_connection()
    # connection = get_localdb_connection()

    cursor = connection.cursor()

    # 유저 한명에 대해 collaborative filtering 계산
    user_id = user

    query = ("SELECT user_id "
             "FROM user WHERE "
             f"dairy = (SELECT dairy FROM user WHERE user_id = {user_id}) "
             f"OR (dairy IS NULL AND (SELECT dairy FROM user WHERE user_id = {user_id}) IS NULL) "
             f"AND (CASE WHEN (SELECT egg FROM user WHERE user_id = {user_id}) = 0 THEN egg = 0 OR egg = 1 "
             f"WHEN (SELECT egg FROM user WHERE user_id = {user_id}) = 1 THEN egg = 1 ELSE FALSE END) "
             f"AND (CASE WHEN (SELECT fruit FROM user WHERE user_id = {user_id}) IS NULL THEN TRUE "
             f"ELSE fruit LIKE CONCAT('%', (SELECT fruit FROM user WHERE user_id = {user_id}), '%') END) "
             f"AND (CASE WHEN (SELECT gluten FROM user WHERE user_id = {user_id}) = 0 THEN gluten = 0 OR gluten = 1 "
             f"WHEN (SELECT gluten FROM user WHERE user_id = {user_id}) = 1 THEN gluten = 1 ELSE FALSE END) "
             f"AND (CASE WHEN (SELECT meat FROM user WHERE user_id = {user_id}) IS NULL THEN meat IS NULL OR meat LIKE 'all kinds%' "
             f"WHEN (SELECT meat FROM user WHERE user_id = {user_id}) LIKE 'all kinds except%' THEN "
             f"meat = 'all kinds' OR meat = (SELECT meat FROM user WHERE user_id = {user_id}) "
             f"WHEN (SELECT meat FROM user WHERE user_id = {user_id}) = 'all kinds' THEN meat = 'all kinds' ELSE FALSE END) "
             f"AND (CASE WHEN (SELECT nut FROM user WHERE user_id = {user_id}) IS NULL THEN True "
             f"WHEN (SELECT nut FROM user WHERE user_id = {user_id}) LIKE 'all kinds' THEN nut = 'all kinds' "
             f"WHEN (SELECT nut FROM user WHERE user_id = {user_id}) = 'tree nuts' THEN nut = 'all kinds' OR nut = 'tree nuts' "
             f"WHEN (SELECT nut FROM user WHERE user_id = {user_id}) = 'peanuts' THEN nut = 'all kinds' OR nut = 'peanuts' "
             f"ELSE FALSE END) AND (CASE WHEN (SELECT other FROM user WHERE user_id = {user_id}) IS NULL THEN TRUE "
             f"ELSE other LIKE CONCAT('%', (SELECT other FROM user WHERE user_id = {user_id}), '%') END) "
             f"AND (CASE WHEN (SELECT seafood FROM user WHERE user_id = {user_id}) IS NULL THEN TRUE "
             f"ELSE seafood LIKE CONCAT('%', (SELECT seafood FROM user WHERE user_id = {user_id}), '%') END) "
             f"AND (CASE WHEN (SELECT vegetable FROM user WHERE user_id = {user_id}) IS NULL THEN TRUE "
             f"ELSE vegetable LIKE CONCAT('%', (SELECT vegetable FROM user WHERE user_id = {user_id}), '%') END) "
             f"AND (CASE WHEN (SELECT vegetarian FROM user WHERE user_id = {user_id}) IS NULL THEN TRUE "
             f"ELSE vegetarian LIKE CONCAT('%', (SELECT vegetarian FROM user WHERE user_id = {user_id}), '%') END);")
    # Execute with the user_id value passed as a parameter.
    print(query)
    cursor.execute(query)

    user_ids_from_db_dic = cursor.fetchall()
    user_ids_from_db = (tuple(user_ids_from_db_dic[0].values()),)
    user_ids = tuple(user_id[0] for user_id in user_ids_from_db)
    cursor.execute("SELECT user_id FROM user WHERE user_id IN %s", (user_ids,))

    # print(cursor.fetchall()) 이건 겹치는 유저 확인용

    cursor.execute("SELECT user_id, pronunciation, star FROM menu WHERE user_id IN %s", (user_ids,))
    menu_ratings_dic = cursor.fetchall()
    # menu_ratings = (tuple(menu_ratings_dic[0].values()),)

    menu_ratings = ()
    for i in range(len(menu_ratings_dic)):
        menu_ratings += (tuple(menu_ratings_dic[i].values()),)

    df = pd.DataFrame(menu_ratings, columns=['user_id', 'pronunciation', 'star'])
    user_menu_matrix = df.pivot_table(index='user_id', columns='pronunciation', values='star')

    # 결측치를 0으로 채우고 유사도 계산
    user_similarity = cosine_similarity(user_menu_matrix.fillna(0))
    user_similarity_df = pd.DataFrame(user_similarity, index=user_menu_matrix.index, columns=user_menu_matrix.index)

    # 특정 유저(user_id=1)의 유사한 유저를 찾고 추천할 메뉴 결정
    target_user_id = user_id
    print(user_similarity_df[target_user_id])
    print(user_similarity_df[target_user_id].index)
    print(user_similarity_df[target_user_id].values)
    similar_users = user_similarity_df[target_user_id].sort_values(ascending=False).index[1:4]  # 자신 제외 3명

    # 유사한 유저들이 별점 준 메뉴 중, target_user 가 평가하지 않은 메뉴 추출
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

    cf_prompt = f"The list of menus that similar users liked, but the user didn't try before is [{recommended_menus}]"
    print(cf_prompt)

    return cf_prompt

    # recommend_history = recommendation(str_user_diet, cf_prompt)


def get_user_info(user_id: int):
    connection = get_rds_connection()
    # connection = get_localdb_connection()

    # 유저 한명 식이제한 불러오기
    cursor = connection.cursor()
    cursor.execute("SHOW COLUMNS FROM user")
    diets_list_dic = cursor.fetchall()

    # 변환 코드
    diets_list = tuple(
        (
            item['Field'],  # Field
            item['Type'],  # Type
            item['Null'],  # Null
            item['Key'],  # Key
            item['Default'],  # Default
            item['Extra']  # Extra
        )
        for item in diets_list_dic
    )

    cursor.execute(f"SELECT * FROM user Where user_id = {user_id}")
    result_dic = cursor.fetchall()
    result = (tuple(result_dic[0].values()),)
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

    return str_user_diet
