import sqlite3

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        city TEXT,
        breed TEXT
    )
    """)

    # таблица отправленных объявлений
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sent_ads (
        user_id INTEGER,
        link TEXT,
        PRIMARY KEY (user_id, link)
    )
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_user_link
    ON sent_ads(user_id, link)
    """)

    conn.commit()
    conn.close()
    
def save_city(user_id, city):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (user_id, city)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET city=excluded.city
    """, (user_id, city))

    conn.commit()
    conn.close()


def save_breed(user_id, breed):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users SET breed = ? WHERE user_id = ?
    """, (breed, user_id))

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT city, breed FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result

def get_all_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, city, breed FROM users WHERE breed IS NOT NULL")
    users = cursor.fetchall()

    conn.close()
    return users

def is_sent(user_id, link): #Проверка: отправляли ли уже
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM sent_ads WHERE user_id = ? AND link = ?",
        (user_id, link)
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None

def save_sent_if_new(user_id, link):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO sent_ads (user_id, link) VALUES (?, ?)",
            (user_id, link)
        )
        conn.commit()
        return True  # новое объявление

    except sqlite3.IntegrityError:
        return False  # уже было

    finally:
        conn.close()

