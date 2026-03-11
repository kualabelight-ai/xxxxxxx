# migrate_db.py
import sqlite3
import bcrypt
from database import get_db


def add_columns():
    """Добавляет необходимые столбцы в таблицу users"""
    print("Подключаемся к базе данных...")

    with get_db() as conn:
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Существующие столбцы: {columns}")

        if 'status' not in columns:
            print("Добавляем столбец 'status'...")
            conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'")
            print("✓ Столбец 'status' добавлен")
        else:
            print("Столбец 'status' уже существует")

        if 'is_admin' not in columns:
            print("Добавляем столбец 'is_admin'...")
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            print("✓ Столбец 'is_admin' добавлен")
        else:
            print("Столбец 'is_admin' уже существует")

        # 👇 НОВЫЙ БЛОК ДЛЯ banned
        if 'banned' not in columns:
            print("Добавляем столбец 'banned'...")
            conn.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
            print("Столбец 'banned' добавлен")
        else:
            print("Столбец 'banned' уже существует")

        # Устанавливаем статус 'approved' для существующих пользователей
        print("Устанавливаем статус 'approved' для существующих пользователей...")
        conn.execute("UPDATE users SET status = 'approved' WHERE status IS NULL OR status = 'pending'")

        # Показываем текущих пользователей (теперь с banned)
        users = conn.execute("SELECT id, username, email, status, is_admin, banned FROM users").fetchall()
        print("\nТекущие пользователи в базе:")
        for user in users:
            print(f"  ID: {user['id']}, Username: {user['username']}, Email: {user['email']}, Status: {user['status']}, is_admin: {user['is_admin']}, banned: {user['banned']}")

        conn.commit()
    print("\n✅ Миграция успешно завершена!")


def create_admin_user(username, password, email):
    """Создает нового пользователя с правами администратора"""
    pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, status, is_admin) VALUES (?, ?, ?, ?, ?)",
                (username, email, pwd_hash, 'approved', 1)
            )
            conn.commit()
            print(f"✅ Администратор {username} успешно создан!")
            return True
        except sqlite3.IntegrityError as e:
            print(f"❌ Ошибка: пользователь с таким именем или email уже существует")
            return False


def make_user_admin(username):
    """Назначает существующего пользователя администратором"""
    with get_db() as conn:
        # Проверяем, существует ли пользователь
        user = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            print(f"❌ Пользователь '{username}' не найден")
            return False

        # Назначаем администратором и устанавливаем статус approved
        conn.execute(
            "UPDATE users SET is_admin = 1, status = 'approved' WHERE username = ?",
            (username,)
        )
        conn.commit()
        print(f"✅ Пользователь '{username}' теперь администратор")
        return True


if __name__ == "__main__":
    print("=" * 50)
    print("МИГРАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 50)

    # Сначала добавляем колонки
    add_columns()

    print("\n" + "=" * 50)
    print("ДОПОЛНИТЕЛЬНЫЕ ДЕЙСТВИЯ")
    print("=" * 50)
    print("1. Создать нового администратора")
    print("2. Назначить существующего пользователя администратором")
    print("3. Выйти")

    choice = input("\nВыберите действие (1-3): ").strip()

    if choice == '1':
        username = input("Введите имя пользователя для администратора: ").strip()
        email = input("Введите email: ").strip()
        password = input("Введите пароль: ").strip()
        create_admin_user(username, password, email)

    elif choice == '2':
        username = input("Введите имя существующего пользователя: ").strip()
        make_user_admin(username)

    else:
        print("Выход...")

    print("\nГотово! Теперь можно запускать основное приложение.")