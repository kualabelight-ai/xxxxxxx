import streamlit as st
import json
import os
import re
from difflib import get_close_matches


# --- CSS стили ---
def local_css():
    st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .markers-table-container {
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px;
        background-color: white;
        margin-bottom: 20px;
    }
    .marker-row {
        display: flex;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .marker-row:last-child {
        border-bottom: none;
    }
    .marker-name {
        flex: 1;
        padding-left: 10px;
    }
    .marker-type-badge {
        font-size: 0.7em;
        padding: 2px 6px;
        border-radius: 3px;
        margin-left: 8px;
        background-color: #e8f4fd;
        color: #0066cc;
    }
    .category-match {
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        cursor: pointer;
    }
    .category-match:hover {
        background-color: #e8f4fd;
    }
    .exact-match {
        border-left: 4px solid #28a745;
    }
    .close-match {
        border-left: 4px solid #ffc107;
    }
    .no-match {
        border-left: 4px solid #dc3545;
    }
    .markers-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 20px;
    }
    .info-box {
        background-color: #e8f4fd;
        border: 1px solid #b6d4fe;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .section-header {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 15px 0 10px 0;
        font-weight: bold;
        color: #495057;
    }
    </style>
    """, unsafe_allow_html=True)


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

    normalized = name.lower().strip()
    normalized = re.sub(r'[^\w\s-]', '', normalized)
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

        if normalized_input == normalized_stored:
            matches.append({
                'category': stored_category,
                'match_type': 'exact',
                'markers': markers,
                'score': 100
            })
        elif normalized_input in normalized_stored or normalized_stored in normalized_input:
            set_input = set(normalized_input.split())
            set_stored = set(normalized_stored.split())
            if set_input and set_stored:
                match_score = len(set_input & set_stored) / len(set_input | set_stored) * 100
            else:
                match_score = 0
            matches.append({
                'category': stored_category,
                'match_type': 'partial',
                'markers': markers,
                'score': match_score
            })

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

    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches


def get_default_markers():
    """Возвращает маркеры по умолчанию"""
    if 'default_markers' in st.session_state:
        return st.session_state.default_markers.copy()
    else:
        return ["продукция", "изделие", "товар"]


def add_marker_to_list(markers_list, new_marker):
    """Добавляет маркер в список, если его там нет"""
    if not new_marker:
        return markers_list

    new_marker_lower = new_marker.lower().strip()
    for marker in markers_list:
        if marker.lower() == new_marker_lower:
            return markers_list

    return markers_list + [new_marker]


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

    if 'app_data' in st.session_state:
        st.session_state.app_data['phase2'] = {
            'category': st.session_state.get('selected_category', ''),
            'markers': st.session_state.get('phase2_markers', []).copy()
        }


# --- Callback функции ---
def toggle_marker(marker):
    """Обработчик переключения маркера (упрощенный)"""
    if marker in st.session_state.phase2_markers:
        st.session_state.phase2_markers.remove(marker)
    else:
        st.session_state.phase2_markers.append(marker)


def delete_all_custom_markers():
    """Удаляет все пользовательские маркеры из текущего списка"""
    default_markers_lower = [m.lower() for m in get_default_markers()]
    st.session_state.phase2_markers = [
        m for m in st.session_state.phase2_markers
        if m.lower() in default_markers_lower
    ]


def load_default_markers_to_list():
    """Добавляет маркеры по умолчанию в текущий список"""
    default_markers = get_default_markers()
    for marker in default_markers:
        if marker not in st.session_state.phase2_markers:
            st.session_state.phase2_markers.append(marker)


def select_all_markers():
    """Выбрать все маркеры"""
    # Получаем все возможные маркеры для этой категории
    all_possible_markers = []
    if st.session_state.selected_category in st.session_state.markers_data:
        all_possible_markers = st.session_state.markers_data[st.session_state.selected_category].copy()

    # Добавляем маркеры по умолчанию
    default_markers = get_default_markers()
    for marker in default_markers:
        if marker not in all_possible_markers:
            all_possible_markers.append(marker)

    # Добавляем текущие маркеры (новые, которые еще не сохранены)
    for marker in st.session_state.phase2_markers:
        if marker not in all_possible_markers:
            all_possible_markers.append(marker)

    # Устанавливаем все маркеры
    st.session_state.phase2_markers = all_possible_markers.copy()


def deselect_all_markers():
    """Сбросить выбор всех маркеров"""
    st.session_state.phase2_markers = []

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
    if 'phase1_data' in st.session_state and st.session_state.phase1_data:
        st.session_state.loaded_data = st.session_state.phase1_data
        category_from_phase1 = st.session_state.phase1_data.get('category', '')

        if category_from_phase1 and not st.session_state.selected_category:
            st.session_state.search_query = category_from_phase1
    elif 'app_data' in st.session_state and 'phase1' in st.session_state.app_data:
        st.session_state.loaded_data = st.session_state.app_data['phase1']
        category_from_phase1 = st.session_state.app_data['phase1'].get('category', '')

        if category_from_phase1 and not st.session_state.selected_category:
            st.session_state.search_query = category_from_phase1

    # --- Боковая панель ---
    with st.sidebar:
        st.header("⚙️ Настройки")

        with st.expander("🔧 Маркеры по умолчанию", expanded=False):
            if st.button("✏️ Редактировать"):
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
        '''st.header("⚡ Быстрые действия")

        if st.button("🔄 Сбросить выбор категории", use_container_width=True):
            st.session_state.selected_category = ""
            st.session_state.phase2_markers = []
            st.session_state.custom_category_mode = False
            st.rerun()

        if st.button("📋 Загрузить маркеры по умолчанию", use_container_width=True,
                     on_click=load_default_markers_to_list):
            st.rerun()'''

    # --- Основной контент ---
    if st.session_state.loaded_data and 'category' in st.session_state.loaded_data:
        category_from_data = st.session_state.loaded_data['category']
        if not st.session_state.selected_category and category_from_data:
            st.session_state.search_query = category_from_data

    if st.session_state.search_query:
        st.subheader(f"🔍 Поиск маркеров для категории: **{st.session_state.search_query}**")

        matches = find_category_matches(st.session_state.search_query, st.session_state.markers_data)

        if matches:
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

    if st.session_state.selected_category:
        st.markdown("<div class='markers-container'>", unsafe_allow_html=True)
        st.subheader(f"✏️ Редактирование маркеров: **{st.session_state.selected_category}**")

        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.info(f"Текущая категория: **{st.session_state.selected_category}**")
        with col_info2:
            if st.session_state.custom_category_mode:
                st.warning("⚠️ Новая категория")
            else:
                st.success("✅ Категория найдена в базе")

        st.markdown("### 📝 Управление маркерами")

        col_quick1, col_quick2 = st.columns(2)

        with col_quick1:
            if st.button("✅ Выбрать все", use_container_width=True,
                         on_click=select_all_markers):
                st.rerun()

        with col_quick2:
            if st.button("❌ Сбросить все", use_container_width=True,
                         on_click=deselect_all_markers):
                st.rerun()
        # Получаем все возможные маркеры для этой категории
        all_possible_markers = []
        if st.session_state.selected_category in st.session_state.markers_data:
            all_possible_markers = st.session_state.markers_data[st.session_state.selected_category].copy()

        # Добавляем текущие маркеры, которых нет в all_possible_markers
        for marker in st.session_state.phase2_markers:
            if marker not in all_possible_markers:
                all_possible_markers.append(marker)

        # Добавляем маркеры по умолчанию
        default_markers = get_default_markers()
        for marker in default_markers:
            if marker not in all_possible_markers:
                all_possible_markers.append(marker)

        # Разделяем на маркеры по умолчанию и пользовательские
        default_markers_lower = [m.lower() for m in default_markers]
        default_markers_list = []
        custom_markers_list = []

        for marker in sorted(all_possible_markers):
            if marker.lower() in default_markers_lower:
                default_markers_list.append(marker)
            else:
                custom_markers_list.append(marker)

        # Отображаем таблицу маркеров
        st.markdown("<div class='markers-table-container'>", unsafe_allow_html=True)

        # В разделе отображения маркеров замените:
        if default_markers_list:
            st.markdown("<div class='section-header'>Маркеры по умолчанию</div>", unsafe_allow_html=True)
            for marker in default_markers_list:
                col1, col2 = st.columns([1, 20])
                with col1:
                    is_checked = marker in st.session_state.phase2_markers
                    new_checked = st.checkbox(
                        " ",  # Пробел вместо пустой строки
                        value=is_checked,
                        key=f"checkbox_default_{marker}_{len(st.session_state.phase2_markers)}",
                        label_visibility="collapsed"
                    )

                    # Обновляем состояние при изменении
                    if new_checked != is_checked:
                        if new_checked:
                            st.session_state.phase2_markers.append(marker)
                        else:
                            st.session_state.phase2_markers.remove(marker)
                        st.rerun()

                with col2:
                    st.markdown(
                        f"<div class='marker-name'>{marker} <span class='marker-type-badge'>по умолчанию</span></div>",
                        unsafe_allow_html=True)

        if custom_markers_list:
            st.markdown("<div class='section-header'>Пользовательские маркеры</div>", unsafe_allow_html=True)
            for marker in custom_markers_list:
                col1, col2 = st.columns([1, 20])
                with col1:
                    is_checked = marker in st.session_state.phase2_markers
                    new_checked = st.checkbox(
                        " ",  # Пробел вместо пустой строки
                        value=is_checked,
                        key=f"checkbox_custom_{marker}_{len(st.session_state.phase2_markers)}",
                        label_visibility="collapsed"
                    )

                    # Обновляем состояние при изменении
                    if new_checked != is_checked:
                        if new_checked:
                            st.session_state.phase2_markers.append(marker)
                        else:
                            st.session_state.phase2_markers.remove(marker)
                        st.rerun()

                with col2:
                    st.markdown(f"<div class='marker-name'>{marker}</div>", unsafe_allow_html=True)

        if not default_markers_list and not custom_markers_list:
            st.info("Нет доступных маркеров. Добавьте новые маркеры.")

        st.markdown("</div>", unsafe_allow_html=True)

        # Статистика
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Всего маркеров", len(all_possible_markers))
        with col_stat2:
            st.metric("Выбрано", len(st.session_state.phase2_markers))
        with col_stat3:
            st.metric("По умолчанию", len(default_markers_list))

        st.divider()

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
                    # Также добавляем в all_possible_markers для отображения
                    if new_marker not in all_possible_markers:
                        all_possible_markers.append(new_marker)
                    st.rerun()

        # Быстрые действия с маркерами
        #st.markdown("### ⚡ Быстрые действия")
        #col_quick1, col_quick2, col_quick3, col_quick4 = st.columns(4)

        #with col_quick1:
            #if st.button("🗑️ Удалить все пользовательские маркеры", use_container_width=True,
                         #on_click=delete_all_custom_markers):
                #st.rerun()

        #with col_quick2:
            #if st.button("📋 Включить все маркеры по умолчанию", use_container_width=True,
                         #on_click=load_default_markers_to_list):
                #st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # Кнопки сохранения
        st.divider()
        st.markdown("### 💾 Сохранение")

        col_save1, col_save2 = st.columns(2)

        with col_save1:
            if st.button("💾 Сохранить маркеры", type="primary", use_container_width=True):
                if st.session_state.selected_category and st.session_state.phase2_markers:
                    # Берём существующие маркеры для этой категории (если есть)
                    existing = st.session_state.markers_data.get(st.session_state.selected_category, [])
                    # Объединяем с текущими выбранными, убираем дубликаты
                    updated = list(set(existing + st.session_state.phase2_markers))
                    st.session_state.markers_data[st.session_state.selected_category] = updated

                    if save_markers(st.session_state.markers_data):
                        st.success(f"✅ Маркеры для категории '{st.session_state.selected_category}' сохранены!")
                        save_to_session_state()
                    else:
                        st.error("❌ Ошибка сохранения маркеров")

        with col_save2:
            if st.button("🚀 Перейти к фазе 3", use_container_width=True):
                save_to_session_state()
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
            st.info("Введите название категории в поле поиска выше или используйте категорию из фазы 1")


if __name__ == "__main__":
    main()