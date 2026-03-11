import streamlit as st
import json
import os
import re
from difflib import get_close_matches


# --- CSS стили ---
# --- CSS с поддержкой темного режима ---
def local_css():
    st.markdown("""
    <style>
    :root {
        --bg-light: #f5f7f9;
        --bg-dark: #1e1e1e;
        --card-light: #ffffff;
        --card-dark: #2b2b2b;
        --marker-bg-light: #f0f4f8;
        --marker-bg-dark: #3a3a3a;
        --marker-border-light: #d1d9e6;
        --marker-border-dark: #555555;
        --info-bg-light: #e8f4fd;
        --info-bg-dark: #254d6f;
        --info-border-light: #b6d4fe;
        --info-border-dark: #1b3550;
    }

    .main { background-color: var(--bg-light); }
    .markers-container { 
        background-color: var(--card-light);
        border: 1px solid #e0e0e0;
    }
    .marker-item {
        background-color: var(--marker-bg-light);
        padding: 8px 12px;
        border-radius: 20px;
        margin: 4px;
        display: inline-flex;
        align-items: center;
        border: 1px solid var(--marker-border-light);
    }
    .marker-item.default-marker {
        background-color: #e8f5e8 !important;
        border-color: #28a745 !important;
    }
    .marker-item:hover { background-color: #e3e8f0; }
    .marker-delete-btn {
        background: none;
        border: none;
        color: #dc3545;
        cursor: pointer;
        margin-left: 8px;
        font-size: 14px;
        padding: 0;
        height: 20px;
        width: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
    }
    .marker-delete-btn:hover { background-color: #dc3545; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- Новый способ управления маркерами (чекбоксы вместо удаления) ---
def render_marker_selection():
    st.markdown("### 📝 Текущие маркеры (выберите активные)")
    updated_markers = []
    default_markers_lower = [m.lower() for m in get_default_markers()]

    for marker in st.session_state.phase2_markers:
        is_default = marker.lower() in default_markers_lower
        label = f"{marker} {'🔧' if is_default else ''}"
        checked = st.checkbox(label, value=True, key=f"marker_{marker}")
        if checked:
            updated_markers.append(marker)

    st.session_state.phase2_markers = updated_markers





# --- Функции для работы с маркерами ---
def load_markers(markers_file="markers.json"):
    """Загружает маркеры из файла"""
    try:
        if os.path.exists(markers_file):
            with open(markers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Создаем файл с примером, если он не существует
            example_markers = {
                "Абразивные материалы": ["абразивные материалы", "шлифовальные материалы"],
                "Адаптер котла": ["адаптер котла", "адаптер для котла"],
                "Алюмель": ["алюмель"]
            }
            save_markers(example_markers, markers_file)
            return example_markers
    except Exception as e:
        st.error(f"Ошибка загрузки маркеров: {e}")
        return {}


def save_markers(markers_data, markers_file="markers.json"):
    """Сохраняет маркеры в файл"""
    try:
        with open(markers_file, 'w', encoding='utf-8') as f:
            json.dump(markers_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения маркеров: {e}")
        return False


def normalize_category_name(name):
    """Нормализует название категории для поиска"""
    if not name:
        return ""

    # Приводим к нижнему регистру, убираем лишние пробелы
    normalized = name.lower().strip()

    # Удаляем специальные символы
    normalized = re.sub(r'[^\w\s-]', '', normalized)

    # Сортируем слова в алфавитном порядке (для учета перестановки слов)
    words = sorted(normalized.split())

    return ' '.join(words)


def find_category_matches(category_name, markers_data):
    """Находит совпадения категории в маркерах"""
    if not category_name or not markers_data:
        return []

    normalized_input = normalize_category_name(category_name)

    matches = []

    for stored_category, markers in markers_data.items():
        normalized_stored = normalize_category_name(stored_category)

        # Проверяем точное совпадение после нормализации
        if normalized_input == normalized_stored:
            matches.append({
                'category': stored_category,
                'match_type': 'exact',
                'markers': markers,
                'score': 100
            })
        # Проверяем частичное совпадение
        elif normalized_input in normalized_stored or normalized_stored in normalized_input:
            set_input = set(normalized_input.split())
            set_stored = set(normalized_stored.split())
            if set_input and set_stored:  # защита от деления на ноль
                match_score = len(set_input & set_stored) / len(set_input | set_stored) * 100
            else:
                match_score = 0
            matches.append({
                'category': stored_category,
                'match_type': 'partial',
                'markers': markers,
                'score': match_score
            })

    # Используем fuzzy matching для похожих названий
    if not matches:
        category_names = list(markers_data.keys())
        fuzzy_matches = get_close_matches(category_name, category_names, n=3, cutoff=0.6)

        for match in fuzzy_matches:
            matches.append({
                'category': match,
                'match_type': 'fuzzy',
                'markers': markers_data[match],
                'score': 70
            })

    # Сортируем по score
    matches.sort(key=lambda x: x['score'], reverse=True)

    return matches


def get_default_markers():
    """Возвращает маркеры по умолчанию (видимые и изменяемые)"""
    # Получаем из session_state, если есть изменения
    if 'default_markers' in st.session_state:
        return st.session_state.default_markers.copy()
    else:
        return ["продукция", "изделие", "товар"]


def add_marker_to_list(markers_list, new_marker):
    """Добавляет маркер в список, если его там нет"""
    if not new_marker:
        return markers_list

    new_marker_lower = new_marker.lower().strip()

    # Проверяем, нет ли уже такого маркера
    for marker in markers_list:
        if marker.lower() == new_marker_lower:
            return markers_list

    return markers_list + [new_marker]


def remove_marker_from_list(markers_list, marker_to_remove):
    """Удаляет маркер из списка"""
    return [m for m in markers_list if m != marker_to_remove]


def save_to_session_state():
    """Сохраняет данные в session_state для передачи в фазу 3"""
    if 'phase2_data' not in st.session_state:
        st.session_state.phase2_data = {}

    st.session_state.phase2_data = {
        'category': st.session_state.get('selected_category', ''),
        'markers': st.session_state.get('phase2_markers', []).copy(),
        'source_data': st.session_state.get('loaded_data', {}),
        'markers_updated': True
    }

    # Также сохраняем в общие данные приложения
    if 'app_data' in st.session_state:
        st.session_state.app_data['phase2'] = {
            'category': st.session_state.get('selected_category', ''),
            'markers': st.session_state.get('phase2_markers', []).copy()
        }


# --- Основное приложение ---
def main():
    st.set_page_config(page_title="Data Harvester Phase 2", layout="wide")
    local_css()
    st.title("🏷️ Фаза 2: Управление маркерами категорий")

    # --- Инициализация состояния ---
    if 'phase2_markers' not in st.session_state:
        st.session_state.phase2_markers = []
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = ""
    if 'custom_category_mode' not in st.session_state:
        st.session_state.custom_category_mode = False
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    if 'new_marker_input' not in st.session_state:
        st.session_state.new_marker_input = ""
    if 'loaded_data' not in st.session_state:
        st.session_state.loaded_data = None
    if 'markers_data' not in st.session_state:
        st.session_state.markers_data = load_markers()
    if 'default_markers' not in st.session_state:
        st.session_state.default_markers = get_default_markers()
    if 'show_default_markers_editor' not in st.session_state:
        st.session_state.show_default_markers_editor = False

    # --- Автоматическая загрузка данных из фазы 1 ---
    # Проверяем, есть ли данные из фазы 1 в session_state
    if 'phase1_data' in st.session_state and st.session_state.phase1_data:
        st.session_state.loaded_data = st.session_state.phase1_data
        category_from_phase1 = st.session_state.phase1_data.get('category', '')

        if category_from_phase1 and not st.session_state.selected_category:
            st.session_state.search_query = category_from_phase1

    # Также проверяем общие данные приложения
    elif 'app_data' in st.session_state and 'phase1' in st.session_state.app_data:
        st.session_state.loaded_data = st.session_state.app_data['phase1']
        category_from_phase1 = st.session_state.app_data['phase1'].get('category', '')

        if category_from_phase1 and not st.session_state.selected_category:
            st.session_state.search_query = category_from_phase1

    # --- Боковая панель ---
    with st.sidebar:
        st.header("⚙️ Настройки")

        # Редактирование маркеров по умолчанию
        with st.expander("🔧 Маркеры по умолчанию", expanded=False):
            if st.button("✏️ Редактировать маркеры по умолчанию"):
                st.session_state.show_default_markers_editor = not st.session_state.show_default_markers_editor

            if st.session_state.show_default_markers_editor:
                default_markers_text = st.text_area(
                    "Маркеры по умолчанию (каждый с новой строки):",
                    value="\n".join(st.session_state.default_markers),
                    height=150
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Сохранить", use_container_width=True):
                        new_default_markers = [m.strip() for m in default_markers_text.split('\n') if m.strip()]
                        st.session_state.default_markers = new_default_markers
                        st.success("Маркеры по умолчанию обновлены!")
                        st.rerun()

                with col2:
                    if st.button("🔄 Сбросить", use_container_width=True):
                        st.session_state.default_markers = ["продукция", "изделие", "товар"]
                        st.rerun()

        st.divider()

        # Информация о загруженных данных
        st.header("📊 Информация")

        if st.session_state.loaded_data:
            category = st.session_state.loaded_data.get('category', 'Не указана')
            characteristics_count = len(st.session_state.loaded_data.get('characteristics', []))

            st.success(f"✅ Данные из фазы 1 загружены")
            st.write(f"**Категория:** {category}")
            st.write(f"**Характеристик:** {characteristics_count}")
        else:
            st.warning("Данные из фазы 1 не загружены")
            st.info("Запустите фазу 1 для автоматической передачи данных")

        st.divider()

        # Быстрые действия
        st.header("⚡ Быстрые действия")

        if st.button("🔄 Сбросить выбор категории", use_container_width=True):
            st.session_state.selected_category = ""
            st.session_state.phase2_markers = []
            st.session_state.custom_category_mode = False
            st.rerun()

        if st.button("📋 Загрузить маркеры по умолчанию", use_container_width=True):
            default_markers = get_default_markers()
            for marker in default_markers:
                st.session_state.phase2_markers = add_marker_to_list(st.session_state.phase2_markers, marker)
            st.rerun()

    # --- Основной контент ---
    # Если есть данные из фазы 1, используем их для поиска
    if st.session_state.loaded_data and 'category' in st.session_state.loaded_data:
        category_from_data = st.session_state.loaded_data['category']

        if not st.session_state.selected_category and category_from_data:
            st.session_state.search_query = category_from_data

    # Если есть поисковый запрос, ищем совпадения
    if st.session_state.search_query:
        st.subheader(f"🔍 Поиск маркеров для категории: **{st.session_state.search_query}**")

        matches = find_category_matches(st.session_state.search_query, st.session_state.markers_data)

        if matches:
            # Показываем найденные совпадения
            with st.expander(f"Найдено {len(matches)} совпадение(ий)", expanded=True):
                for i, match in enumerate(matches):
                    match_class = {
                        'exact': 'exact-match',
                        'partial': 'close-match',
                        'fuzzy': 'close-match'
                    }.get(match['match_type'], 'no-match')

                    match_icon = {
                        'exact': '✅',
                        'partial': '🔍',
                        'fuzzy': '🔍'
                    }.get(match['match_type'], '❓')

                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.markdown(f"**{match_icon}**")
                    with col2:
                        st.markdown(f"**{match['category']}**")
                        st.caption(f"Маркеров: {len(match['markers'])}")
                    with col3:
                        if st.button("Выбрать", key=f"select_{i}"):
                            st.session_state.selected_category = match['category']
                            st.session_state.phase2_markers = match['markers'].copy()
                            st.rerun()

                    if match['markers']:
                        sample_markers = match['markers'][:3]
                        st.markdown(f"*Примеры:* {', '.join(sample_markers)}")

                    st.divider()

            # Опция для создания новой категории
            st.markdown("<div class='info-box'>", unsafe_allow_html=True)
            st.write("**Не нашли подходящую категорию?**")

            col_new1, col_new2 = st.columns([3, 1])
            with col_new1:
                new_category_name = st.text_input(
                    "Создать новую категорию:",
                    value=st.session_state.search_query,
                    key="new_category_input"
                )
            with col_new2:
                if st.button("Создать", use_container_width=True):
                    if new_category_name:
                        st.session_state.selected_category = new_category_name
                        st.session_state.phase2_markers = get_default_markers().copy()
                        st.session_state.custom_category_mode = True
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            # Не найдено совпадений
            st.warning("Совпадений не найдено. Создайте новую категорию.")

            col_new1, col_new2 = st.columns([3, 1])
            with col_new1:
                new_category_name = st.text_input(
                    "Название новой категории:",
                    value=st.session_state.search_query,
                    key="new_category_input_empty"
                )
            with col_new2:
                if st.button("Создать", use_container_width=True, key="create_empty"):
                    if new_category_name:
                        st.session_state.selected_category = new_category_name
                        st.session_state.phase2_markers = get_default_markers().copy()
                        st.session_state.custom_category_mode = True
                        st.rerun()

    # Редактирование маркеров для выбранной категории
    if st.session_state.selected_category:
        st.markdown("<div class='markers-container'>", unsafe_allow_html=True)
        st.subheader(f"✏️ Редактирование маркеров: **{st.session_state.selected_category}**")

        render_marker_selection()

        # Информация о категории
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.info(f"Текущая категория: **{st.session_state.selected_category}**")
        with col_info2:
            if st.session_state.custom_category_mode:
                st.warning("⚠️ Новая категория")
            else:
                st.success("✅ Категория найдена в базе")


        # Показываем пользовательские маркеры


        # Добавление нового маркера
        st.markdown("### ➕ Добавить новый маркер")

        col_add1, col_add2 = st.columns([3, 1])
        with col_add1:
            new_marker = st.text_input(
                "Введите новый маркер:",
                placeholder="Например: товар, продукт, изделие...",
                key="new_marker_input_main"
            )
        with col_add2:
            if st.button("Добавить", use_container_width=True):
                if new_marker:
                    st.session_state.phase2_markers = add_marker_to_list(st.session_state.phase2_markers, new_marker)
                    st.rerun()

        # Быстрые действия с маркерами
        st.markdown("### ⚡ Быстрые действия")

        col_quick1, col_quick2 = st.columns(2)

        with col_quick1:
            if st.button("🗑️ Удалить все пользовательские маркеры", use_container_width=True):
                # Сохраняем только стандартные маркеры
                default_markers_lower = [m.lower() for m in get_default_markers()]
                st.session_state.phase2_markers = [
                    m for m in st.session_state.phase2_markers
                    if m.lower() in default_markers_lower
                ]
                st.rerun()

        with col_quick2:
            if st.button("📋 Копировать из другой категории", use_container_width=True):
                all_categories = list(st.session_state.markers_data.keys())
                if all_categories:
                    selected_copy = st.selectbox(
                        "Выберите категорию для копирования маркеров:",
                        all_categories,
                        key="copy_category_select"
                    )
                    if selected_copy:
                        st.session_state.phase2_markers = st.session_state.markers_data[selected_copy].copy()
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # Кнопки сохранения
        st.divider()
        st.markdown("### 💾 Сохранение")

        col_save1, col_save2 = st.columns(2)

        with col_save1:
            if st.button("💾 Сохранить маркеры", type="primary", use_container_width=True):
                if st.session_state.selected_category and st.session_state.phase2_markers:
                    # Обновляем данные маркеров
                    st.session_state.markers_data[st.session_state.selected_category] = st.session_state.phase2_markers

                    # Сохраняем в файл
                    if save_markers(st.session_state.markers_data):
                        st.success(f"✅ Маркеры для категории '{st.session_state.selected_category}' сохранены!")

                        # Автоматически сохраняем в session_state для передачи в фазу 3
                        save_to_session_state()
                    else:
                        st.error("❌ Ошибка сохранения маркеров")

        with col_save2:
            # Кнопка для перехода к фазе 3 (если в main_app)
            if st.button("🚀 Перейти к фазе 3", use_container_width=True):
                # Сохраняем данные перед переходом
                save_to_session_state()

                # В реальном приложении здесь будет переход к фазе 3
                # В standalone версии показываем сообщение
                st.success("✅ Данные сохранены и готовы для передачи в фазу 3!")

        # Предпросмотр сохраненных данных
        with st.expander("👁️ Предпросмотр данных для передачи в фазу 3"):
            phase3_data = {
                "category": st.session_state.selected_category,
                "markers": st.session_state.phase2_markers,
                "characteristics": st.session_state.loaded_data.get('characteristics',
                                                                    []) if st.session_state.loaded_data else [],
                "source_data": {
                    "category": st.session_state.loaded_data.get('category',
                                                                 '') if st.session_state.loaded_data else '',
                    "characteristics_count": len(
                        st.session_state.loaded_data.get('characteristics', [])) if st.session_state.loaded_data else 0
                }
            }
            st.json(phase3_data)

    else:
        # Если категория не выбрана и нет данных из фазы 1
        if not st.session_state.loaded_data:
            st.info("""
            ## 👋 Добро пожаловать в фазу 2!

            Чтобы начать работу:

            1. **Запустите фазу 1** и обработайте данные
            2. **Категория автоматически передастся** в фазу 2
            3. **Найдите или создайте** категорию для работы с маркерами

            Или вручную введите название категории для поиска:
            """)

            manual_search = st.text_input(
                "Введите название категории для поиска:",
                placeholder="Например: Абразивные материалы",
                key="manual_search_input"
            )

            if manual_search:
                st.session_state.search_query = manual_search
                st.rerun()
        else:
            # Данные есть, но категория не выбрана
            st.info("Введите название категории в поле поиска выше или используйте категорию из фазы 1")


if __name__ == "__main__":
    main()