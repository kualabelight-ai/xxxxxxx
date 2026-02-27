import sqlite3
import bcrypt
import pyotp
from contextlib import contextmanager

DB_PATH = "users.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                totp_secret TEXT,
                totp_enabled INTEGER DEFAULT 0,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица для сброса пароля
        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

# Хеширование пароля (та же функция)
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Создание первого администратора (вызвать один раз вручную)
def create_admin(username, email, password):
    with get_db() as conn:
        pwd_hash = hash_password(password)
        try:
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, pwd_hash)
            )
            conn.commit()
            print(f"Admin {username} created")
        except sqlite3.IntegrityError:
            print("User already exists")

if __name__ == "__main__":
    init_db()
    # Пример создания администратора (раскомментировать и запустить один раз)
    #create_admin("admin", "v52882680@gmail.com", "123456")