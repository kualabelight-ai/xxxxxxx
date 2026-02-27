import streamlit as st
import bcrypt
import pyotp
import qrcode
from io import BytesIO
import base64
import sqlite3
import time
from datetime import datetime, timedelta
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
from database import get_db, verify_password, hash_password

# Настройка логирования
logging.basicConfig(
    filename='login_attempts.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Конфигурация email (замените на свои данные или используйте st.secrets)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = st.secrets.get("email", {}).get("user", "your_email@gmail.com")
SMTP_PASSWORD = st.secrets.get("email", {}).get("password", "your_password")
FROM_EMAIL = SMTP_USER

# -------------------- Rate limiting --------------------
MAX_ATTEMPTS = 50
LOCKOUT_MINUTES = 1

def check_rate_limit(username: str) -> bool:
    """Проверяет, не заблокирован ли пользователь из-за множества неудачных попыток."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT failed_attempts, locked_until FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        if not user:
            return True  # пользователь не существует, но пропускаем для единообразия

        if user["locked_until"]:
            locked_until = datetime.fromisoformat(user["locked_until"])
            if datetime.now() < locked_until:
                return False  # ещё заблокирован
            else:
                # Сбрасываем блокировку
                conn.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
                    (username,)
                )
                conn.commit()
        return True

def record_failed_attempt(username: str):
    """Увеличивает счётчик неудач и блокирует при превышении лимита."""
    with get_db() as conn:
        user = conn.execute("SELECT failed_attempts FROM users WHERE username = ?", (username,)).fetchone()
        if user:
            attempts = user["failed_attempts"] + 1
            locked_until = None
            if attempts >= MAX_ATTEMPTS:
                locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                logging.warning(f"User {username} locked until {locked_until}")
            conn.execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?",
                (attempts, locked_until, username)
            )
            conn.commit()

def reset_rate_limit(username: str):
    """Сбрасывает счётчик после успешного входа."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
            (username,)
        )
        conn.commit()

# -------------------- Логирование --------------------
def log_attempt(username: str, success: bool, ip: str = None):
    """Записывает попытку входа в лог-файл."""
    status = "SUCCESS" if success else "FAILURE"
    logging.info(f"Login attempt - User: {username} - Status: {status} - IP: {ip or 'unknown'}")

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    with get_db() as conn:
        result = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        return result and result["is_admin"] == 1

# -------------------- Аутентификация с 2FA --------------------
def authenticate_user(username: str, password: str, totp_code: str = None) -> tuple:
    """
    Проверяет логин/пароль и, если включена 2FA, проверяет код.
    Возвращает (success: bool, message: str, user_data: dict or None)
    """
    if not check_rate_limit(username):
        return False, "Слишком много попыток. Попробуйте позже.", None

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, password_hash, totp_secret, totp_enabled, status, banned FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if not user:
            # Не сообщаем, что пользователь не существует (безопасность)
            record_failed_attempt(username)
            log_attempt(username, False)
            return False, "Неверное имя пользователя или пароль", None

        # Проверка пароля
        if not verify_password(password, user["password_hash"]):
            record_failed_attempt(username)
            log_attempt(username, False)
            return False, "Неверное имя пользователя или пароль", None

        # Если включена 2FA, проверяем код
        if user["totp_enabled"]:
            if not totp_code:
                return False, "REQUIRE_2FA", dict(user)  # специальный код для запроса 2FA
            totp = pyotp.TOTP(user["totp_secret"])
            if not totp.verify(totp_code):
                record_failed_attempt(username)
                log_attempt(username, False)
                return False, "Неверный код двухфакторной аутентификации", None
        if user["status"] != "approved":
            log_attempt(username, False)
            return False, "Ваша учётная запись ещё не подтверждена администратором.", None
        if user["banned"]:
            log_attempt(username, False)
            return False, "Ваша учётная запись заблокирована администратором.", None
        # Успешный вход
        reset_rate_limit(username)
        log_attempt(username, True)
        return True, "Успешный вход", dict(user)

# -------------------- 2FA управление --------------------
def generate_totp_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(username: str, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="Data Harvester")

def generate_qr_base64(uri: str) -> str:
    qr = qrcode.make(uri)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def enable_2fa(user_id: int, secret: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE id = ?",
            (secret, user_id)
        )
        conn.commit()

def disable_2fa(user_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET totp_enabled = 0 WHERE id = ?",
            (user_id,)
        )
        conn.commit()

# -------------------- Смена пароля --------------------
def change_password(user_id: int, old_password: str, new_password: str) -> tuple:
    """Проверяет старый пароль и меняет на новый."""
    with get_db() as conn:
        user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "Пользователь не найден"

        if not verify_password(old_password, user["password_hash"]):
            return False, "Неверный текущий пароль"

        new_hash = hash_password(new_password)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.commit()
        logging.info(f"Password changed for user {user_id}")
        return True, "Пароль успешно изменён"

# -------------------- Восстановление пароля (через email) --------------------
def send_reset_email(email: str, token: str):
    """Отправляет письмо со ссылкой для сброса пароля (требуется настройка SMTP)."""
    reset_link = f"http://localhost:8501?reset_token={token}"  # В реальности используйте ваш домен
    subject = "Сброс пароля в Data Harvester"
    body = f"Для сброса пароля перейдите по ссылке: {reset_link}\n\nСсылка действительна 1 час."

    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

def request_password_reset(email: str):
    """Создаёт токен для сброса пароля и отправляет email."""
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            # Не сообщаем, что email не найден (безопасность)
            return False

        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        conn.execute(
            "INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user["id"], token, expires_at)
        )
        conn.commit()

        return send_reset_email(email, token)

def reset_password_with_token(token: str, new_password: str) -> bool:
    """Проверяет токен и меняет пароль."""
    with get_db() as conn:
        reset = conn.execute(
            "SELECT user_id, expires_at FROM password_resets WHERE token = ?",
            (token,)
        ).fetchone()
        if not reset:
            return False

        if datetime.now() > datetime.fromisoformat(reset["expires_at"]):
            return False  # токен истёк

        new_hash = hash_password(new_password)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, reset["user_id"]))
        conn.execute("DELETE FROM password_resets WHERE token = ?", (token,))
        conn.commit()
        return True


def register_form():
    """Форма регистрации нового пользователя."""
    st.title("📝 Регистрация")

    with st.form("register_form"):
        new_username = st.text_input("Придумайте логин")
        new_email = st.text_input("Ваш email")
        new_password = st.text_input("Придумайте пароль", type="password")
        confirm_password = st.text_input("Повторите пароль", type="password")
        submitted = st.form_submit_button("Зарегистрироваться")

        if submitted:
            # Проверка совпадения паролей
            if new_password != confirm_password:
                st.error("Пароли не совпадают")
                return

            # Простейшая проверка сложности (можно расширить)
            if len(new_password) < 6:
                st.error("Пароль должен быть не менее 6 символов")
                return

            # Хешируем пароль
            pwd_hash = hash_password(new_password)

            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO users (username, email, password_hash, status) VALUES (?, ?, ?, ?)",
                        (new_username, new_email, pwd_hash, 'pending')
                    )
                    conn.commit()
                st.success("Регистрация успешна! Ваша заявка отправлена администратору на подтверждение.")
                # Переключаемся на форму входа
                st.session_state["show_login"] = True
                st.rerun()
            except Exception as e:
                st.error("Ошибка: возможно, такой логин или email уже заняты.")
# -------------------- Форма входа (обновлённая) --------------------
def login_form():
    st.title("🔐 Вход в систему")

    # Проверка, не хотим ли мы показать регистрацию
    if st.session_state.get("show_register", False):
        register_form()
        if st.button("← Вернуться ко входу"):
            st.session_state["show_register"] = False
            st.rerun()
        return

    # Проверяем, не находимся ли мы в процессе 2FA (как было ранее)
    if "2fa_user" in st.session_state:
        # Этап ввода кода 2FA
        with st.form("2fa_form"):
            st.write(f"Введите код двухфакторной аутентификации для {st.session_state['2fa_user']['username']}")
            totp_code = st.text_input("Код из приложения", max_chars=6)
            submitted = st.form_submit_button("Подтвердить")
            if submitted:
                success, msg, user = authenticate_user(
                    st.session_state['2fa_user']['username'],
                    st.session_state['2fa_password'],
                    totp_code
                )
                if success:
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user["id"]
                    st.session_state["username"] = user["username"]
                    st.session_state.pop("2fa_user", None)
                    st.session_state.pop("2fa_password", None)
                    st.success("Вход выполнен успешно!")
                    st.rerun()
                else:
                    st.error(msg)
        # Кнопка вернуться
        if st.button("← Назад"):
            st.session_state.pop("2fa_user", None)
            st.session_state.pop("2fa_password", None)
            st.rerun()
        return

    # Основная форма логина
    with st.form("login_form"):
        username = st.text_input("Имя пользователя")
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Войти")
        if submitted:
            success, msg, user = authenticate_user(username, password)
            if success:
                st.session_state["authenticated"] = True
                st.session_state["user_id"] = user["id"]
                st.session_state["username"] = user["username"]
                st.success("Вход выполнен успешно!")
                st.rerun()
            elif msg == "REQUIRE_2FA":
                # Запоминаем пользователя для второго этапа
                st.session_state["2fa_user"] = user
                st.session_state["2fa_password"] = password
                st.rerun()
            else:
                st.error(msg)

    if st.button("Нет аккаунта? Зарегистрироваться"):
        st.session_state["show_register"] = True
        st.rerun()

        # Раздел восстановления пароля (как было)
    with st.expander("Забыли пароль?"):
        email = st.text_input("Ваш email")
        if st.button("Отправить ссылку для сброса"):
            if request_password_reset(email):
                st.success("Если email зарегистрирован, ссылка отправлена.")
            else:
                st.error("Ошибка отправки. Проверьте email и попробуйте снова.")

# -------------------- Выход --------------------
def logout():
    st.session_state["authenticated"] = False
    st.session_state.pop("user_id", None)
    st.session_state.pop("username", None)
    st.rerun()

# -------------------- Интерфейс профиля (смена пароля, 2FA) --------------------
def profile_page():
    st.sidebar.title(f"👤 {st.session_state['username']}")
    with st.sidebar.expander("Настройки профиля"):
        if st.button("Сменить пароль"):
            st.session_state["show_change_password"] = True
        if st.button("Двухфакторная аутентификация"):
            st.session_state["show_2fa_settings"] = True
        if is_admin(st.session_state["user_id"]):   # <-- исправлено
            if st.button("👥 Панель администратора"):
                st.session_state["show_admin_panel"] = True
                st.rerun()
        if st.button("Выйти"):
            logout()

    # Смена пароля
    if st.session_state.get("show_change_password", False):
        st.subheader("Смена пароля")
        with st.form("change_password"):
            old_pwd = st.text_input("Текущий пароль", type="password")
            new_pwd = st.text_input("Новый пароль", type="password")
            confirm_pwd = st.text_input("Подтвердите новый пароль", type="password")
            submitted = st.form_submit_button("Изменить")
            if submitted:
                if new_pwd != confirm_pwd:
                    st.error("Пароли не совпадают")
                else:
                    success, msg = change_password(st.session_state["user_id"], old_pwd, new_pwd)
                    if success:
                        st.success(msg)
                        st.session_state["show_change_password"] = False
                        st.rerun()
                    else:
                        st.error(msg)
        if st.button("Отмена"):
            st.session_state["show_change_password"] = False
            st.rerun()

    # Настройки 2FA
    if st.session_state.get("show_2fa_settings", False):
        st.subheader("Двухфакторная аутентификация")
        with get_db() as conn:
            user = conn.execute(
                "SELECT totp_enabled, totp_secret FROM users WHERE id = ?",
                (st.session_state["user_id"],)
            ).fetchone()

        if user["totp_enabled"]:
            st.info("2FA включена")
            if st.button("Отключить 2FA"):
                disable_2fa(st.session_state["user_id"])
                st.success("2FA отключена")
                st.session_state["show_2fa_settings"] = False
                st.rerun()
        else:
            st.write("Включите двухфакторную аутентификацию для дополнительной защиты.")
            if "temp_totp_secret" not in st.session_state:
                st.session_state["temp_totp_secret"] = generate_totp_secret()

            secret = st.session_state["temp_totp_secret"]
            uri = get_totp_uri(st.session_state["username"], secret)
            qr_base64 = generate_qr_base64(uri)

            st.image(f"data:image/png;base64,{qr_base64}", caption="Отсканируйте QR-код в приложении (Google Authenticator и др.)")
            st.code(f"Секретный ключ (если не можете отсканировать): {secret}")

            with st.form("verify_2fa"):
                verify_code = st.text_input("Введите код из приложения для подтверждения", max_chars=6)
                submitted = st.form_submit_button("Активировать 2FA")
                if submitted:
                    totp = pyotp.TOTP(secret)
                    if totp.verify(verify_code):
                        enable_2fa(st.session_state["user_id"], secret)
                        st.success("2FA успешно включена!")
                        st.session_state.pop("temp_totp_secret", None)
                        st.session_state["show_2fa_settings"] = False
                        st.rerun()
                    else:
                        st.error("Неверный код. Попробуйте ещё раз.")


        if st.button("Закрыть настройки 2FA"):
            st.session_state.pop("temp_totp_secret", None)
            st.session_state["show_2fa_settings"] = False
            st.rerun()

def ban_user(user_id: int):
    with get_db() as conn:
        conn.execute("UPDATE users SET banned = 1 WHERE id = ?", (user_id,))
        conn.commit()
    logging.info(f"User {user_id} banned by admin {st.session_state['user_id']}")

def unban_user(user_id: int):
    with get_db() as conn:
        conn.execute("UPDATE users SET banned = 0 WHERE id = ?", (user_id,))
        conn.commit()
    logging.info(f"User {user_id} unbanned by admin {st.session_state['user_id']}")

def delete_user(user_id: int):
    try:
        with get_db() as conn:
            # Удаляем связанные записи (если есть таблица password_resets)
            conn.execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
            # Удаляем самого пользователя
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        logging.info(f"User {user_id} deleted by admin {st.session_state['user_id']}")
        return True, "Пользователь успешно удалён"
    except Exception as e:
        logging.error(f"Error deleting user {user_id}: {e}")
        return False, str(e)

def toggle_admin(user_id: int, make_admin: bool):
    with get_db() as conn:
        conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if make_admin else 0, user_id))
        conn.commit()
    logging.info(f"User {user_id} admin set to {make_admin} by admin {st.session_state['user_id']}")

def reset_2fa(user_id: int):
    """Принудительно отключает 2FA (если пользователь потерял доступ)"""
    with get_db() as conn:
        conn.execute("UPDATE users SET totp_enabled = 0, totp_secret = NULL WHERE id = ?", (user_id,))
        conn.commit()
    logging.info(f"2FA reset for user {user_id} by admin {st.session_state['user_id']}")


def admin_panel():
    st.title("👥 Панель администратора")

    tab1, tab2 = st.tabs(["📋 Заявки на регистрацию", "👤 Все пользователи"])

    # ---------- Вкладка заявок ----------
    with tab1:
        st.subheader("Новые заявки")
        with get_db() as conn:
            pending_users = conn.execute(
                "SELECT id, username, email FROM users WHERE status = 'pending'"
            ).fetchall()

        if not pending_users:
            st.info("Нет новых заявок.")
        else:
            for user in pending_users:
                col1, col2, col3 = st.columns([3, 3, 2])
                with col1:
                    st.write(f"**{user['username']}**")
                with col2:
                    st.write(user['email'])
                with col3:
                    if st.button("✅ Одобрить", key=f"approve_{user['id']}"):
                        with get_db() as conn:
                            conn.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user['id'],))
                            conn.commit()
                        st.success(f"Пользователь {user['username']} одобрен.")
                        st.rerun()

    # ---------- Вкладка всех пользователей ----------
    with tab2:
        st.subheader("Управление пользователями")

        with get_db() as conn:
            users = conn.execute("""
                SELECT id, username, email, status, is_admin, totp_enabled, banned, 
                       failed_attempts, locked_until
                FROM users ORDER BY id
            """).fetchall()

        if not users:
            st.info("Нет пользователей.")
            return

        # Преобразуем в список словарей для удобства отображения
        users_list = []
        for u in users:
            users_list.append({
                "ID": u["id"],
                "Username": u["username"],
                "Email": u["email"],
                "Status": u["status"],
                "Admin": "✅" if u["is_admin"] else "❌",
                "2FA": "✅" if u["totp_enabled"] else "❌",
                "Banned": "✅" if u["banned"] else "❌",
                "Failed": u["failed_attempts"],
                "Locked": "🔒" if u["locked_until"] and datetime.now() < datetime.fromisoformat(
                    u["locked_until"]) else "—"
            })

        # Показываем таблицу
        st.dataframe(users_list, use_container_width=True)

        st.markdown("---")
        st.subheader("Действия с пользователем")

        # Выбор пользователя по ID или имени (для простоты сделаем выпадающий список)
        user_options = {f"{u['username']} (ID: {u['id']})": u['id'] for u in users}
        selected_display = st.selectbox("Выберите пользователя", list(user_options.keys()))
        selected_id = user_options[selected_display]

        # Получаем данные выбранного пользователя
        with get_db() as conn:
            user = conn.execute(
                "SELECT id, username, email, status, is_admin, banned FROM users WHERE id = ?",
                (selected_id,)
            ).fetchone()

        if user:
            st.write(
                f"**Текущий статус:** {user['status']}, Админ: {'да' if user['is_admin'] else 'нет'}, Бан: {'да' if user['banned'] else 'нет'}")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                # Бан / разбан
                if user["banned"]:
                    if st.button("🔓 Разблокировать", key=f"unban_{user['id']}"):
                        if user["id"] == st.session_state["user_id"]:
                            st.error("Нельзя разблокировать самого себя (вы не забанены, но это бессмысленно).")
                        else:
                            unban_user(user["id"])
                            st.success(f"Пользователь {user['username']} разблокирован.")
                            st.rerun()
                else:
                    if st.button("🔒 Заблокировать", key=f"ban_{user['id']}"):
                        if user["id"] == st.session_state["user_id"]:
                            st.error("Нельзя заблокировать самого себя.")
                        else:
                            ban_user(user["id"])
                            st.success(f"Пользователь {user['username']} заблокирован.")
                            st.rerun()

            with col2:
                # Назначить / снять админа
                if user["is_admin"]:
                    if st.button("👤 Снять админа", key=f"deadmin_{user['id']}"):
                        if user["id"] == st.session_state["user_id"]:
                            st.error("Нельзя снять админа с самого себя (вы перестанете видеть админку).")
                        else:
                            toggle_admin(user["id"], False)
                            st.success(f"Пользователь {user['username']} больше не администратор.")
                            st.rerun()
                else:
                    if st.button("👑 Назначить админом", key=f"admin_{user['id']}"):
                        toggle_admin(user["id"], True)
                        st.success(f"Пользователь {user['username']} теперь администратор.")
                        st.rerun()

            with col3:
                # Сброс 2FA
                if st.button("🔄 Сбросить 2FA", key=f"reset2fa_{user['id']}"):
                    reset_2fa(user["id"])
                    st.success(f"2FA для {user['username']} сброшена.")
                    st.rerun()

            with col4:
                if f"confirm_delete_{user['id']}" not in st.session_state:
                    st.session_state[f"confirm_delete_{user['id']}"] = False

                if not st.session_state[f"confirm_delete_{user['id']}"]:
                    if st.button("❌ Удалить", key=f"delete_{user['id']}"):
                        if user["id"] == st.session_state["user_id"]:
                            st.error("Нельзя удалить самого себя.")
                        else:
                            st.session_state[f"confirm_delete_{user['id']}"] = True
                            st.rerun()
                else:
                    st.warning(f"Точно удалить {user['username']}?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Да", key=f"yes_{user['id']}"):
                            success, msg = delete_user(user["id"])
                            if success:
                                st.success(msg)
                                st.session_state[f"confirm_delete_{user['id']}"] = False
                                st.rerun()
                            else:
                                st.error(msg)
                                st.session_state[f"confirm_delete_{user['id']}"] = False
                                st.rerun()
                    with col_no:
                        if st.button("Нет", key=f"no_{user['id']}"):
                            st.session_state[f"confirm_delete_{user['id']}"] = False
                            st.rerun()