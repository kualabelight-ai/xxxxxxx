from pathlib import Path
import json
from datetime import datetime
import streamlit as st

USER_DATA_DIR = Path("user_data")
USER_DATA_DIR.mkdir(exist_ok=True)

def get_user_state_path(user_id: int = None) -> Path:
    """
    Возвращает путь к файлу состояния для указанного user_id.
    Если user_id не передан, берётся из session_state (должен существовать).
    """
    if user_id is None:
        user_id = st.session_state.get("user_id")
    if user_id is None:
        # Не пытаемся угадать файл – это ошибка использования
        raise ValueError("Cannot determine user state path: no user_id")
    return USER_DATA_DIR / f"state_user_{user_id}.json"

def get_user_container():
    user_id = st.session_state.get("user_id")
    if user_id is None:
        raise ValueError("Нет user_id")
    user_key = f"user_{user_id}"
    if user_key not in st.session_state:
        st.session_state[user_key] = {
            "current_phase": 1,
            "app_data": {
                'phase1': {}, 'phase2': {}, 'phase3': {},
                'phase4': {}, 'phase5': {}, 'phase6': {},
                'category': '', 'project_name': 'Новый проект'
            }
        }
    return st.session_state[user_key]

def save_user_state():
    if "user_id" not in st.session_state:
        return

    user_id = st.session_state["user_id"]

    # Убеждаемся что директория существует
    USER_DATA_DIR.mkdir(exist_ok=True)

    # Собираем только основные данные
    data = {
        "authenticated": st.session_state.get("authenticated", False),
        "user_id": user_id,
        "username": st.session_state.get("username", ""),
        "current_phase": st.session_state.get("current_phase", 1),
        "app_data": st.session_state.get("app_data", {}),
        "last_saved": datetime.now().isoformat(),
    }

    # Сохраняем в файл
    path = USER_DATA_DIR / f"state_user_{user_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
def load_user_state(user_id: int = None) -> bool:
    """
    Загружает состояние пользователя из файла.
    Возвращает True если загрузка успешна, иначе False.
    """
    if user_id is None:
        user_id = st.session_state.get("user_id")
    if user_id is None:
        print("❌ load_user_state: No user_id provided")
        return False

    path = USER_DATA_DIR / f"state_user_{user_id}.json"
    if not path.exists():
        print(f"❌ load_user_state: File not found: {path}")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"📂 load_user_state: Loading state for user {user_id}")

        # Восстанавливаем основные данные
        st.session_state["authenticated"] = data.get("authenticated", False)
        st.session_state["user_id"] = data.get("user_id")
        st.session_state["username"] = data.get("username", "")
        st.session_state["current_phase"] = data.get("current_phase", 1)
        st.session_state["app_data"] = data.get("app_data", {})

        # Создаём или обновляем контейнер пользователя
        user_key = f"user_{user_id}"
        if user_key not in st.session_state:
            st.session_state[user_key] = {}

        st.session_state[user_key]["current_phase"] = st.session_state["current_phase"]
        st.session_state[user_key]["app_data"] = st.session_state["app_data"]

        print(f"✅ load_user_state: Success for user {user_id}")
        print(f"   current_phase: {st.session_state['current_phase']}")
        print(f"   app_data keys: {list(st.session_state['app_data'].keys())}")

        return True

    except Exception as e:
        print(f"❌ load_user_state: Error: {e}")
        return False