import streamlit as st
import json
from pathlib import Path
import os
from datetime import datetime
from styles import load_css
import auth

# --- CSS стили для всего приложения ---
import state_manager

st.set_page_config(
        page_title="Data Harvester Pro",
        layout="wide",
        initial_sidebar_state="expanded"
    )
def local_css():
    st.markdown("""
    <style>
        /* Ретро-минимализм */
        .stApp {
            background-color: #faf7f2;
            color: #3e3a36;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #5e4b3c !important;
            font-family: 'Courier New', monospace;
        }
        .stButton>button {
            background-color: #e6dacd;
            color: #4a3f38;
            border: 1px solid #b7a99a;
            border-radius: 6px;
            font-size: 14px;
            padding: 4px 12px;
            transition: 0.2s;
            font-family: 'Courier New', monospace;
        }
        .stButton>button:hover {
            background-color: #d4c3b2;
            border-color: #8c7a6a;
        }
        div.stAlert {
            background-color: #f0ebe4;
            border-left: 4px solid #b08968;
            color: #3e3a36;
            border-radius: 0;
        }
        div.stSuccess {
            background-color: #e6f0da;
            border-left: 4px solid #7f9f6f;
        }
        div.stWarning {
            background-color: #fff1d6;
            border-left: 4px solid #e6b89c;
        }
        div.stInfo {
            background-color: #e1e7e0;
            border-left: 4px solid #8d9f87;
        }
        hr {
            border-top: 1px solid #d4c3a2;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)


# --- Класс для управления состоянием ---
class AppState:

    def get_phase_data(self, phase):
        """Получает данные для указанной фазы"""
        return st.session_state.app_data.get(f'phase{phase}', {})

    def set_phase_data(self, phase, data):
        """Устанавливает данные для указанной фазы"""
        st.session_state.app_data[f'phase{phase}'] = data

    def get_all_data_for_phase3(self):
        """Собирает все данные для фазы 3 (редактирование)"""
        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', '')
        }

    def get_all_data_for_phase4(self):
        """Собирает все данные для фазы 4 (генерация)"""
        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', '')
        }

    def get_all_data_for_phase5(self):
        """Собирает все данные для фазы 5 (генерация текстов)"""
        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'phase4_data': st.session_state.app_data.get('phase4', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', '')
        }

    def get_all_data_for_phase6(self):
        """Собирает все данные для фазы 6"""
        # Из фазы 5 нужно передать:
        # 1. Результаты генерации текстов
        # 2. Статистику
        # 3. Настройки генерации

        phase5_data = self.get_phase_data(5)

        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'phase4_data': st.session_state.app_data.get('phase4', {}),
            'phase5_data': phase5_data,  # Основные данные из фазы 5

            # Ключевые поля из фазы 5 для удобства доступа:
            'generation_results': phase5_data.get('results', {}),
            'generation_stats': phase5_data.get('statistics', {}),
            'generation_settings': phase5_data.get('generation_settings', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', ''),

            # Дополнительные метаданные
            'total_prompts': phase5_data.get('statistics', {}).get('total', 0),
            'successful_generations': phase5_data.get('statistics', {}).get('success', 0)
        }
# --- Функции для отображения фаз ---


# --- Главное приложение ---

def main():
    # САМОЕ ПЕРВОЕ - проверяем URL параметры
    query_params = st.query_params
    import state_manager
    # Если есть user_id в URL и нет активной сессии - пробуем загрузить
    if "user_id" in query_params and not st.session_state.get("authenticated", False):
        user_id = int(query_params["user_id"])
        print(f"🔍 Found user_id in URL: {user_id}, attempting to load state")

        # Загружаем состояние
        if state_manager.load_user_state(user_id):
            print(f"✅ State loaded successfully for user {user_id}")
            # Принудительно устанавливаем authenticated
            st.session_state.authenticated = True
            st.session_state.user_id = user_id
        else:
            print(f"❌ Failed to load state for user {user_id}")
            st.query_params.clear()

    # Проверка авторизации
    if not st.session_state.get("authenticated", False):
        print("Not authenticated, showing login form")
        auth.login_form()
        return

    # Финальная проверка - есть ли user_id в сессии
    if "user_id" not in st.session_state:
        print("ERROR: Authenticated but no user_id!")
        auth.logout()
        return

    print(f"✅ Authenticated as user {st.session_state['user_id']}, continuing to main app")
    if 'app_data' in st.session_state:
        app_data = st.session_state.app_data

        # Синхронизируем phase1_data
        if 'phase1' in app_data and app_data['phase1']:
            st.session_state.phase1_data = app_data['phase1']
            print("🔄 Synced phase1_data")

        # Синхронизируем phase2_data/markers
        if 'phase2' in app_data and app_data['phase2']:
            st.session_state.phase2_data = app_data['phase2']
            if 'markers' in app_data['phase2']:
                st.session_state.phase2_markers = app_data['phase2']['markers']
                st.session_state.markers_data = app_data['phase2']['markers']
            print("🔄 Synced phase2_data")

        # Синхронизируем phase3_data
        if 'phase3' in app_data and app_data['phase3']:
            st.session_state.phase3_data = app_data['phase3']
            print("🔄 Synced phase3_data")

        # Синхронизируем category
        if 'category' in app_data and app_data['category']:
            st.session_state.category_name = app_data['category']
            st.session_state.selected_category = app_data['category']
            print(f"🔄 Synced category: {app_data['category']}")

    # Также восстанавливаем контейнер пользователя если нужно
    user_key = f"user_{st.session_state['user_id']}"
    if user_key in st.session_state:
        container = st.session_state[user_key]
        if 'app_data' in container:
            # Если в контейнере есть данные, но нет в основных ключах
            if not st.session_state.get('phase1_data') and 'phase1' in container['app_data']:
                st.session_state.phase1_data = container['app_data']['phase1']
    # Убеждаемся что user_id есть в URL
    if "user_id" not in st.query_params:
        st.query_params["user_id"] = str(st.session_state["user_id"])
    print("\n🔍 DEBUG: Checking data after authentication:")
    print(f"📊 current_phase: {st.session_state.get('current_phase')}")
    print(f"📊 app_data keys: {list(st.session_state.get('app_data', {}).keys())}")
    print(f"📊 phase1 exists: {'phase1' in st.session_state.get('app_data', {})}")
    if 'phase1' in st.session_state.get('app_data', {}):
        print(f"📊 phase1 category: {st.session_state.app_data['phase1'].get('category', 'N/A')}")
        print(f"📊 phase1 characteristics: {len(st.session_state.app_data['phase1'].get('characteristics', []))}")

    # Проверяем контейнер пользователя
    user_key = f"user_{st.session_state['user_id']}"
    if user_key in st.session_state:
        print(f"📊 container {user_key} exists")
        print(f"📊 container phase: {st.session_state[user_key].get('current_phase')}")
        print(f"📊 container app_data keys: {list(st.session_state[user_key].get('app_data', {}).keys())}")
    else:
        print(f"❌ container {user_key} NOT found!")
    user_key = f"user_{st.session_state['user_id']}"
    if user_key in st.session_state:
        container = st.session_state[user_key]

        # Если в основных ключах нет данных, но есть в контейнере - восстанавливаем
        if not st.session_state.get('app_data') or not st.session_state.app_data.get('phase1'):
            print("⚠️ Основные ключи пусты, восстанавливаем из контейнера")
            st.session_state.current_phase = container.get('current_phase', 1)
            st.session_state.app_data = container.get('app_data', {})
            print(f"✅ Восстановлено: phase1 exists: {'phase1' in st.session_state.app_data}")
    # ─── Дальше идёт весь остальной код приложения ───
    load_css()

    # Верхняя панель
    col_logo, col_ai, col_reset, col_user = st.columns([5, 1, 1, 1])   # ← добавили ещё одну колонку
    with col_logo:
        st.markdown("<h1>📀 DH Data Harvester Pro</h1>", unsafe_allow_html=True)
    with col_ai:
        if st.button("⚙️ AI", help="Настройки AI"):
            st.session_state.show_ai_config = True
            st.rerun()


    # ─── НОВАЯ КНОПКА СБРОСА ────────────────────────────────────────────────
    with col_reset:
        if st.button("🗑️", help="Сбросить проект (очистить прогресс)"):
            with st.spinner("Сброс состояния..."):
                try:
                    # 1. Удаляем файл сохранения (самое важное!)
                    path = state_manager.get_user_state_path()
                    if path.exists():
                        path.unlink(missing_ok=True)
                        st.toast("Файл сохранения удалён", icon="🗑️")

                    # 2. Принудительно очищаем ВСЕ возможные ключи
                    keys_to_reset = [
                        "current_phase",
                        "app_data",
                        "state_restored",
                        "session_restored",
                        "last_auto_save",
                        # добавь сюда любые другие ключи, которые используешь в проекте
                    ]

                    for key in list(st.session_state.keys()):  # ← берём копию списка!
                        if key in keys_to_reset or key.startswith("phase"):  # на всякий случай
                            del st.session_state[key]

                    # 3. Явно устанавливаем чистое состояние
                    st.session_state.current_phase = 1
                    st.session_state.app_data = {
                        'phase1': {}, 'phase2': {}, 'phase3': {},
                        'phase4': {}, 'phase5': {}, 'phase6': {},
                        'category': '',
                        'project_name': 'Новый проект'
                    }

                    # 4. Запрещаем автозагрузку старого состояния в ближайший rerun
                    st.session_state.session_restored = False
                    st.session_state.state_restored = False

                    st.success("Проект сброшен. Переходим на фазу 1...", icon="✅")

                    # 5. Небольшая задержка + rerun (иногда помогает Streamlit'у применить изменения)
                    import time
                    time.sleep(0.4)  # 400 мс — обычно достаточно
                    st.rerun()

                except Exception as e:
                    st.error(f"Ошибка сброса: {str(e)}")
    with col_user:
        if st.button("👤 Профиль"):
            st.session_state.show_profile = True
            st.rerun()
    # Отображение профиля, если нужно
    if st.session_state.get("show_admin_panel", False):
        auth.admin_panel()
        if st.button("← Назад к приложению"):
            st.session_state.show_admin_panel = False
            st.rerun()

    if st.session_state.get("show_profile", False):
        auth.profile_page()

    # Здесь продолжается ваш основной код (фазы, навигация и т.д.)
    # Например:
    st.write("Добро пожаловать,", st.session_state["username"])
    # ===============================================================

    # Инициализация состояния приложения
    app_state = AppState()

    # ============ КОМПАКТНАЯ ПАНЕЛЬ ФАЗ (только этапы) ============
    st.markdown("")  # небольшой отступ

    # Определяем статусы фаз (логика без дублирования)
    phase_status = {}
    for phase in [1, 2, 3, 4, 5, 6]:
        if phase == st.session_state.current_phase:
            phase_status[phase] = "active"
        elif phase == 3:
            blocks_dir = Path("blocks")
            has_blocks = blocks_dir.exists() and any(blocks_dir.iterdir())
            phase_status[phase] = "completed" if has_blocks else "pending"
        elif phase == 4:
            has_prompts = bool(st.session_state.app_data.get('phase4', {}).get('prompts', []))
            phase_status[phase] = "completed" if has_prompts else "pending"
        elif phase == 5:
            has_results = bool(st.session_state.app_data.get('phase5', {}).get('results', {}))
            phase_status[phase] = "completed" if has_results else "pending"
        elif phase == 6:
            phase6_data = app_state.get_phase_data(6)
            phase_status[phase] = "completed" if phase6_data else "pending"
        else:
            phase_status[phase] = "completed" if st.session_state.app_data.get(f'phase{phase}') else "pending"

    # Отображаем фазы компактно
    phase_cols = st.columns(6)
    icons = ["📦", "🏷️", "📝", "🚀", "📄", "📊"]
    titles = ["Сбор", "Маркеры", "Блоки", "Промпты", "Тексты", "Анализ"]

    for i, col in enumerate(phase_cols, 1):
        with col:
            status = phase_status[i]
            if status == "active":
                bg = "#f0e6d2"
                border = "2px solid #b08968"
            elif status == "completed":
                bg = "#e6f0da"
                border = "1px solid #7f9f6f"
            else:
                bg = "#f5f0e6"
                border = "1px solid #d4c3a2"

            st.markdown(f"""
            <div style="background-color: {bg}; border: {border}; border-radius: 8px; padding: 6px 4px; text-align: center; margin-bottom: 5px;">
                <div style="font-size: 20px;">{icons[i-1]}</div>
                <div style="font-size: 12px; font-weight: bold;">{titles[i-1]}</div>
                <div style="font-size: 11px; color: #5e4b3c;">Фаза {i}</div>
            </div>
            """, unsafe_allow_html=True)

            # Маленькая кнопка перехода без растяжения
            if st.button("▶", key=f"phase_{i}"):
            # Сохраняем ТОЛЬКО нужные данные перед переходом
                if "user_id" in st.session_state:
                    user_id = st.session_state.user_id
                    user_key = f"user_{user_id}"

                    # Обновляем app_data из всех источников
                    if 'phase1_data' in st.session_state:
                        st.session_state.app_data['phase1'] = st.session_state.phase1_data
                    if 'phase2_data' in st.session_state:
                        st.session_state.app_data['phase2'] = st.session_state.phase2_data
                    if 'phase2_markers' in st.session_state:
                        if 'phase2' not in st.session_state.app_data:
                            st.session_state.app_data['phase2'] = {}
                        st.session_state.app_data['phase2']['markers'] = st.session_state.phase2_markers
                    if 'category_name' in st.session_state:
                        st.session_state.app_data['category'] = st.session_state.category_name

                    # Обновляем контейнер пользователя
                    if user_key in st.session_state:
                        st.session_state[user_key]['app_data'] = st.session_state.app_data
                        st.session_state[user_key]['current_phase'] = i

                    # Сохраняем в файл ТОЛЬКО основные данные
                    from state_manager import save_user_state
                    save_user_state()

                st.session_state.current_phase = i
                st.rerun()

    st.markdown("---")  # разделитель перед контентом фазы
    # ===============================================================

    # ============ ПРОВЕРКА НАСТРОЕК AI ============
    if st.session_state.get('show_ai_config', False):
        st.markdown("---")
        st.title("🤖 Настройки AI")
        if st.button("← Вернуться"):
            st.session_state.show_ai_config = False
            st.rerun()

        try:
            from ai_config import show_ai_config_interface
            show_ai_config_interface()
        except Exception as e:
            st.error(f"Ошибка загрузки настроек AI: {e}")
        return  # не показываем фазы
    # ==============================================

    # ============ ЗАГРУЗКА ТЕКУЩЕЙ ФАЗЫ ============
    phase1_data = app_state.get_phase_data(1)
    phase2_data = app_state.get_phase_data(2)
    phase4_data = app_state.get_phase_data(4)
    phase5_data = app_state.get_phase_data(5)

    if st.session_state.current_phase == 1:
        try:
            import phase1
            phase1.main()
        except Exception as e:
            st.error(f"Ошибка загрузки фазы 1: {e}")

    elif st.session_state.current_phase == 2:
        if phase1_data:
            try:
                import phase2
                phase2.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 2: {e}")
        else:
            st.warning("⚠️ Сначала выполните фазу 1")
            if st.button("← Перейти к фазе 1"):
                st.session_state.current_phase = 1
                st.rerun()

    elif st.session_state.current_phase == 3:
        try:
            import phase3
            phase3.main()
        except Exception as e:
            st.error(f"Ошибка загрузки фазы 3: {e}")

    elif st.session_state.current_phase == 4:
        if phase1_data and phase2_data:
            try:
                import phase4
                phase4.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 4: {e}")
        else:
            st.warning("⚠️ Сначала выполните фазы 1 и 2")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Фаза 1"):
                    st.session_state.current_phase = 1
                    st.rerun()
            with col2:
                if st.button("← Фаза 2"):
                    st.session_state.current_phase = 2
                    st.rerun()

    elif st.session_state.current_phase == 5:
        if phase1_data and phase2_data and phase4_data:
            try:
                import phase5
                phase5.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 5: {e}")
        else:
            st.warning("⚠️ Сначала выполните фазы 1, 2 и 4")
            cols = st.columns(3)
            with cols[0]:
                if st.button("← Фаза 1"):
                    st.session_state.current_phase = 1
                    st.rerun()
            with cols[1]:
                if st.button("← Фаза 2"):
                    st.session_state.current_phase = 2
                    st.rerun()
            with cols[2]:
                if st.button("← Фаза 4"):
                    st.session_state.current_phase = 4
                    st.rerun()

    elif st.session_state.current_phase == 6:
        if phase5_data:
            try:
                import phase6
                phase6.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 6: {e}")
        else:
            st.warning("⚠️ Сначала выполните фазу 5")
            if st.button("← Фаза 5"):
                st.session_state.current_phase = 5
                st.rerun()
    # ==============================================
    # ============ НАВИГАЦИЯ МЕЖДУ ФАЗАМИ ============
    st.markdown("---")
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    with col_nav1:
        if st.session_state.current_phase > 1:
            if st.button("← Предыдущая фаза"):
                # Сохраняем перед переходом
                if "user_id" in st.session_state:
                    # Обновляем данные из отдельных ключей в app_data
                    if 'phase1_data' in st.session_state:
                        st.session_state.app_data['phase1'] = st.session_state.phase1_data
                    if 'phase2_data' in st.session_state:
                        st.session_state.app_data['phase2'] = st.session_state.phase2_data
                    if 'phase2_markers' in st.session_state:
                        if 'phase2' not in st.session_state.app_data:
                            st.session_state.app_data['phase2'] = {}
                        st.session_state.app_data['phase2']['markers'] = st.session_state.phase2_markers
                    if 'category_name' in st.session_state:
                        st.session_state.app_data['category'] = st.session_state.category_name

                    # ИМПОРТИРУЕМ state_manager и сохраняем
                    import state_manager
                    state_manager.save_user_state()

                st.session_state.current_phase -= 1
                st.rerun()

    with col_nav3:
        # Определяем, можно ли перейти к следующей фазе
        can_proceed = False
        current = st.session_state.current_phase

        if current == 1:
            can_proceed = bool(app_state.get_phase_data(1))
        elif current == 2:
            can_proceed = bool(app_state.get_phase_data(1) and app_state.get_phase_data(2))
        elif current == 3:
            blocks_dir = Path("blocks")
            has_blocks = blocks_dir.exists() and any(blocks_dir.iterdir())
            can_proceed = has_blocks
        elif current == 4:
            can_proceed = bool(app_state.get_phase_data(1) and app_state.get_phase_data(2) and app_state.get_phase_data(4))
        elif current == 5:
            can_proceed = bool(app_state.get_phase_data(1) and app_state.get_phase_data(2) and app_state.get_phase_data(4) and app_state.get_phase_data(5))
        elif current == 6:
            can_proceed = bool(app_state.get_phase_data(5))

        if current < 6:
            if can_proceed:
                if st.button("Следующая фаза →", type="primary"):
                    # Сохраняем перед переходом
                    if "user_id" in st.session_state:
                        # Обновляем данные из отдельных ключей в app_data
                        if 'phase1_data' in st.session_state:
                            st.session_state.app_data['phase1'] = st.session_state.phase1_data
                        if 'phase2_data' in st.session_state:
                            st.session_state.app_data['phase2'] = st.session_state.phase2_data
                        if 'phase2_markers' in st.session_state:
                            if 'phase2' not in st.session_state.app_data:
                                st.session_state.app_data['phase2'] = {}
                            st.session_state.app_data['phase2']['markers'] = st.session_state.phase2_markers
                        if 'category_name' in st.session_state:
                            st.session_state.app_data['category'] = st.session_state.category_name

                        import state_manager
                        state_manager.save_user_state()

                    st.session_state.current_phase += 1
                    st.rerun()
            else:
                st.info("⚠️ Завершите текущую фазу, чтобы перейти дальше")
    # Автосохранение каждые 30–60 сек или при смене фазы
    now = datetime.now()
    if "last_auto_save" not in st.session_state:
        st.session_state.last_auto_save = now

    if (now - st.session_state.last_auto_save).total_seconds() > 5:
        state_manager.save_user_state()
        st.session_state.last_auto_save = now
    # =================================================

if __name__ == "__main__":
    main()