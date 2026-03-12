import streamlit as st
import json
import os
from collections import defaultdict
from datetime import datetime
from styles import load_css

# --- CSS ---
# --- CSS ---
def local_css():
    st.markdown("""
    <style>
    /* Основные стили */
    .main { 
        background-color: #f5f7f9; 
    }

    /* Темный режим */
    @media (prefers-color-scheme: dark) {
        .main {
            background-color: #0e1117;
        }
        .characteristic-container {
            background-color: #262730;
            border-color: #41434d;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }
        .characteristic-container:hover {
            border-color: #4a4d57;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }
        .metric-box {
            background-color: #262730;
            color: #f0f2f6;
            border-color: #41434d;
        }
        .warning-box {
            background-color: #332701;
            border-color: #665c00;
            color: #ffd54f;
        }
        .stButton > button {
            background-color: #4a4d57;
            color: #f0f2f6;
            border: 1px solid #5a5d68;
        }
        .stButton > button:hover {
            background-color: #5a5d68;
            border-color: #6a6d78;
        }
        .char-header {
            color: #e2e8f0;
        }
        .char-info {
            color: #94a3b8;
        }
        .fill-rate {
            color: #34d399;
        }
    }

    .stTable { 
        font-size: 12px; 
    }

    .metric-box {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        margin-bottom: 15px;
        border: 1px solid #eaeaea;
    }

    .preview-btn {
        background-color: #e0f7fa;
        color: #00796b;
        border: none;
        border-radius: 5px;
        padding: 2px 8px;
        cursor: pointer;
    }

    .characteristic-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 16px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }

    .characteristic-container:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-color: #d0d0d0;
        transform: translateY(-1px);
    }

    /* Разделитель между карточками */
    .characteristic-container::after {
        content: '';
        display: block;
        height: 1px;
        background: linear-gradient(90deg, 
            transparent 0%, 
            rgba(0,0,0,0.1) 20%, 
            rgba(0,0,0,0.1) 80%, 
            transparent 100%);
        margin-top: 16px;
        margin-bottom: 0;
    }

    .characteristic-container:last-child::after {
        display: none;
    }

    /* Альтернативный вариант - разделитель между колонками */
    .stColumn {
        position: relative;
    }

    .stColumn:not(:last-child)::after {
        content: '';
        position: absolute;
        top: 10%;
        right: 0;
        height: 80%;
        width: 1px;
        background: linear-gradient(to bottom, 
            transparent 0%, 
            rgba(0,0,0,0.1) 20%, 
            rgba(0,0,0,0.1) 80%, 
            transparent 100%);
    }

    .mode-buttons {
        display: flex;
        gap: 5px;
    }

    .global-sync-btn {
        margin-top: 10px;
    }

    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 20px;
        color: #856404;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Улучшенные стили для чекбоксов и радио */
    .stCheckbox > label,
    .stRadio > label {
        font-weight: 500 !important;
    }

    /* Стили для заголовков */
    .char-header {
        font-weight: 600;
        margin-bottom: 8px;
        color: #1e293b;
    }

    /* Стили для информации о характеристике */
    .char-info {
        color: #64748b;
        font-size: 0.85em;
        margin-top: 4px;
    }

    /* Дубликаты - особый стиль */
    .duplicate-char {
        border-left: 4px solid #ef4444;
        background: linear-gradient(90deg, rgba(239,68,68,0.05) 0%, transparent 100%);
    }

    /* Дополнительные характеристики */
    .extra-char {
        border-left: 4px solid #f59e0b;
        background: linear-gradient(90deg, rgba(245,158,11,0.05) 0%, transparent 100%);
    }

    /* Нормальные характеристики */
    .normal-char {
        border-left: 4px solid #10b981;
        background: linear-gradient(90deg, rgba(16,185,129,0.05) 0%, transparent 100%);
    }

    /* Темный режим для типов характеристик */
    @media (prefers-color-scheme: dark) {
        .duplicate-char {
            border-left: 4px solid #ef4444;
            background: linear-gradient(90deg, rgba(239,68,68,0.15) 0%, transparent 100%);
        }
        .extra-char {
            border-left: 4px solid #f59e0b;
            background: linear-gradient(90deg, rgba(245,158,11,0.15) 0%, transparent 100%);
        }
        .normal-char {
            border-left: 4px solid #10b981;
            background: linear-gradient(90deg, rgba(16,185,129,0.15) 0%, transparent 100%);
        }
    }

    /* Улучшение отступов в колонках */
    .stColumn > div {
        padding: 0 8px;
    }

    /* Улучшение видимости процентов заполнения */
    .fill-rate {
        font-weight: 600;
        color: #10b981;
        font-size: 1.1em;
    }

    /* Иконка дубликата */
    .duplicate-icon {
        color: #ef4444;
        margin-right: 6px;
        display: inline-block;
    }

    /* Улучшение для кнопок в карточках */
    .characteristic-container .stButton > button {
        font-size: 0.85em;
        padding: 4px 12px;
        border-radius: 6px;
    }

    /* Улучшение для селекторов и инпутов */
    .characteristic-container .stSelectbox > div,
    .characteristic-container .stNumberInput > div {
        border-radius: 6px;
        border: 1px solid #d1d5db;
    }

    .characteristic-container .stSelectbox > div:hover,
    .characteristic-container .stNumberInput > div:hover {
        border-color: #9ca3af;
    }

    /* Темный режим для инпутов */
    @media (prefers-color-scheme: dark) {
        .characteristic-container .stSelectbox > div,
        .characteristic-container .stNumberInput > div {
            border-color: #4b5563;
            background-color: #374151;
        }
        .characteristic-container .stSelectbox > div:hover,
        .characteristic-container .stNumberInput > div:hover {
            border-color: #6b7280;
        }
    }

    /* Стили для состояния активности */
    .active-char {
        opacity: 1;
    }

    .inactive-char {
        opacity: 0.7;
        background-color: #f8f9fa;
    }

    @media (prefers-color-scheme: dark) {
        .inactive-char {
            background-color: #1f2937;
        }
    }

    /* Улучшение для заголовков разделов */
    h1, h2, h3 {
        margin-top: 0 !important;
        padding-top: 0.5em !important;
    }

    /* Градиентные заголовки */
    h1 {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* Анимация при наведении на заголовки */
    h2:hover, h3:hover {
        transition: all 0.3s ease;
        transform: translateX(5px);
    }

    /* Стили для expander */
    .streamlit-expanderHeader {
        font-weight: 500 !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
    }

    .streamlit-expanderContent {
        padding: 12px !important;
    }

    /* Стили для таблиц в предпросмотре */
    .dataframe {
        border-radius: 8px !important;
        overflow: hidden !important;
        border: 1px solid #e5e7eb !important;
    }

    @media (prefers-color-scheme: dark) {
        .dataframe {
            border-color: #4b5563 !important;
        }
    }

    /* Плавные переходы */
    * {
        transition: background-color 0.3s ease, 
                    border-color 0.3s ease, 
                    box-shadow 0.3s ease,
                    transform 0.3s ease;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Логика обработки ---
def normalize_string(s):
    """Нормализует строку: убирает лишние пробелы"""
    if not isinstance(s, str):
        return s
    # Заменяем множественные пробелы на один, убираем в начале и конце
    return ' '.join(s.split())  # Это преобразует "Труба  горячедеформированная" в "Труба горячедеформированная"


def normalize_data(data):
    """
    Нормализует данные: убирает лишние пробелы в названиях категорий и характеристик.
    """
    if not isinstance(data, dict):
        return data

    # Нормализуем название категории
    if "ПараметрыТовара" in data and isinstance(data["ПараметрыТовара"], dict):
        params = data["ПараметрыТовара"]
        if "Наименование" in params and isinstance(params["Наименование"], str):
            params["Наименование"] = normalize_string(params["Наименование"])
            #print(f"Нормализовано название категории: {params['Наименование']}")  # Для отладки

        # Нормализуем названия характеристик
        if "Характеристики" in params and isinstance(params["Характеристики"], list):
            for char in params["Характеристики"]:
                if "Наименование" in char and isinstance(char["Наименование"], str):
                    char["Наименование"] = normalize_string(char["Наименование"])

    return data


# Затем в функции load_data:
def load_data(uploaded_file):
    try:
        data = json.load(uploaded_file)
        # Нормализуем данные сразу после загрузки
        return normalize_data(data)
    except Exception as e:
        st.error(f"Ошибка чтения JSON: {e}")
        return None


def is_empty_value(val):
    """Проверяем, является ли значение по-настоящему пустым"""
    if val is None:
        return True

    if isinstance(val, (int, float)):
        return False

    val_str = str(val).strip()
    if not val_str:
        return True

    empty_patterns = [
        "", "null", "none", "nan", "undefined",
        "нет", "не указано", "не задано", "не определено",
        "-", "–", "—", "―", "−",
        "n/a", "na", "n.a.", "n.a", "n\\a",
        "пусто", "отсутствует", "не заполнено"
    ]

    val_lower = val_str.lower()
    if val_lower in empty_patterns:
        return True

    special_empty = ["\u200b", "\u00a0", "\u3000", "\u200e", "\u200f", "\u202a", "\u202c"]
    if val_str in special_empty:
        return True

    import re
    if re.fullmatch(r'[\s\-_\.]+', val_str):
        return True

    return False


def format_top_goods(raw_data, top_n):
    """
    Формирует текст с топ-N товаров по количеству предложений.
    Включает единицы измерения и общее количество предложений.
    Возвращает строку для копирования.
    """
    items = raw_data.get('Товары', [])
    if not items:
        return "Нет товаров"

    # Создаем маппинг ID характеристики -> {name, unit}
    char_info = {}
    for char in raw_data.get('ПараметрыТовара', {}).get('Характеристики', []):
        char_id = char['ID']
        char_info[char_id] = {
            'name': char.get('Наименование', ''),
            'unit': char.get('ЕдиницаИзмеренияХарактеристики', '')
        }

    offers_keys = ["9000048005", "9000048006", "Всего предложений", "Предложения", "Количество предложений"]

    # Собираем товары с количеством предложений
    goods_with_offers = []
    for item in items:
        chars = item.get('Характеристики', {})
        offers_count = 0
        for key in offers_keys:
            if key in chars:
                try:
                    offers_count = int(chars[key])
                    break
                except (ValueError, TypeError):
                    pass
        goods_with_offers.append((offers_count, item))

    # Сортируем по убыванию предложений
    goods_with_offers.sort(key=lambda x: x[0], reverse=True)
    top_goods = goods_with_offers[:top_n]

    category_name = raw_data.get('ПараметрыТовара', {}).get('Наименование', 'Категория')
    lines = []
    for offers, item in top_goods:
        parts = [category_name]
        chars = item.get('Характеристики', {})
        for char_id, value in chars.items():
            if char_id in offers_keys:
                continue
            if char_id not in char_info:
                continue
            info = char_info[char_id]
            if is_empty_value(value):
                continue
            # Формируем часть "название значение единица"
            part = info['name']
            if value is not None:
                part += f" {value}"
            if info['unit'] and not is_empty_value(info['unit']):
                part += f" {info['unit']}"
            parts.append(part)
        # Добавляем общее количество предложений
        parts.append(f"Предложений: {offers}")
        line = ", ".join(parts)
        lines.append(line)

    return "\n\n".join(lines)
def process_characteristics(data, black_list):
    params_info = data.get("ПараметрыТовара", {}).get("Характеристики", [])
    items = data.get("Товары", [])

    char_map = {}
    name_to_ids = defaultdict(list)

    for char in params_info:
        char_id = char["ID"]
        char_name = char["Наименование"]
        char_map[char_id] = {
            "name": char_name,
            "original_name": char_name,
            "is_extra": bool(char.get("ДополнительнаяХарактеристика", 0)),
            "unit": char.get("ЕдиницаИзмеренияХарактеристики", ""),
            "priority": char.get("ПриоритетВИмени", 0),
            "values": defaultdict(lambda: {"items": set(), "offers": 0}),
            "items_with_char": set(),
        }
        name_to_ids[char_name].append(char_id)

    total_items = len(items)

    for item_idx, item in enumerate(items):
        item_chars = item.get("Характеристики", {})

        offers_count = 0
        offers_keys = ["9000048005", "9000048006", "Всего предложений", "Предложения", "Количество предложений"]
        for key in offers_keys:
            if key in item_chars:
                try:
                    offers_count = int(item_chars[key])
                    break
                except (ValueError, TypeError):
                    offers_count = 0

        for c_id, val in item_chars.items():
            if c_id in offers_keys:
                continue

            if c_id in char_map:
                if is_empty_value(val):
                    continue

                val_str = str(val).strip()
                char_map[c_id]["values"][val_str]["items"].add(item_idx)
                char_map[c_id]["items_with_char"].add(item_idx)
                char_map[c_id]["values"][val_str]["offers"] += offers_count

    result = []
    duplicate_names = {name: ids for name, ids in name_to_ids.items() if len(ids) > 1}

    for c_id, info in char_map.items():
        is_in_black_list = (c_id in black_list) or (info["name"] in black_list) or \
                           any(x in info["name"].lower() for x in ["ед.изм", "едизм", "ед изм"])

        items_with_char_count = len(info["items_with_char"])
        fill_rate = (items_with_char_count / total_items) * 100 if total_items > 0 else 0

        values_data_formatted = {}
        for val, stats in info["values"].items():
            items_count = len(stats["items"])
            values_data_formatted[val] = {
                "count": items_count,
                "offers": stats["offers"]
            }

        is_duplicate = info["name"] in duplicate_names

        result.append({
            "id": c_id,
            "name": info["name"],
            "original_name": info["original_name"],
            "is_extra": info["is_extra"],
            "unit": info["unit"],
            "priority": info["priority"],
            "fill_rate": fill_rate,
            "items_with_char_count": items_with_char_count,
            "total_items": total_items,
            "values_data": values_data_formatted,
            "in_black_list": is_in_black_list,
            "is_duplicate": is_duplicate,
            "duplicate_ids": duplicate_names.get(info["name"], [])
        })

    return result, duplicate_names


# --- Callback-функции ---
def toggle_preview(char_id):
    preview_key = f"preview_{char_id}"
    st.session_state[preview_key] = not st.session_state.get(preview_key, False)


def toggle_json(char_id):
    json_key = f"json_{char_id}"
    st.session_state[json_key] = not st.session_state.get(json_key, False)


def apply_global_settings():
    """Применить глобальные настройки ко всем характеристикам"""
    new_mode = st.session_state.global_mode_selector
    st.session_state.global_mode = new_mode

    # Синхронизируем все индивидуальные режимы
    for key in list(st.session_state.keys()):
        if key.startswith("mode_"):
            st.session_state[key] = new_mode

    # Применяем глобальный Top N ко всем характеристикам в режиме Top N
    for key in list(st.session_state.keys()):
        if key.startswith("topn_"):
            char_id = key.split("_")[1]
            mode_key = f"mode_{char_id}"

            # Обновляем только если характеристика в режиме Top N
            if st.session_state.get(mode_key) == "Top N":
                st.session_state[key] = st.session_state.global_top_n


def update_black_list():
    """Обновить черный список"""
    new_black_list = st.session_state.black_list_textarea
    st.session_state.black_list = [x.strip() for x in new_black_list.split(",") if x.strip()]


def save_edited_name(char_id):
    """Сохранить отредактированное название характеристики"""
    edit_key = f"edit_name_{char_id}"
    if edit_key in st.session_state:
        st.session_state.edited_names[char_id] = st.session_state[edit_key]
        st.session_state[f"json_{char_id}"] = False  # Закрываем JSON панель


def update_global_top_n():
    """Обновить глобальный Top N и применить к характеристикам в режиме Top N"""
    # Обновляем глобальное значение
    st.session_state.global_top_n = st.session_state.global_top_n_input

    # Применяем ко всем характеристикам в режиме Top N
    for key in list(st.session_state.keys()):
        if key.startswith("topn_"):
            char_id = key.split("_")[1]
            mode_key = f"mode_{char_id}"

            # Обновляем только если характеристика в режиме Top N
            if st.session_state.get(mode_key) == "Top N":
                # Проверяем, чтобы новое значение не превышало максимальное
                all_vals_count = st.session_state.get(f"vals_count_{char_id}", 1)
                safe_max_val = max(1, all_vals_count)
                new_value = min(st.session_state.global_top_n, safe_max_val)
                st.session_state[key] = new_value


# --- Приложение ---
def main():
    st.set_page_config(page_title="Data Harvester Phase 1", layout="wide")
    load_css()
    st.title("📦 Сбор и фильтрация характеристик (Фаза 1)")

    # --- Инициализация session_state ---
    defaults = {
        'black_list': ["Цена", "Всего предложений", "Единица измерения", "Комментарий"],
        'global_top_n': 5,
        'global_mode': "Top N",
        'edited_names': {},
        'category_name': "",
        'uploaded_filename': None,
        'processed_chars': None,
        'duplicate_names': None,
        'raw_data': None
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # --- Sidebar ---
    # --- Замена сайдбара: все элементы перенесены в основное окно ---

    # 1. Загрузка файла (не растягиваем — помещаем в центральную колонку)

        # 3. Два блока настроек в две колонки (чтобы не растягивались)
    with st.sidebar:
        st.header("Загрузка данных")
        with st.expander("Гайд"):
            st.markdown("""
                1. Выберите файл json для обработки (Browse files)
                2. Для характеристик, которые не нужно делать переменной - поставить not var
                3. Если у характеристики 0 товаров - 
                3. Установите модель и параметры  
                4. Запустите генерацию  
                """)
        # Загрузка файла в sidebar
        uploaded_file = st.file_uploader(
            "📁 Загрузите JSON файл категории",
            type="json",
            help="Выберите JSON файл с данными о товарах и характеристиках"
        )

        st.markdown("---")  # Разделитель
        st.header("Настройки")

        with st.expander("🚫 Черный список"):
            st.text_area(
                "Список ID или имен (через запятую)",
                value=", ".join(st.session_state.black_list),
                key="black_list_textarea",
                on_change=update_black_list,
                height=150
            )

        st.number_input(
            "🌐 Top N для всех характеристик",
            min_value=1,
            max_value=100,
            value=st.session_state.global_top_n,
            key="global_top_n_input",
            on_change=update_global_top_n,
            help="Будет применён ко всем характеристикам в режиме 'Top N'"
        )


    # 2. Если файл загружен — обрабатываем (логика из sidebar)
    if uploaded_file:
        # Проверяем, нужно ли переобрабатывать (новый файл или первый запуск)
        if (st.session_state.uploaded_filename != uploaded_file.name or
                st.session_state.processed_chars is None):
            raw_data = load_data(uploaded_file)  # Здесь данные УЖЕ нормализованы!
            if raw_data:
                st.session_state.raw_data = raw_data
                st.session_state.processed_chars, st.session_state.duplicate_names = process_characteristics(
                    raw_data, st.session_state.black_list
                )
                st.session_state.uploaded_filename = uploaded_file.name

                # ВАЖНО: Устанавливаем имя категории из НОРМАЛИЗОВАННЫХ данных
                original_category = raw_data.get('ПараметрыТовара', {}).get('Наименование', '')
                if original_category:
                    st.session_state.category_name = original_category
                    #print(f"Установлена категория из данных: {st.session_state.category_name}")  # Для отладки
                else:
                    # Если нет в данных, берем из имени файла и тоже нормализуем
                    filename = uploaded_file.name
                    base_name = os.path.splitext(filename)[0]
                    st.session_state.category_name = normalize_string(base_name)
                    #print(f"Установлена категория из имени файла (нормализовано): {st.session_state.category_name}")



    # 4. Название категории (показываем только если файл загружен)
    '''if uploaded_file:
        st.markdown("---")
        st.markdown("### 🏷️ Название категории для экспорта")
        col_cat1, col_cat2 = st.columns([1, 3])
        with col_cat2:
            # Важно: value должно быть st.session_state.category_name
            category_input = st.text_input(
                "Измените название категории",
                value=st.session_state.category_name,
                key="category_name_input",
                label_visibility="collapsed"
            )
            # Обновляем session_state при изменении
            if category_input != st.session_state.category_name:
                st.session_state.category_name = category_input'''

    # --- Основной интерфейс ---
    if uploaded_file and st.session_state.raw_data:
        raw_data = st.session_state.raw_data
        processed_chars = st.session_state.processed_chars
        duplicate_names = st.session_state.duplicate_names

        # Заголовки
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📁 Файл: {uploaded_file.name}")
            st.info(f"Категория из файла: {raw_data.get('ПараметрыТовара', {}).get('Наименование', 'Неизвестно')}")
        '''with col2:
            st.subheader(f"🏷️ Категория для экспорта")
            st.success(f"**{st.session_state.category_name}**")'''

        # Предупреждения о дубликатах
        if duplicate_names:
            with st.expander("⚠️ Внимание: Обнаружены дублирующиеся названия", expanded=False):
                st.warning("""
                **Обнаружены характеристики с одинаковыми названиями!**
                Это может привести к путанице. Рекомендуется переименовать их.
                """)

                for name, ids in list(duplicate_names.items())[:10]:  # Ограничиваем показ
                    st.error(f"**'{name}'** встречается у ID: {', '.join(ids)}")

                if len(duplicate_names) > 10:
                    st.info(f"... и ещё {len(duplicate_names) - 10} дублирующихся названий")

        # Глобальные настройки
        st.markdown("### Объем данных для всех характеристик")

        col_sync1, col_sync2 = st.columns([3, 1])
        with col_sync1:
            # Сохраняем текущий режим для корректного отображения
            current_mode_idx = ["Все", "Top N", "Вручную"].index(st.session_state.global_mode)
            st.radio(
                "Выберите режим для всех характеристик:",
                ["Все", "Top N", "Вручную"],
                horizontal=True,
                key="global_mode_selector",
                index=current_mode_idx
            )

        with col_sync2:
            if st.button("🔄 Применить ко всем", type="primary", key="apply_global_btn"):
                apply_global_settings()

        # Обработка характеристик
        selected_configs = {}

        for char in processed_chars:
            if char["in_black_list"]:
                continue

            char_id = char["id"]
            all_vals_count = len(char['values_data'])

            # --- Инициализация session_state ---
            st.session_state[f"vals_count_{char_id}"] = all_vals_count
            if f"expanded_{char_id}" not in st.session_state:
                st.session_state[f"expanded_{char_id}"] = False

            display_name = st.session_state.edited_names.get(char_id, char['name'])

            # --- Класс карточки ---
            container_class = ""
            if char['is_duplicate']:
                container_class = "duplicate-char"
            elif char['is_extra']:
                container_class = "extra-char"
            else:
                container_class = "normal-char"
            container_class += " characteristic-container"

            with st.container():
                st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)

                # --- КОМПАКТНАЯ СТРОКА (5 колонок) ---
                cols = st.columns([2.2, 1, 0.7, 2.2, 0.6])

                # 1) Название + ID/приоритет/единица
                with cols[0]:
                    # Формируем метки: для дубликатов и для дополнительных
                    label_parts = [f"**{display_name}**"]
                    if char['is_duplicate']:
                        label_parts.append("🔄")
                    if char['is_extra']:
                        label_parts.append("➕")  # или " [Доп]" / "⭐" / любой другой символ
                    label = " ".join(label_parts)

                    is_active = st.checkbox(
                        label,
                        value=not char['is_extra'],
                        key=f"act_{char_id}"
                    )
                    info_parts = []
                    if char['id']:
                        info_parts.append(f"ID:{char['id']}")
                    if char['priority']:
                        info_parts.append(f"P:{char['priority']}")
                    if char['unit']:
                        info_parts.append(char['unit'])
                    st.caption(" | ".join(info_parts))

                # 2) Заполненность + сумма предложений
                with cols[1]:
                    total_offers = sum(v['offers'] for v in char['values_data'].values())
                    st.markdown(
                        f"<span style='font-size:0.9rem;'>📊 {char['fill_rate']:.0f}%</span><br>"
                        f"<span style='font-size:0.8rem; color:#64748b;'>📦 {total_offers}</span>",
                        unsafe_allow_html=True
                    )

                # 3) Чекбокс «Уникальная» (всегда виден)
                with cols[2]:
                    st.checkbox("Not var", key=f"uniq_{char_id}", help="Не делать переменной")

                # 4) Режим и контролы (Все / Top N / Вручную)
                with cols[3]:
                    mode_key = f"mode_{char_id}"
                    if mode_key not in st.session_state:
                        st.session_state[mode_key] = st.session_state.global_mode

                    mode = st.radio(
                        "Режим",
                        ["Все", "Top N", "Вручную"],
                        index=["Все", "Top N", "Вручную"].index(st.session_state[mode_key]),
                        key=mode_key,
                        horizontal=True,
                        label_visibility="collapsed"
                    )

                    if mode == "Top N":
                        safe_max = max(1, all_vals_count)
                        safe_default = min(st.session_state.global_top_n, safe_max)
                        topn_key = f"topn_{char_id}"
                        if topn_key not in st.session_state:
                            st.session_state[topn_key] = safe_default
                        st.number_input(
                            "N",
                            min_value=1,
                            max_value=safe_max,
                            value=st.session_state[topn_key],
                            key=topn_key,
                            label_visibility="collapsed"
                        )
                    elif mode == "Вручную" and all_vals_count > 0:
                        available_vals = list(char['values_data'].keys())
                        if len(available_vals) > 50:
                            available_vals = available_vals[:50]
                        st.multiselect(
                            "Выберите значения",
                            available_vals,
                            key=f"manual_{char_id}",
                            label_visibility="collapsed"
                        )
                    elif mode == "Вручную":
                        st.caption("Нет значений")

                # 5) Кнопка раскрытия (▶/▼)
                with cols[4]:
                    expand_label = "▼" if st.session_state[f"expanded_{char_id}"] else "▶"
                    if st.button(
                            expand_label,
                            key=f"expand_btn_{char_id}",
                            help="Дополнительные настройки и просмотр",
                            type="secondary"
                    ):
                        st.session_state[f"expanded_{char_id}"] = not st.session_state[f"expanded_{char_id}"]
                        st.rerun()

                # --- РАСКРЫВАЕМАЯ ПАНЕЛЬ (сортировка, предпросмотр, JSON) ---
                if st.session_state.get(f"expanded_{char_id}", False):
                    st.markdown('<div class="compact-details-panel">', unsafe_allow_html=True)

                    # Сортировка (только здесь)
                    sort_by = st.selectbox(
                        "Сортировка значений",
                        ["Предложения", "Кол-во товаров"],
                        key=f"sort_{char_id}",
                        label_visibility="visible"
                    )

                    # Кнопки предпросмотра и JSON
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        preview_state = st.session_state.get(f"preview_{char_id}", False)
                        preview_label = "🔍 Предпросмотр"
                        if st.button(preview_label, key=f"btn_preview_{char_id}"):
                            st.session_state[f"preview_{char_id}"] = not preview_state
                            st.rerun()
                    with col_btn2:
                        json_state = st.session_state.get(f"json_{char_id}", False)
                        json_label = "📋 JSON"
                        if st.button(json_label, key=f"btn_json_{char_id}"):
                            st.session_state[f"json_{char_id}"] = not json_state
                            st.rerun()

                    # --- Предпросмотр значений (если включён) ---
                    if st.session_state.get(f"preview_{char_id}", False):
                        with st.expander("🔍 Предпросмотр значений", expanded=True):
                            if all_vals_count == 0:
                                st.info("Нет значений")
                            else:
                                sorted_vals = []
                                for val, stats in char['values_data'].items():
                                    sorted_vals.append({
                                        "Значение": val[:100] + ("..." if len(val) > 100 else ""),
                                        "Товары": stats["count"],
                                        "Предложения": stats["offers"],
                                        "%": f"{(stats['count'] / len(raw_data['Товары']) * 100):.1f}"
                                    })

                                # Сортировка по выбранному критерию
                                sort_key = "offers" if sort_by == "Предложения" else "items_count"
                                reverse = True
                                # в sorted_vals ключи "Предложения" и "Товары"
                                if sort_by == "Предложения":
                                    sorted_vals.sort(key=lambda x: x['Предложения'], reverse=True)
                                else:
                                    sorted_vals.sort(key=lambda x: x['Товары'], reverse=True)

                                preview_size = min(10, len(sorted_vals))
                                st.write(f"**Топ-{preview_size} значений** (всего: {all_vals_count})")
                                st.dataframe(
                                    sorted_vals[:preview_size],
                                    use_container_width=True,
                                    height=min(400, preview_size * 35 + 40)
                                )

                    # --- Редактор JSON (если включён) ---
                    if st.session_state.get(f"json_{char_id}", False):
                        with st.expander("📝 Редактирование / JSON", expanded=True):
                            col_edit1, col_edit2 = st.columns([3, 1])
                            with col_edit1:
                                st.text_input(
                                    "Новое название",
                                    value=display_name,
                                    key=f"edit_name_{char_id}"
                                )
                            with col_edit2:
                                if st.button("💾 Сохранить", key=f"save_name_{char_id}"):
                                    # логика сохранения
                                    st.session_state.edited_names[char_id] = st.session_state[f"edit_name_{char_id}"]
                                    st.session_state[f"json_{char_id}"] = False
                                    st.rerun()
                                if st.button("❌ Отмена", key=f"cancel_edit_{char_id}"):
                                    st.session_state[f"json_{char_id}"] = False
                                    st.rerun()

                            st.markdown("### 📊 Исходные данные")
                            char_data = None
                            for param in raw_data.get("ПараметрыТовара", {}).get("Характеристики", []):
                                if param.get("ID") == char_id:
                                    char_data = param
                                    break
                            if char_data:
                                st.json(char_data)

                    st.markdown('</div>', unsafe_allow_html=True)

                # --- Сохраняем конфигурацию, если активна ---
                if is_active:
                    n_val_selected = (
                        st.session_state.get(f"topn_{char_id}", "all") if mode == "Top N"
                        else (st.session_state.get(f"manual_{char_id}", []) if mode == "Вручную" else "all")
                    )
                    selected_configs[char_id] = {
                        "name": display_name,
                        "original_name": char['original_name'],
                        "unit": char['unit'],
                        "is_unique": st.session_state.get(f"uniq_{char_id}", False),
                        "sort_by": st.session_state.get(f"sort_{char_id}", "Предложения"),
                        "mode": mode,
                        "n_val": n_val_selected,
                        "source_data": char['values_data'],
                        "is_duplicate": char['is_duplicate']
                    }

                st.markdown('</div>', unsafe_allow_html=True)

        # --- Генерация итогового массива ---
        if selected_configs and st.button("🚀 Сформировать итоговый массив", type="primary"):
            final_output = []
            edited_names_summary = {}

            for c_id, cfg in selected_configs.items():
                raw_vals = []
                for val, stats in cfg['source_data'].items():
                    raw_vals.append({
                        "value": val,
                        "items_count": stats["count"],
                        "offers_sum": stats["offers"],
                        "percent": (stats["count"] / len(raw_data["Товары"]) * 100)
                    })

                if cfg['sort_by'] == "Предложения":
                    raw_vals.sort(key=lambda x: x['offers_sum'], reverse=True)
                else:
                    raw_vals.sort(key=lambda x: x['items_count'], reverse=True)

                if cfg['mode'] == "Top N":
                    processed_vals = raw_vals[:cfg['n_val']]
                elif cfg['mode'] == "Вручную":
                    processed_vals = [v for v in raw_vals if v['value'] in cfg['n_val']]
                else:
                    processed_vals = raw_vals

                final_output.append({
                    "char_id": c_id,
                    "char_name": cfg['name'],
                    "original_name": cfg['original_name'],
                    "unit": cfg['unit'],
                    "is_unique": cfg['is_unique'],
                    "values": processed_vals,
                    "is_duplicate": cfg.get('is_duplicate', False)
                })

                if cfg['name'] != cfg['original_name']:
                    edited_names_summary[c_id] = {
                        "original": cfg['original_name'],
                        "edited": cfg['name']
                    }
            st.session_state.category_name = normalize_string(st.session_state.category_name)
            # Итоговый результат
            final_result = {
                "category": st.session_state.category_name,  # Здесь должно быть нормализованное значение
                "characteristics": final_output,
                "metadata": {
                    "source_file": uploaded_file.name,  # Оригинальное имя файла (может быть с пробелами)
                    "original_category": raw_data.get("ПараметрыТовара", {}).get("Наименование", "Неизвестно"),
                    # Уже нормализовано
                    "total_items": len(raw_data["Товары"]),
                    "selected_characteristics_count": len(final_output),
                    "export_timestamp": datetime.now().isoformat()
                }
            }

            # Для отладки выведем значения перед сохранением
            print(f"Финальная категория: {final_result['category']}")
            print(f"Оригинальная категория: {final_result['metadata']['original_category']}")


            # Сохраняем данные в session_state для главного приложения
            if 'app_data' not in st.session_state:
                st.session_state.app_data = {}

            st.session_state.app_data['phase1'] = final_result.copy()
            st.session_state.app_data['category'] = st.session_state.category_name
            # ======== КОНЕЦ ДОБАВЛЕНИЯ ========

            # Сохранение в session_state (этот код уже есть, оставляем его)
            st.session_state.phase1_data = final_result.copy()

            st.success(f"✅ Данные успешно собраны! Обработано характеристик: {len(final_output)}")
            st.info(f"🏷️ Категория для экспорта: **{st.session_state.category_name}**")

            # Сводки
            if edited_names_summary:
                with st.expander("📝 Сводка по переименованным характеристикам", expanded=False):
                    st.info(f"Переименовано характеристик: {len(edited_names_summary)}")
                    for c_id, names in list(edited_names_summary.items())[:10]:
                        st.write(f"**ID {c_id}**: `{names['original']}` → `{names['edited']}`")

            if duplicate_names:
                with st.expander("⚠️ Дублирующиеся названия в результатах", expanded=False):
                    st.warning("В результатах присутствуют характеристики с одинаковыми названиями:")
                    for name, ids in list(duplicate_names.items())[:5]:
                        selected_ids = [cid for cid in ids if cid in selected_configs]
                        if selected_ids:
                            st.write(f"**'{name}'** у ID: {', '.join(selected_ids)}")

            # Просмотр и экспорт
            with st.expander("📊 Просмотр итоговых данных", expanded=False):
                st.json(final_result)

            # Кнопки скачивания
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{st.session_state.category_name}_{timestamp}.json"

                st.download_button(
                    "💾 Скачать JSON данные",
                    data=json.dumps(final_result, ensure_ascii=False, indent=4),
                    file_name=filename,
                    mime="application/json"
                )

            with col_dl2:
                config_export = {
                    "category": st.session_state.category_name,
                    "source_file": uploaded_file.name,
                    "black_list": st.session_state.black_list,
                    "selected_ids": list(selected_configs.keys()),
                    "global_top_n": st.session_state.global_top_n,
                    "global_mode": st.session_state.global_mode,
                    "edited_names": st.session_state.edited_names
                }

                #st.download_button(
                    #"⚙️ Скачать Конфигурацию",
                    #data=json.dumps(config_export, ensure_ascii=False, indent=4),
                    #file_name=f"config_{timestamp}.json",
                    #mime="application/json"
                #)


    elif uploaded_file:
        st.warning("⏳ Обрабатываю файл...")
    else:
        st.info("📤 Пожалуйста, загрузите JSON файл в боковой панели для начала работы.")


if __name__ == "__main__":
    main()