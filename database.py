import psycopg2
import os

DATABASE_URL = os.getenv("postgresql://puppy_bot_db_user:RBd8XY8nUfmFxtM0rEg356KrtB8RuNaJ@dpg-d7qb3l3rjlhs73ebsfcg-a.oregon-postgres.render.com/puppy_bot_db")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        city TEXT,
        breed TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sent_ads (
        user_id BIGINT,
        link TEXT,
        PRIMARY KEY (user_id, link)
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


def save_city(user_id, city):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO users (user_id, city)
    VALUES (%s, %s)
    ON CONFLICT (user_id)
    DO UPDATE SET city = EXCLUDED.city
    """, (user_id, city))

    conn.commit()
    cur.close()
    conn.close()


def save_breed(user_id, breed):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    UPDATE users SET breed = %s WHERE user_id = %s
    """, (breed.lower(), user_id))

    conn.commit()
    cur.close()
    conn.close()


def get_all_users():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT user_id, city, breed
    FROM users
    WHERE breed IS NOT NULL
    """)

    users = cur.fetchall()

    cur.close()
    conn.close()
    return users


def save_sent_if_new(user_id, link):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT INTO sent_ads (user_id, link)
        VALUES (%s, %s)
        """, (user_id, link))

        conn.commit()
        return True

    except:
        return False

    finally:
        cur.close()
        conn.close()
