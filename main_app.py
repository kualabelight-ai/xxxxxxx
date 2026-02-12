import streamlit as st
import json
from pathlib import Path
import os
from datetime import datetime

# --- CSS стили для всего приложения ---
def local_css():
    st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .phase-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    .phase-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .phase-active {
        border-left: 5px solid #4CAF50;
        background-color: #f8fff8;
    }
    .phase-completed {
        border-left: 5px solid #2196F3;
    }
    .phase-pending {
        border-left: 5px solid #9E9E9E;
        opacity: 0.8;
    }
    .phase-title {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .phase-description {
        color: #666;
        font-size: 0.9em;
        margin-bottom: 15px;
    }
    .app-title {
        text-align: center;
        padding: 20px 0;
        background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 30px;
    }
    .data-transfer-info {
        background-color: #e8f5e9;
        border: 1px solid #c8e6c9;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    .ai-config-info {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Класс для управления состоянием ---
class AppState:
    def __init__(self):
        # Инициализация состояния приложения
        if 'current_phase' not in st.session_state:
            st.session_state.current_phase = 1

        if 'app_data' not in st.session_state:
            st.session_state.app_data = {
                'phase1': {},
                'phase2': {},
                'phase3': {},  # Данные редактирования блоков (если нужно)
                'phase4': {},
                'phase5': {},
                'phase6': {},# Данные генерации промптов
                'category': '',
                'project_name': 'Новый проект'
            }
        if 'phase6_auto_load' not in st.session_state:
            st.session_state.phase6_auto_load = True
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
def show_phase_card(phase_num, title, description, icon, status="pending"):
    """Отображает карточку фазы"""

    status_classes = {
        "active": "phase-active",
        "completed": "phase-completed",
        "pending": "phase-pending"
    }

    status_icons = {
        "active": "▶️",
        "completed": "✅",
        "pending": "⏸️"
    }

    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown(f"<div style='text-align: center; font-size: 24px;'>{status_icons[status]}</div>",
                    unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="phase-card {status_classes[status]}">
            <div class="phase-title">{icon} Фаза {phase_num}: {title}</div>
            <div class="phase-description">{description}</div>
        </div>
        """, unsafe_allow_html=True)

        if status == "active":
            if st.button(f"Перейти к фазе {phase_num}", key=f"goto_phase_{phase_num}", use_container_width=True):
                st.session_state.current_phase = phase_num
                st.rerun()


# --- Главное приложение ---
def main():
    st.set_page_config(
        page_title="Data Harvester Pro",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    local_css()

    # Инициализация дополнительных состояний
    if 'show_ai_config' not in st.session_state:
        st.session_state.show_ai_config = False

    # Заголовок приложения
    st.markdown("""
    <div class="app-title">
        <h1>🚀 Data Harvester Pro</h1>
        <p>Комплексная система обработки данных и генерации промптов с AI</p>
    </div>
    """, unsafe_allow_html=True)

    # Инициализация состояния
    app_state = AppState()

    # Боковая панель
    with st.sidebar:
        st.header("📊 Статус передачи данных")

        # Информация о передаче данных между фазами
        phase1_data = app_state.get_phase_data(1)
        phase2_data = app_state.get_phase_data(2)
        phase3_data = app_state.get_phase_data(3)
        phase4_data = app_state.get_phase_data(4)
        phase5_data = app_state.get_phase_data(5)
        phase6_data = app_state.get_phase_data(6)
        if phase1_data:
            st.markdown("<div class='data-transfer-info'>", unsafe_allow_html=True)
            st.success("✅ Фаза 1: Данные готовы")
            category = phase1_data.get('category', 'Не указана')
            chars_count = len(phase1_data.get('characteristics', []))
            st.write(f"**Категория:** {category}")
            st.write(f"**Характеристик:** {chars_count}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ Фаза 1: Данные не обработаны")

        if phase2_data:
            st.markdown("<div class='data-transfer-info'>", unsafe_allow_html=True)
            st.success("✅ Фаза 2: Маркеры готовы")
            markers_count = len(phase2_data.get('markers', []))
            st.write(f"**Маркеров:** {markers_count}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("ℹ️ Фаза 2: Ожидает данные")

        # Фаза 3 - редактирование блоков
        blocks_dir = Path("blocks")
        if blocks_dir.exists() and any(blocks_dir.iterdir()):
            st.markdown("<div class='data-transfer-info'>", unsafe_allow_html=True)
            st.success("✅ Фаза 3: Блоки доступны")
            block_count = len([d for d in blocks_dir.iterdir() if d.is_dir()])
            st.write(f"**Блоков:** {block_count}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("ℹ️ Фаза 3: Блоки не созданы")

        # Фаза 4 - генерация промптов
        if phase4_data:
            st.markdown("<div class='data-transfer-info'>", unsafe_allow_html=True)
            st.success("✅ Фаза 4: Промпты сгенерированы")
            prompts_count = len(phase4_data.get('prompts', []))
            st.write(f"**Промптов:** {prompts_count}")
            if 'characteristics_count' in phase4_data:
                st.write(f"**Характеристик:** {phase4_data['characteristics_count']}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("ℹ️ Фаза 4: Промпты не сгенерированы")


        if phase5_data:
            st.markdown("<div class='data-transfer-info'>", unsafe_allow_html=True)
            st.success("✅ Фаза 5: Тексты сгенерированы")
            texts_count = len(phase5_data.get('results', {}))
            st.write(f"**Текстов:** {texts_count}")
            if 'statistics' in phase5_data:
                stats = phase5_data['statistics']
                st.write(f"**Успешно:** {stats.get('success', 0)}")
                st.write(f"**Ошибки:** {stats.get('error', 0)}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("ℹ️ Фаза 5: Тексты не сгенерированы")
        st.divider()
        st.header("📊 Фаза 6: Постобработка")

        phase6_data = app_state.get_phase_data(6)
        if phase6_data:
            if phase6_data.get('processed'):
                st.success("✅ Фаза 6: Данные обработаны")
                # Показать специфичную для фазы 6 статистику
                if 'analysis_stats' in phase6_data:
                    stats = phase6_data['analysis_stats']
                    st.write(f"**Проанализировано:** {stats.get('analyzed', 0)} текстов")
                    st.write(f"**Экспортировано:** {stats.get('exported', 0)} файлов")
            else:
                st.info("ℹ️ Фаза 6: Данные готовы для обработки")
        else:
            st.info("ℹ️ Фаза 6: Ожидает данных из фазы 5")
        st.divider()

        # AI настройки
        st.header("🤖 AI Настройки")

        # Проверяем наличие конфигурации AI
        ai_config_file = Path("config/ai_config.json")
        has_ai_config = ai_config_file.exists()

        if has_ai_config:
            try:
                with open(ai_config_file, 'r', encoding='utf-8') as f:
                    ai_config = json.load(f)
                    provider = ai_config.get("default_provider", "openai")
                    provider_config = ai_config.get("providers", {}).get(provider, {})
                    api_key_set = bool(provider_config.get("api_key", ""))

                    if api_key_set:
                        st.success(f"✅ {provider.upper()} настроен")
                    else:
                        st.warning(f"⚠️ {provider.upper()} требует настройки API ключа")
            except:
                st.warning("⚠️ Настройки AI требуют проверки")
        else:
            st.info("ℹ️ AI не настроен")

        # Кнопка для открытия настроек AI
        if st.button("⚙️ Настроить AI", use_container_width=True):
            st.session_state.show_ai_config = True

        # Если нажали кнопку настроек AI
        if st.session_state.get('show_ai_config', False):
            st.markdown("<div class='ai-config-info'>", unsafe_allow_html=True)
            st.info("AI настройки открыты в основном окне")
            if st.button("← Закрыть AI настройки", use_container_width=True):
                st.session_state.show_ai_config = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # Быстрый переход
        st.header("⚡ Быстрый переход")

        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

        with col1:
            if st.button("1️⃣", use_container_width=True, disabled=st.session_state.current_phase == 1,
                         key="quick_1"):
                st.session_state.current_phase = 1
                st.rerun()

        with col2:
            if st.button("2️⃣", use_container_width=True, disabled=st.session_state.current_phase == 2,
                         key="quick_2"):
                st.session_state.current_phase = 2
                st.rerun()

        with col3:
            if st.button("3️⃣", use_container_width=True, disabled=st.session_state.current_phase == 3,
                         key="quick_3"):
                st.session_state.current_phase = 3
                st.rerun()

        with col4:
            if st.button("4️⃣", use_container_width=True, disabled=st.session_state.current_phase == 4,
                         key="quick_4"):
                st.session_state.current_phase = 4
                st.rerun()

        with col5:
            if st.button("5️⃣", use_container_width=True, disabled=st.session_state.current_phase == 5,
                         key="quick_5"):
                st.session_state.current_phase = 5
                st.rerun()

        with col6:
            if st.button("6️⃣", use_container_width=True, disabled=st.session_state.current_phase == 6,
                         key="quick_6"):
                st.session_state.current_phase = 6  # ДОБАВЬТЕ ЭТУ СТРОКУ
                st.rerun()

        with col7:
            if st.button("⚙️", use_container_width=True, disabled=st.session_state.show_ai_config,
                         key="quick_ai"):
                st.session_state.show_ai_config = True  # ДОБАВЬТЕ ЭТУ СТРОКУ
                st.rerun()



    # Показываем настройки AI если нужно
    if st.session_state.get('show_ai_config', False):
        st.markdown("---")
        st.title("🤖 Настройки AI")

        # Кнопка возврата
        col_back1, col_back2 = st.columns([1, 5])
        with col_back1:
            if st.button("← Вернуться", use_container_width=True):
                st.session_state.show_ai_config = False
                st.rerun()

        # Загружаем интерфейс настроек AI
        try:
            from ai_config import show_ai_config_interface
            show_ai_config_interface()
        except ImportError:
            st.error("Модуль ai_config.py не найден. Убедитесь, что файл существует в той же директории.")
            st.code("""
            Создайте файл ai_config.py с содержимым из предоставленного кода.

            Или временно отключите AI настройки кнопкой выше.
            """)
        except Exception as e:
            st.error(f"Ошибка загрузки настроек AI: {e}")

        return  # Прерываем выполнение, чтобы не показывать основное меню

    # Основная область - отображение фаз
    st.header("🎯 Этапы обработки данных")

    # Определяем статусы фаз
    phase_status = {}
    for phase in [1, 2, 3, 4, 5, 6]:  # Добавили фазу 5
        if phase == st.session_state.current_phase:
            phase_status[phase] = "active"
        elif phase == 3:
            # Для фазы 3 проверяем наличие блоков
            blocks_dir = Path("blocks")
            has_blocks = blocks_dir.exists() and any(blocks_dir.iterdir())
            phase_status[phase] = "completed" if has_blocks else "pending"
        elif phase == 4:
            # Для фазы 4 проверяем наличие промптов
            has_prompts = bool(st.session_state.app_data.get('phase4', {}).get('prompts', []))
            phase_status[phase] = "completed" if has_prompts else "pending"
        elif phase == 5:
            # Для фазы 5 проверяем наличие сгенерированных текстов
            has_results = bool(st.session_state.app_data.get('phase5', {}).get('results', {}))
            phase_status[phase] = "completed" if has_results else "pending"
        elif phase == 6:  # НОВОЕ: проверка для фазы 6
            phase6_data = app_state.get_phase_data(6)
            # Фаза 6 считается завершенной, если в ней есть данные
            phase_status[phase] = "completed" if phase6_data else "pending"
        else:
            phase_status[phase] = "completed" if st.session_state.app_data.get(f'phase{phase}') else "pending"


    # Отображаем карточки фаз - теперь 5 колонок
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    with col1:
        show_phase_card(
            1,
            "Сбор характеристик",
            "Загрузка и фильтрация характеристик товаров",
            "📦",
            phase_status[1]
        )

    with col2:
        show_phase_card(
            2,
            "Управление маркерами",
            "Настройка ключевых слов для категорий",
            "🏷️",
            phase_status[2]
        )

    with col3:
        show_phase_card(
            3,
            "Редактирование блоков",
            "Создание и настройка шаблонов промптов с AI",
            "📝",
            phase_status[3]
        )

    with col4:
        show_phase_card(
            4,
            "Генерация промптов",
            "Создание промптов для ИИ на основе данных",
            "🚀",
            phase_status[4]
        )

    with col5:
        show_phase_card(
            5,
            "Генерация текстов",
            "Создание текстов через ИИ и форматирование",
            "📄",
            phase_status[5]
        )
    with col6:
        show_phase_card(
            6,
             "Анализ и экспорт",
            "Анализ результатов и финальный экспорт",
            "📊",
            phase_status[6]
        )

    with col7:
        # Карточка для настроек AI (не фаза, а отдельная страница)
        st.markdown(f"""
        <div class="phase-card phase-pending">
            <div class="phase-title">⚙️ Настройки AI</div>
            <div class="phase-description">Управление AI API и параметрами генерации</div>
        </div>
        """, unsafe_allow_html=True)

        # Кнопка для перехода к настройкам AI
        if st.button("⚙️ Открыть настройки AI", key="goto_ai_config", use_container_width=True):
            st.session_state.show_ai_config = True
            st.rerun()

    st.divider()

    # Отображение текущей активной фазы
    st.header(f"🎮 Текущая фаза: {st.session_state.current_phase}")

    # Информация о передаче данных
    phase1_data = app_state.get_phase_data(1)
    phase2_data = app_state.get_phase_data(2)
    phase4_data = app_state.get_phase_data(4)

    if st.session_state.current_phase == 2 and phase1_data:
        st.info(
            f"📥 Данные из фазы 1 автоматически переданы: **{phase1_data.get('category', 'Категория')}** ({len(phase1_data.get('characteristics', []))} характеристик)")

    elif st.session_state.current_phase == 3:
        if phase1_data and phase2_data:
            st.success(
                f"✅ Данные для работы: {phase1_data.get('category', 'Категория')} с {len(phase2_data.get('markers', []))} маркерами")
            st.info("💡 Фаза 3 поддерживает AI-генерацию инструкций для переменных. Настройте AI в боковой панели.")
        else:
            st.info("ℹ️ Фаза 3 работает независимо от данных, но для тестирования шаблонов нужны данные из фазы 1 и 2")

    elif st.session_state.current_phase == 4:
        if phase1_data and phase2_data:
            st.success(
                f"✅ Все данные готовы: {phase1_data.get('category', 'Категория')} с {len(phase2_data.get('markers', []))} маркерами и {len(phase1_data.get('characteristics', []))} характеристиками")
        else:
            st.warning("⚠️ Для генерации промптов нужны данные из фазы 1 и 2")
    elif st.session_state.current_phase == 5:
        if phase1_data and phase2_data and phase4_data:
            st.success(
                f"✅ Все данные готовы: {phase1_data.get('category', 'Категория')} с {len(phase2_data.get('markers', []))} маркерами, {len(phase1_data.get('characteristics', []))} характеристиками и {len(phase4_data.get('prompts', []))} промптами")

            # Проверяем наличие AI конфигурации для фазы 5
            ai_config_file = Path("config/ai_config.json")
            if ai_config_file.exists():
                try:
                    with open(ai_config_file, 'r', encoding='utf-8') as f:
                        ai_config = json.load(f)
                        provider = ai_config.get("default_provider", "openai")
                        provider_config = ai_config.get("providers", {}).get(provider, {})
                        if provider_config.get("api_key"):
                            st.info(f"🤖 AI готов к работе ({provider.upper()})")
                        else:
                            st.warning(
                                f"⚠️ AI требует настройки API ключа для {provider}. Генерация текстов невозможна.")
                except:
                    st.warning("⚠️ Проверьте настройки AI в боковой панели")
            else:
                st.error("❌ AI не настроен. Для генерации текстов необходимо настроить AI в боковой панели.")
        else:
            st.warning("""
            ## ⚠️ Недостаточно данных для фазы 5

            Для работы фазы 5 необходимо:

            1. **Выполнить фазу 1** - собрать характеристики товаров
            2. **Выполнить фазу 2** - настроить маркеры категории
            3. **Выполнить фазу 4** - сгенерировать промпты

            Данные автоматически передаются между фазами.
            """)

            if not phase1_data:
                st.error("❌ Фаза 1 не выполнена")
            if not phase2_data:
                st.error("❌ Фаза 2 не выполнена")
            if not phase4_data:
                st.error("❌ Фаза 4 не выполнена")

            col_back1, col_back2, col_back3, col_back4 = st.columns(4)
            with col_back1:
                if st.button("← Вернуться к фазе 1", use_container_width=True):
                    st.session_state.current_phase = 1
                    st.rerun()
            with col_back2:
                if st.button("← Вернуться к фазе 2", use_container_width=True):
                    st.session_state.current_phase = 2
                    st.rerun()
            with col_back3:
                if st.button("← Вернуться к фазе 3", use_container_width=True):
                    st.session_state.current_phase = 3
                    st.rerun()
            with col_back4:
                if st.button("← Вернуться к фазе 4", use_container_width=True):
                    st.session_state.current_phase = 4
                    st.rerun()
    # Загрузка соответствующей фазы
    if st.session_state.current_phase == 1:
        try:
            import phase1
            phase1.main()
        except Exception as e:
            st.error(f"Ошибка загрузки фазы 1: {e}")

    elif st.session_state.current_phase == 2:
        # Проверяем, есть ли данные для фазы 2
        if phase1_data:
            try:
                import phase2
                phase2.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 2: {e}")
        else:
            st.warning("""
            ## ⚠️ Недостаточно данных для фазы 2

            Для работы фазы 2 необходимо:

            1. **Выполнить фазу 1** - собрать характеристики товаров

            Данные автоматически передаются между фазами.
            """)

            if st.button("← Вернуться к фазе 1", use_container_width=True):
                st.session_state.current_phase = 1
                st.rerun()

    elif st.session_state.current_phase == 3:
        # Фаза 3 (редактирование блоков) может работать без данных предыдущих фаз
        try:
            import phase3
            phase3.main()
        except Exception as e:
            st.error(f"Ошибка загрузки фазы 3: {e}")

    elif st.session_state.current_phase == 4:
        # Проверяем, есть ли данные для фазы 4
        if phase1_data and phase2_data:
            st.success(
                f"✅ Все данные готовы: {phase1_data.get('category', 'Категория')} с {len(phase2_data.get('markers', []))} маркерами и {len(phase1_data.get('characteristics', []))} характеристиками")

            # Проверяем наличие AI конфигурации
            ai_config_file = Path("config/ai_config.json")
            if ai_config_file.exists():
                try:
                    with open(ai_config_file, 'r', encoding='utf-8') as f:
                        ai_config = json.load(f)
                        provider = ai_config.get("default_provider", "openai")
                        provider_config = ai_config.get("providers", {}).get(provider, {})
                        if provider_config.get("api_key"):
                            st.info(f"🤖 AI готов к работе ({provider.upper()})")
                        else:
                            st.warning(f"⚠️ AI требует настройки API ключа для {provider}")
                except:
                    st.warning("⚠️ Проверьте настройки AI в боковой панели")
            else:
                st.info("ℹ️ AI не настроен. Для использования AI-переменных настройте AI в боковой панели.")

            # Загружаем фазу 4
            try:
                import phase4
                phase4.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 4: {e}")
        else:
            st.warning("""
            ## ⚠️ Недостаточно данных для фазы 4

            Для работы фазы 4 необходимо:

            1. **Выполнить фазу 1** - собрать характеристики товаров
            2. **Выполнить фазу 2** - настроить маркеры категории

            Данные автоматически передаются между фазами.
            """)

            if not phase1_data:
                st.error("❌ Фаза 1 не выполнена")
            if not phase2_data:
                st.error("❌ Фаза 2 не выполнена")

            col_back1, col_back2, col_back3 = st.columns(3)
            with col_back1:
                if st.button("← Вернуться к фазе 1", use_container_width=True):
                    st.session_state.current_phase = 1
                    st.rerun()
            with col_back2:
                if st.button("← Вернуться к фазе 2", use_container_width=True):
                    st.session_state.current_phase = 2
                    st.rerun()
            with col_back3:
                if st.button("← Вернуться к фазе 3", use_container_width=True):
                    st.session_state.current_phase = 3
                    st.rerun()
    elif st.session_state.current_phase == 5:
        # Проверяем, есть ли данные для фазы 5
        if phase1_data and phase2_data and phase4_data:
            st.success(
                f"✅ Все данные готовы: {phase1_data.get('category', 'Категория')} с {len(phase2_data.get('markers', []))} маркерами и {len(phase4_data.get('prompts', []))} промптами")

            # Проверяем наличие AI конфигурации
            ai_config_file = Path("config/ai_config.json")
            if ai_config_file.exists():
                try:
                    with open(ai_config_file, 'r', encoding='utf-8') as f:
                        ai_config = json.load(f)
                        provider = ai_config.get("default_provider", "openai")
                        provider_config = ai_config.get("providers", {}).get(provider, {})
                        if provider_config.get("api_key"):
                            st.info(f"🤖 AI готов к работе ({provider.upper()})")
                        else:
                            st.warning(f"⚠️ AI требует настройки API ключа для {provider}")
                except:
                    st.warning("⚠️ Проверьте настройки AI в боковой панели")
            else:
                st.info("ℹ️ AI не настроен. Для генерации текстов настройте AI в боковой панели.")

            # Загружаем фазу 5
            try:
                import phase5
                phase5.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 5: {e}")
        else:
            st.warning("""
               ## ⚠️ Недостаточно данных для фазы 5

               Для работы фазы 5 необходимо:

               1. **Выполнить фазу 1** - собрать характеристики товаров
               2. **Выполнить фазу 2** - настроить маркеры категории
               3. **Выполнить фазу 4** - сгенерировать промпты

               Данные автоматически передаются между фазами.
               """)

            if not phase1_data:
                st.error("❌ Фаза 1 не выполнена")
            if not phase2_data:
                st.error("❌ Фаза 2 не выполнена")
            if not phase4_data:
                st.error("❌ Фаза 4 не выполнена")

            col_back1, col_back2, col_back3, col_back4 = st.columns(4)
            with col_back1:
                if st.button("← Вернуться к фазе 1", use_container_width=True):
                    st.session_state.current_phase = 1
                    st.rerun()
            with col_back2:
                if st.button("← Вернуться к фазе 2", use_container_width=True):
                    st.session_state.current_phase = 2
                    st.rerun()
            with col_back3:
                if st.button("← Вернуться к фазе 3", use_container_width=True):
                    st.session_state.current_phase = 3
                    st.rerun()
            with col_back4:
                if st.button("← Вернуться к фазе 4", use_container_width=True):
                    st.session_state.current_phase = 4
                    st.rerun()
    elif st.session_state.current_phase == 6:
        # Проверяем, есть ли данные для фазы 6
        phase5_data = app_state.get_phase_data(5)

        if phase5_data:  # Основное требование - данные из фазы 5
            st.success(f"✅ Данные из фазы 5 готовы")

            # Проверяем структуру данных
            if isinstance(phase5_data, dict):
                results = phase5_data.get('results', [])
                st.write(f"Найдено {len(results)} текстов")
            else:
                st.warning("⚠️ Данные фазы 5 имеют неожиданный формат")
                results = []

            # Автоматически передаем данные в фазу 6 при первом входе
            if not st.session_state.app_data.get('phase6'):
                # Создаем структурированные данные для фазы 6
                phase6_input_data = {
                    'phase5_data': phase5_data,
                    'category': st.session_state.app_data.get('category', ''),
                    'project_name': st.session_state.app_data.get('project_name', ''),
                    'phase1_data': st.session_state.app_data.get('phase1', {}),
                    'phase2_data': st.session_state.app_data.get('phase2', {}),
                    'phase4_data': st.session_state.app_data.get('phase4', {})
                }

                app_state.set_phase_data(6, {
                    'input_data': phase6_input_data,
                    'processed': False,
                    'received_from_phase5': True,
                    'received_at': datetime.now().isoformat()
                })
                st.info("📥 Данные автоматически переданы из фазы 5")

            # Загружаем фазу 6
            try:
                import phase6
                phase6.main()
            except ImportError:
                st.warning("""
                ## ⚠️ Фаза 6 не реализована
                Модуль `phase6.py` не найден.
                """)

                # Показать структуру переданных данных
                with st.expander("📋 Просмотр переданных данных из фазы 5"):
                    st.json(phase5_data)

            except Exception as e:
                st.error(f"Ошибка загрузки фазы 6: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
        else:
            st.warning("""
            ## ⚠️ Недостаточно данных для фазы 6
            Для работы фазы 6 необходимо:
            1. **Выполнить фазу 5** - сгенерировать тексты
            """)
    # Кнопки навигации
    st.divider()
    col_nav1, col_nav2 = st.columns(2)

    with col_nav1:
        if st.session_state.current_phase > 1:
            if st.button("← Предыдущая фаза", use_container_width=True):
                st.session_state.current_phase -= 1
                st.rerun()

    with col_nav2:
        if st.session_state.current_phase < 6:  # Изменили с 4 на 5
            # Проверяем, есть ли данные для перехода к следующей фазе
            if st.session_state.current_phase == 1:
                # Для перехода к фазе 2 нужны данные фазы 1
                can_proceed = bool(phase1_data)
            elif st.session_state.current_phase == 2:
                # Для перехода к фазе 3 нужны данные фазы 1 и 2
                can_proceed = bool(phase1_data and phase2_data)
            elif st.session_state.current_phase == 3:
                # Для перехода к фазе 4 нужны данные фазы 1 и 2
                can_proceed = bool(phase1_data and phase2_data)
            elif st.session_state.current_phase == 4:
                # Для перехода к фазе 5 нужны данные фазы 1, 2 и 4
                can_proceed = bool(phase1_data and phase2_data and phase4_data)
            elif st.session_state.current_phase == 5:
                can_proceed = bool(phase5_data)
            else:
                can_proceed = True

            if can_proceed:
                if st.button("Следующая фаза →", type="primary", use_container_width=True):
                    st.session_state.current_phase += 1
                    st.rerun()
            else:
                st.warning(f"⚠️ Завершите текущую фазу перед переходом")


if __name__ == "__main__":
    main()