# state_manager.py
from pathlib import Path
import json
from datetime import datetime
import streamlit as st

USER_DATA_DIR = Path("user_data")
USER_DATA_DIR.mkdir(exist_ok=True)


def get_user_state_path() -> Path:
    # Если user_id уже есть — используем его
    user_id = st.session_state.get("user_id")
    if user_id is not None:
        return USER_DATA_DIR / f"state_user_{user_id}.json"

    # Если user_id ещё нет — ищем самый свежий файл вообще
    candidates = list(USER_DATA_DIR.glob("state_user_*.json"))
    if not candidates:
        return Path("dummy_never_used.json")

    # Самый свежий по времени модификации
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest


# state_manager.py (замени соответствующие функции)

def save_user_state():
    if "user_id" not in st.session_state:
        return

    path = get_user_state_path()

    data = {
        "authenticated": st.session_state.get("authenticated", False),
        "user_id": st.session_state.get("user_id"),
        "username": st.session_state.get("username", ""),
        "current_phase": st.session_state.get("current_phase", 1),
        "app_data": st.session_state.get("app_data", {}),
        "last_saved": datetime.now().isoformat(),
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Ошибка сохранения состояния: {e}")


def load_user_state() -> bool:
    path = get_user_state_path()
    if not path.exists():
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Восстанавливаем авторизацию
        if data.get("authenticated", False):
            st.session_state.authenticated = True
            st.session_state.user_id = data.get("user_id")
            st.session_state.username = data.get("username", "")

        # Восстанавливаем состояние приложения
        st.session_state.current_phase = data.get("current_phase", 1)
        st.session_state.app_data = data.get("app_data", {
            'phase1': {}, 'phase2': {}, 'phase3': {},
            'phase4': {}, 'phase5': {}, 'phase6': {},
            'category': '', 'project_name': 'Новый проект'
        })

        return True
    except Exception as e:
        st.warning(f"Не удалось загрузить сохранение: {e}")
        return False