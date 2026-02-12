import streamlit as st
import json
import os
import time
import random
from pathlib import Path
import re
import shutil


# --- CSS стили ---
def local_css():
    st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .prompt-block {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid #e0e0e0;
        font-family: monospace;
        font-size: 0.9em;
        white-space: pre-wrap;
    }
    .prompt-header {
        background-color: #f0f7ff;
        padding: 8px 12px;
        border-radius: 5px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    .characteristic-item {
        background-color: #f8f9fa;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 5px 0;
        border-left: 4px solid #6c757d;
    }
    .characteristic-item.regular {
        border-left-color: #28a745;
    }
    .characteristic-item.unique {
        border-left-color: #ffc107;
    }
    .variable-chip {
        display: inline-block;
        background-color: #e9ecef;
        padding: 3px 8px;
        border-radius: 15px;
        margin: 2px;
        font-size: 0.8em;
        border: 1px solid #dee2e6;
    }
    .variable-chip.static {
        background-color: #d4edda;
        border-color: #c3e6cb;
    }
    .variable-chip.dynamic {
        background-color: #cce5ff;
        border-color: #b8daff;
    }
    .edit-mode {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
    }
    .block-type-chip {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        margin-left: 8px;
    }
    .block-type-characteristic {
        background-color: #e3f2fd;
        color: #1565c0;
    }
    .block-type-other {
        background-color: #f3e5f5;
        color: #7b1fa2;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Классы для работы с данными ---
class BlockManager:
    """Управление блоками (шаблонами промптов)"""

    def __init__(self, blocks_dir="blocks"):
        self.blocks_dir = Path(blocks_dir)
        self.blocks_dir.mkdir(exist_ok=True)
        self.blocks = {}
        self.load_blocks()

    def load_blocks(self):
        """Загружает все блоки из файлов"""
        self.blocks = {}

        # Проверяем, есть ли папки блоков
        block_dirs = [d for d in self.blocks_dir.iterdir() if d.is_dir()]

        # Загружаем все блоки
        for block_dir in block_dirs:
            block_file = block_dir / "block.json"
            variables_file = block_dir / "variables.json"

            if block_file.exists():
                try:
                    with open(block_file, 'r', encoding='utf-8') as f:
                        block_data = json.load(f)

                    # Устанавливаем тип блока по умолчанию, если не указан
                    if "block_type" not in block_data:
                        # Определяем тип по названию или другим признакам
                        if "характеристика" in block_data.get("name", "").lower() or "характеристик" in block_data.get(
                                "description", "").lower():
                            block_data["block_type"] = "characteristic"
                        else:
                            block_data["block_type"] = "other"

                    # Загружаем переменные
                    if variables_file.exists():
                        with open(variables_file, 'r', encoding='utf-8') as f:
                            block_data["variables_data"] = json.load(f)
                    else:
                        block_data["variables_data"] = {}

                    self.blocks[block_data["block_id"]] = block_data

                except Exception as e:
                    st.error(f"Ошибка загрузки блока {block_dir.name}: {e}")

    def save_block(self, block_data, variables_data=None):
        """Сохраняет блок в файл"""
        block_id = block_data["block_id"]
        block_dir = self.blocks_dir / block_id
        block_dir.mkdir(exist_ok=True)

        block_file = block_dir / "block.json"
        variables_file = block_dir / "variables.json"

        try:
            # Сохраняем блок
            with open(block_file, 'w', encoding='utf-8') as f:
                json.dump(block_data, f, ensure_ascii=False, indent=2)

            # Сохраняем переменные, если переданы
            if variables_data:
                with open(variables_file, 'w', encoding='utf-8') as f:
                    json.dump(variables_data, f, ensure_ascii=False, indent=2)

            # Обновляем кэш
            if "variables_data" not in block_data and variables_data:
                block_data["variables_data"] = variables_data
            self.blocks[block_id] = block_data

            return True
        except Exception as e:
            st.error(f"Ошибка сохранения блока {block_id}: {e}")
            return False

    def delete_block(self, block_id):
        """Удаляет блок"""
        if block_id in self.blocks:
            block_dir = self.blocks_dir / block_id
            if block_dir.exists():
                shutil.rmtree(block_dir)
            del self.blocks[block_id]
            return True
        return False

    def create_new_block(self, base_block_id=None):
        """Создает новый блок"""
        if base_block_id and base_block_id in self.blocks:
            # Копируем существующий блок
            base_block = self.blocks[base_block_id]
            new_block_id = f"{base_block_id}_copy_{int(time.time())}"

            new_block = base_block.copy()
            new_block["block_id"] = new_block_id
            new_block["name"] = f"{base_block['name']} (копия)"

            # Копируем переменные
            variables_data = base_block.get("variables_data", {})

            return new_block_id, new_block, variables_data
        else:
            # Создаем пустой блок
            new_block_id = f"new_block_{int(time.time())}"
            new_block = {
                "block_id": new_block_id,
                "name": "Новый блок",
                "description": "Новый шаблон промпта",
                "template": "Твой шаблон здесь...\n{переменная1}\n{переменная2}",
                "variables": ["переменная1", "переменная2"],
                "settings": {
                    "маркер_позиция": "начало",
                    "формат_значения_regular": "[[значение]]",
                    "формат_значения_unique": "\"[значение]\"",
                    "добавлять_скобки_переменную": True
                },
                "block_type": "other"  # По умолчанию создаем блок типа other
            }

            variables_data = {
                "переменная1": {
                    "name": "переменная1",
                    "description": "Описание переменной 1",
                    "values": ["Значение 1", "Значение 2"],
                    "type": "static"
                },
                "переменная2": {
                    "name": "переменная2",
                    "description": "Описание переменной 2",
                    "values": ["Значение А", "Значение Б"],
                    "type": "static"
                }
            }

            return new_block_id, new_block, variables_data

    def get_block(self, block_id):
        """Получает блок по ID"""
        return self.blocks.get(block_id)

    def get_all_blocks(self):
        """Возвращает все блоки"""
        return self.blocks

    def get_blocks_by_type(self, block_type):
        """Возвращает блоки определенного типа"""
        return {block_id: block for block_id, block in self.blocks.items() if block.get("block_type") == block_type}


class VariableManager:
    """Управление переменными (упрощенная версия)"""

    def __init__(self, block_manager):
        self.block_manager = block_manager

    def get_variable_data(self, block_id, var_name):
        """Получает данные переменной из блока"""
        block = self.block_manager.get_block(block_id)
        if not block:
            return None

        variables_data = block.get("variables_data", {})
        return variables_data.get(var_name)

    def get_random_value(self, block_id, var_name):
        """Возвращает случайное значение переменной"""
        var_data = self.get_variable_data(block_id, var_name)
        if var_data and "values" in var_data and var_data["values"]:
            return random.choice(var_data["values"])
        return ""

    def save_variable(self, block_id, var_name, var_data):
        """Сохраняет переменную"""
        block = self.block_manager.get_block(block_id)
        if not block:
            return False

        if "variables_data" not in block:
            block["variables_data"] = {}

        block["variables_data"][var_name] = var_data
        return self.block_manager.save_block(block, block["variables_data"])


class MarkerRotator:
    """Ротация маркеров для равномерного использования"""

    def __init__(self, markers):
        self.markers = markers
        self.usage_counter = {marker: 0 for marker in markers}
        self.reset_cycle()

    def reset_cycle(self):
        """Сбрасывает цикл ротации"""
        self.available_markers = self.markers.copy()
        random.shuffle(self.available_markers)
        self.current_index = 0

    def get_next_marker(self):
        """Возвращает следующий маркер с ротацией"""
        if not self.markers:
            return ""

        # Если доступные маркеры закончились, сбрасываем цикл
        if not self.available_markers:
            self.reset_cycle()

        # Берем следующий маркер
        marker = self.available_markers[self.current_index]
        self.usage_counter[marker] += 1

        # Увеличиваем индекс
        self.current_index += 1
        if self.current_index >= len(self.available_markers):
            self.reset_cycle()

        return marker

    def get_marker_stats(self):
        """Возвращает статистику использования маркеров"""
        return self.usage_counter


class PromptGenerator:
    """Генератор промптов на основе блоков и переменных"""

    def __init__(self, block_manager, variable_manager):
        self.block_manager = block_manager
        self.variable_manager = variable_manager

    def generate_prompts_for_characteristic(self, characteristic, block_id, num_prompts_per_value, char_type="regular",
                                            category="", markers=None, marker_rotator=None):
        """Генерирует промпты для характеристики"""

        block = self.block_manager.get_block(block_id)
        if not block:
            return []

        prompts = []

        # Получаем значения характеристики
        values_list = characteristic.get("values", [])
        if not values_list:
            return []

        # Извлекаем сами значения из объектов
        values = [item["value"] for item in values_list if "value" in item]

        for value in values:
            for prompt_num in range(num_prompts_per_value):
                # Создаем контекст для генерации
                context = {
                    "category": category,
                    "characteristic_name": characteristic.get("char_name", ""),
                    "value": value,
                    "type": char_type,
                    "prompt_num": prompt_num + 1
                }

                # Генерируем промпт
                prompt = self.generate_single_prompt(block, context, markers, marker_rotator)

                if prompt:
                    prompts.append({
                        "characteristic_id": characteristic.get("char_id", ""),
                        "characteristic_name": characteristic.get("char_name", ""),
                        "value": value,
                        "prompt_num": prompt_num + 1,
                        "type": char_type,
                        "prompt": prompt,
                        "context": context
                    })

        return prompts

    def generate_prompts_for_block(self, block, num_prompts, category="", markers=None, marker_rotator=None):
        """Генерирует промпты для блока (не характеристика)"""

        if not block:
            return []

        prompts = []
        block_type = block.get("block_type", "other")

        for prompt_num in range(num_prompts):
            # Создаем контекст для генерации
            context = {
                "category": category,
                "block_id": block.get("block_id", ""),
                "block_name": block.get("name", ""),
                "block_type": block_type,
                "prompt_num": prompt_num + 1
            }

            # Генерируем промпт
            if block_type == "characteristic":
                # Для характеристик нужен особый контекст, но эта функция не должна вызываться для характеристик
                continue
            else:
                prompt = self.generate_single_other_block_prompt(block, context, markers, marker_rotator)

            if prompt:
                prompts.append({
                    "block_id": block.get("block_id", ""),
                    "block_name": block.get("name", ""),
                    "block_type": block_type,
                    "prompt_num": prompt_num + 1,
                    "prompt": prompt,
                    "context": context
                })

        return prompts

    def generate_single_prompt(self, block, context, markers=None, marker_rotator=None):
        """Генерирует один промпт для характеристики"""

        template = block.get("template", "")
        settings = block.get("settings", {})

        # 1. Форматируем значение в зависимости от типа
        if context["type"] == "regular":
            value_formatted = settings.get("формат_значения_regular", "[[значение]]").replace("значение",
                                                                                              context["value"])
        else:  # unique
            value_formatted = settings.get("формат_значения_unique", "\"[значение]\"").replace("значение",
                                                                                               context["value"])

        # 2. Заменяем специальный плейсхолдер для значения
        template = template.replace("{значение_форматированное}", value_formatted)

        # 3. Получаем маркер
        marker = ""
        if markers and marker_rotator:
            marker = marker_rotator.get_next_marker()

        # 4. Обрабатываем переменную скобки_характеристика
        if context["type"] == "regular" and settings.get("добавлять_скобки_переменную", True):
            # Добавляем значение переменной скобки_характеристика
            brackets_value = self.variable_manager.get_random_value(block["block_id"], "скобки_характеристика")
            template = template.replace("{скобки_характеристика}", brackets_value)
        else:
            # Убираем упоминание скобок
            template = template.replace("{скобки_характеристика}", "")

        # 5. Заменяем динамические переменные из данных
        template = template.replace("{контекст_категория}", f"Категория: {context['category']}")
        template = template.replace("{название_характеристики}", context["characteristic_name"])
        template = template.replace("{характеристика_маркер}", marker)

        # 6. Заменяем статические переменные (случайный выбор)
        for var_name in block.get("variables", []):
            if var_name in ["скобки_характеристика", "значение_форматированное", "контекст_категория",
                            "название_характеристики", "характеристика_маркер"]:
                continue  # Уже обработали

            placeholder = f"{{{var_name}}}"
            if placeholder in template:
                var_value = self.variable_manager.get_random_value(block["block_id"], var_name)
                template = template.replace(placeholder, var_value)

        # 7. Очищаем от лишних переносов и пробелов
        template = re.sub(r'\n{3,}', '\n\n', template.strip())

        return template

    def generate_single_other_block_prompt(self, block, context, markers=None, marker_rotator=None):
        """Генерирует один промпт для блока (не характеристика)"""

        template = block.get("template", "")

        # 1. Получаем маркер
        marker = ""
        if markers and marker_rotator:
            marker = marker_rotator.get_next_marker()

        # 2. Заменяем динамические переменные
        if "{контекст_категория}" in template:
            template = template.replace("{контекст_категория}", f"Категория: {context['category']}")

        if "{маркер}" in template:
            template = template.replace("{маркер}", marker)

        # 3. Заменяем статические переменные (случайный выбор)
        for var_name in block.get("variables", []):
            placeholder = f"{{{var_name}}}"
            if placeholder in template:
                var_value = self.variable_manager.get_random_value(block["block_id"], var_name)
                template = template.replace(placeholder, var_value)

        # 4. Очищаем от лишних переносов и пробелов
        template = re.sub(r'\n{3,}', '\n\n', template.strip())

        return template


# --- Основное приложение ---
def main():
    st.set_page_config(page_title="Data Harvester Phase 3", layout="wide")
    local_css()
    st.title("📝 Фаза 3: Генерация промптов")

    # --- Инициализация менеджеров ---
    if 'block_manager' not in st.session_state:
        st.session_state.block_manager = BlockManager()

    if 'variable_manager' not in st.session_state:
        st.session_state.variable_manager = VariableManager(st.session_state.block_manager)

    if 'marker_rotator' not in st.session_state:
        st.session_state.marker_rotator = None

    if 'phase3_generated_prompts' not in st.session_state:
        st.session_state.phase3_generated_prompts = []

    if 'phase3_prompts_per_value' not in st.session_state:
        st.session_state.phase3_prompts_per_value = 3  # По умолчанию 3 промпта на значение

    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False

    if 'phase3_global_prompts' not in st.session_state:
        st.session_state.phase3_global_prompts = 3

    if 'phase3_char_settings' not in st.session_state:
        st.session_state.phase3_char_settings = {}

    if 'phase3_other_blocks_settings' not in st.session_state:
        st.session_state.phase3_other_blocks_settings = {}

    # --- Загрузка данных из предыдущих фаз ---
    phase1_data = {}
    phase2_data = {}
    category = ""
    markers = []

    # Загрузка из session_state или app_data
    if 'phase1_data' in st.session_state and st.session_state.phase1_data:
        phase1_data = st.session_state.phase1_data
        category = phase1_data.get('category', '')

    if 'phase2_data' in st.session_state and st.session_state.phase2_data:
        phase2_data = st.session_state.phase2_data
        markers = phase2_data.get('markers', [])

    elif 'app_data' in st.session_state:
        app_data = st.session_state.app_data
        phase1_data = app_data.get('phase1', {})
        phase2_data = app_data.get('phase2', {})
        category = phase1_data.get('category', '') or app_data.get('category', '')
        markers = phase2_data.get('markers', [])

    # Отладка
    with st.expander("🔍 Отладка загрузки данных", expanded=False):
        st.write("**phase1_data:**", phase1_data.keys() if phase1_data else "Нет данных")
        if phase1_data:
            st.write(f"**Характеристик:** {len(phase1_data.get('characteristics', []))}")
            # Покажем первую характеристику для проверки структуры
            if phase1_data.get('characteristics'):
                first_char = phase1_data['characteristics'][0]
                st.write("**Первая характеристика:**")
                st.json({k: v for k, v in first_char.items() if k not in ['values']})
                st.write(f"**Значений у первой характеристики:** {len(first_char.get('values', []))}")

    # Проверяем наличие данных
    if not phase1_data or not phase1_data.get('characteristics'):
        st.error("""
        ## ❌ Данные фазы 1 не загружены

        Для работы фазы 3 необходимо выполнить фазу 1.

        **Решение:**
        1. Перейдите к фазе 1
        2. Загрузите JSON файл
        3. Выберите характеристики
        4. Нажмите "Сформировать итоговый массив"
        5. Вернитесь к фазе 3
        """)
        return

    # --- Боковая панель ---
    with st.sidebar:
        st.header("⚙️ Настройки фазы 3")

        # Переключение режима редактирования
        edit_mode = st.checkbox("Режим редактирования блоков", value=st.session_state.edit_mode)
        if edit_mode != st.session_state.edit_mode:
            st.session_state.edit_mode = edit_mode
            st.rerun()

        st.divider()

        # Информация о загруженных данных
        st.header("📊 Данные из предыдущих фаз")

        if phase1_data:
            chars_count = len(phase1_data.get('characteristics', []))
            st.success(f"✅ Фаза 1: {chars_count} характеристик")
            st.write(f"**Категория:** {category}")

            if chars_count > 0:
                unique_count = sum(1 for c in phase1_data['characteristics'] if c.get('is_unique', False))
                regular_count = chars_count - unique_count
                st.write(f"**Unique:** {unique_count}, **Regular:** {regular_count}")

        if phase2_data:
            markers_count = len(markers)
            st.success(f"✅ Фаза 2: {markers_count} маркеров")

        st.divider()

        # Глобальная настройка
        st.header("🎯 Глобальная настройка")

        global_prompts = st.number_input(
            "Промптов на значение (по умолчанию):",
            min_value=1,
            max_value=20,
            value=st.session_state.phase3_global_prompts,
            help="Будет применено ко всем характеристикам, если не настроено индивидуально"
        )

        if global_prompts != st.session_state.phase3_global_prompts:
            st.session_state.phase3_global_prompts = global_prompts
            st.rerun()

        # Кнопка применения глобальной настройки
        if st.button("📋 Применить ко всем характеристикам", use_container_width=True):
            if phase1_data and 'characteristics' in phase1_data:
                for char in phase1_data['characteristics']:
                    char_id = char.get('char_id', '')
                    if char_id:
                        if char_id not in st.session_state.phase3_char_settings:
                            st.session_state.phase3_char_settings[char_id] = {}
                        st.session_state.phase3_char_settings[char_id]['prompts_per_value'] = global_prompts
            st.success(f"Применено {global_prompts} промптов на значение для всех характеристик!")
            st.rerun()

        st.divider()

        # Управление
        if st.button("🔄 Сбросить ротацию маркеров", use_container_width=True):
            if markers:
                st.session_state.marker_rotator = MarkerRotator(markers)
                st.success("Ротация маркеров сброшена!")
                st.rerun()

    # --- Основной контент ---
    if st.session_state.edit_mode:
        show_edit_mode()
    else:
        show_generation_mode(phase1_data, category, markers)


def show_edit_mode():
    """Режим редактирования блоков и переменных"""
    st.header("✏️ Режим редактирования блоков")

    # Создаем табы
    tab1, tab2, tab3 = st.tabs(["📋 Управление блоками", "📝 Редактирование блока", "🔧 Редактирование переменных"])

    with tab1:
        show_blocks_management()

    with tab2:
        show_block_editor()

    with tab3:
        show_variables_editor()


def show_blocks_management():
    """Управление блоками: список, создание, удаление"""
    st.subheader("📋 Управление блоками")

    blocks = st.session_state.block_manager.get_all_blocks()

    if not blocks:
        st.info("Блоки не найдены. Создайте первый блок.")

    # Создание нового блока
    st.markdown("### ➕ Создать новый блок")

    col_create1, col_create2, col_create3 = st.columns([2, 2, 1])

    with col_create1:
        if blocks:
            base_block_options = ["(пустой блок)"] + list(blocks.keys())
            base_block = st.selectbox(
                "На основе блока:",
                base_block_options,
                format_func=lambda
                    x: "(пустой блок)" if x == "(пустой блок)" else f"{blocks[x].get('name', x)} ({blocks[x].get('block_type', 'other')})"
            )
        else:
            base_block = "(пустой блок)"

    with col_create2:
        block_type = st.selectbox(
            "Тип блока:",
            ["characteristic", "other"],
            format_func=lambda x: "Характеристика" if x == "characteristic" else "Другой блок"
        )

    with col_create3:
        if st.button("Создать", use_container_width=True):
            base_block_id = None if base_block == "(пустой блок)" else base_block

            new_block_id, new_block, variables_data = st.session_state.block_manager.create_new_block(base_block_id)

            # Устанавливаем тип блока
            new_block["block_type"] = block_type

            # Если создаем characteristic блок, добавляем стандартные настройки
            if block_type == "characteristic" and base_block == "(пустой блок)":
                new_block.update({
                    "name": "Шаблон для характеристики",
                    "description": "Универсальный шаблон для regular/unique характеристик",
                    "template": """Ты должен генерировать текст, полностью исключая определительные конструкции с тире и союзом 'что'.
{стиль_текста}.
Объем: {объем_характеристики}. 
{скобки_характеристика}
{контекст_категория}.
Тут крайне внимательно: {инструкция_характеристика} {название_характеристики} так, чтобы значение {значение_форматированное} было логично вставлено в текст, {подводка_характеристика}
Обязательно используй "{характеристика_маркер}" один раз в тексте.  
Структура предложения: {структура_характеристики}.
{ограничение_повторы}.
{требование_тошноты}.
{стоп}.""",
                    "variables": [
                        "стиль_текста",
                        "объем_характеристики",
                        "структура_характеристики",
                        "подводка_характеристика",
                        "инструкция_характеристика",
                        "ограничение_повторы",
                        "требование_тошноты",
                        "скобки_характеристика"
                    ],
                    "settings": {
                        "маркер_позиция": "начало",
                        "формат_значения_regular": "[[значение]]",
                        "формат_значения_unique": "\"[значение]\"",
                        "добавлять_скобки_переменную": True
                    }
                })

                # Базовые переменные для characteristic блока
                variables_data = {
                    "стиль_текста": {
                        "name": "стиль_текста",
                        "description": "Стиль текста для генерации",
                        "values": [
                            "Деловой стиль",
                            "Маркетинговый стиль",
                            "Технический стиль",
                            "Простой и понятный стиль"
                        ],
                        "type": "static"
                    },
                    "объем_характеристики": {
                        "name": "объем_характеристики",
                        "description": "Объем текста для характеристики",
                        "values": [
                            "2-3 предложения",
                            "3-4 предложения",
                            "4-5 предложений",
                            "Кратко, 1-2 предложения"
                        ],
                        "type": "static"
                    },
                    "структура_характеристики": {
                        "name": "структура_характеристики",
                        "description": "Структура предложения",
                        "values": [
                            "Простое повествовательное предложение",
                            "Сложносочиненное предложение с союзом 'и'",
                            "Предложение с вводными конструкциями"
                        ],
                        "type": "static"
                    },
                    "подводка_характеристика": {
                        "name": "подводка_характеристика",
                        "description": "Подводка для характеристики",
                        "values": [
                            "что делает его идеальным для использования",
                            "что обеспечивает высокое качество",
                            "что является важным преимуществом"
                        ],
                        "type": "static"
                    },
                    "инструкция_характеристика": {
                        "name": "инструкция_характеристика",
                        "description": "Инструкция для характеристики",
                        "values": [
                            "напиши о",
                            "сгенерируй текст о",
                            "опиши"
                        ],
                        "type": "static"
                    },
                    "ограничение_повторы": {
                        "name": "ограничение_повторы",
                        "description": "Ограничение на повторы",
                        "values": [
                            "Избегай повторений одних и тех же слов",
                            "Используй синонимы для разнообразия",
                            "Не повторяй одни и те же конструкции"
                        ],
                        "type": "static"
                    },
                    "требование_тошноты": {
                        "name": "требование_тошноты",
                        "description": "Требования к тошноте текста",
                        "values": [
                            "Тошнота текста должна быть низкой",
                            "Избегай спама ключевыми словами",
                            "Текст должен быть естественным"
                        ],
                        "type": "static"
                    },
                    "скобки_характеристика": {
                        "name": "скобки_характеристика",
                        "description": "Указание про скобки для regular характеристик",
                        "values": [
                            "Значение характеристики заключено в двойные квадратные скобки",
                            "Значение в [[ ]] нужно использовать как есть",
                            "Обрати внимание: значение в [[ ]]"
                        ],
                        "type": "static"
                    },
                    "стоп": {
                        "name": "стоп",
                        "description": "Стоп-слова и ограничения",
                        "values": [
                            "Не используй слова: очень, самый, лучший",
                            "Избегай: купить, заказать, цена",
                            "Не упоминай бренды и названия компаний"
                        ],
                        "type": "static"
                    }
                }

            # Сохраняем новый блок
            if st.session_state.block_manager.save_block(new_block, variables_data):
                st.success(f"✅ Создан новый блок: {new_block['name']} ({block_type})")
                # Перезагружаем блоки
                st.session_state.block_manager.load_blocks()
                st.session_state.current_edit_block = new_block_id
                # Переключаемся на вкладку редактирования
                st.rerun()
            else:
                st.error("❌ Ошибка создания блока")

    st.divider()

    # Список блоков
    st.markdown("### 📋 Список блоков")

    if blocks:
        for block_id, block in blocks.items():
            block_type = block.get("block_type", "other")
            block_type_display = "Характеристика" if block_type == "characteristic" else "Другой блок"

            col_list1, col_list2, col_list3, col_list4 = st.columns([3, 2, 1, 1])

            with col_list1:
                st.write(f"**{block.get('name', 'Без названия')}**")
                st.caption(f"ID: {block_id}")
                if block.get('description'):
                    st.caption(
                        block.get('description')[:100] + "..." if len(block.get('description')) > 100 else block.get(
                            'description'))

            with col_list2:
                st.markdown(f'<span class="block-type-chip block-type-{block_type}">{block_type_display}</span>',
                            unsafe_allow_html=True)

            with col_list3:
                # ИСПРАВЛЕНО: Кнопка редактирования теперь работает правильно
                if st.button("✏️", key=f"edit_{block_id}", help="Редактировать блок", use_container_width=True):
                    st.session_state.current_edit_block = block_id
                    st.rerun()

            with col_list4:
                # Запрещаем удаление только стандартных блоков, если они есть
                if st.button("🗑️", key=f"delete_{block_id}", help="Удалить блок", use_container_width=True):
                    if st.session_state.block_manager.delete_block(block_id):
                        st.success(f"✅ Блок '{block.get('name', '')}' удален")
                        st.rerun()

    else:
        st.info("Нет созданных блоков")


def show_block_editor():
    """Редактор блока"""

    # Выбор блока для редактирования
    blocks = st.session_state.block_manager.get_all_blocks()

    if not blocks:
        st.info("Нет блоков для редактирования")
        return

    # Инициализируем текущий редактируемый блок
    if 'current_edit_block' not in st.session_state:
        block_ids = list(blocks.keys())
        st.session_state.current_edit_block = block_ids[0] if block_ids else None

    # Выбор блока
    block_ids = list(blocks.keys())
    selected_block_id = st.selectbox(
        "Выберите блок для редактирования:",
        block_ids,
        index=block_ids.index(
            st.session_state.current_edit_block) if st.session_state.current_edit_block in block_ids else 0,
        format_func=lambda x: f"{blocks[x].get('name', x)} ({blocks[x].get('block_type', 'other')})"
    )

    if selected_block_id != st.session_state.current_edit_block:
        st.session_state.current_edit_block = selected_block_id
        st.rerun()

    selected_block = blocks[selected_block_id]

    # Редактирование блока
    with st.form(key="edit_block_form"):
        st.subheader(f"✏️ Редактирование блока: {selected_block['name']}")

        # Основные поля
        col1, col2 = st.columns([3, 1])
        with col1:
            block_name = st.text_input("Название блока", value=selected_block.get("name", ""))
        with col2:
            block_type = st.selectbox(
                "Тип блока:",
                ["characteristic", "other"],
                index=0 if selected_block.get("block_type", "other") == "characteristic" else 1,
                format_func=lambda x: "Характеристика" if x == "characteristic" else "Другой блок"
            )

        block_desc = st.text_area("Описание блока", value=selected_block.get("description", ""))

        # Шаблон
        st.markdown("### Шаблон промпта")
        st.caption(
            "Используйте `{переменная}` для вставки переменных, `{значение_форматированное}` для значения характеристики, `{маркер}` для маркера, `{контекст_категория}` для категории")
        template = st.text_area(
            "Шаблон",
            value=selected_block.get("template", ""),
            height=300
        )

        # Переменные блока
        st.markdown("### Переменные блока")
        current_vars = selected_block.get("variables", [])
        vars_text = "\n".join(current_vars)
        new_vars_text = st.text_area(
            "Переменные (каждая с новой строки)",
            value=vars_text,
            height=150,
            help="Каждая переменная должна быть на отдельной строке"
        )

        # Настройки (только для characteristic блоков)
        if block_type == "characteristic":
            st.markdown("### Настройки обработки характеристик")
            col1, col2 = st.columns(2)

            with col1:
                marker_position = st.selectbox(
                    "Позиция маркера",
                    ["начало", "текст", "любая"],
                    index=["начало", "текст", "любая"].index(
                        selected_block.get("settings", {}).get("маркер_позиция", "начало")
                    )
                )

                add_brackets_var = st.checkbox(
                    "Добавлять переменную скобки",
                    value=selected_block.get("settings", {}).get("добавлять_скобки_переменную", True)
                )

            with col2:
                format_regular = st.text_input(
                    "Формат значения (regular)",
                    value=selected_block.get("settings", {}).get("формат_значения_regular", "[[значение]]")
                )

                format_unique = st.text_input(
                    "Формат значения (unique)",
                    value=selected_block.get("settings", {}).get("формат_значения_unique", "\"[значение]\"")
                )

        # Кнопки сохранения
        col_save1, col_save2 = st.columns(2)
        with col_save1:
            if st.form_submit_button("💾 Сохранить блок", use_container_width=True):
                # Обновляем блок
                selected_block["name"] = block_name
                selected_block["description"] = block_desc
                selected_block["template"] = template
                selected_block["variables"] = [v.strip() for v in new_vars_text.split("\n") if v.strip()]
                selected_block["block_type"] = block_type

                # Обновляем настройки для characteristic блоков
                if block_type == "characteristic":
                    selected_block["settings"] = {
                        "маркер_позиция": marker_position,
                        "формат_значения_regular": format_regular,
                        "формат_значения_unique": format_unique,
                        "добавлять_скобки_переменную": add_brackets_var
                    }
                elif "settings" not in selected_block:
                    selected_block["settings"] = {}

                # Сохраняем
                if st.session_state.block_manager.save_block(selected_block):
                    st.success("✅ Блок сохранен!")
                    st.rerun()
                else:
                    st.error("❌ Ошибка сохранения блока")

        with col_save2:
            if st.form_submit_button("❌ Отмена", type="secondary", use_container_width=True):
                st.rerun()

    # Предпросмотр
    with st.expander("👁️ Предпросмотр шаблона", expanded=False):
        # Находим все переменные в шаблоне
        template_vars = re.findall(r'\{([^}]+)\}', template)

        if block_type == "characteristic":
            dynamic_vars = ["значение_форматированное", "контекст_категория", "название_характеристики",
                            "характеристика_маркер"]
        else:
            dynamic_vars = ["контекст_категория", "маркер"]

        col_vars1, col_vars2 = st.columns(2)

        with col_vars1:
            st.markdown("**Статические переменные:**")
            for var in set(template_vars):
                if var not in dynamic_vars:
                    st.markdown(f'<div class="variable-chip static">{{{var}}}</div>', unsafe_allow_html=True)

        with col_vars2:
            st.markdown("**Динамические переменные:**")
            for var in dynamic_vars:
                if var in template_vars:
                    st.markdown(f'<div class="variable-chip dynamic">{{{var}}}</div>', unsafe_allow_html=True)


def show_variables_editor():
    """Редактор переменных"""

    blocks = st.session_state.block_manager.get_all_blocks()

    if not blocks:
        st.info("Нет блоков для редактирования переменных")
        return

    # Выбор блока
    block_ids = list(blocks.keys())
    selected_block_id = st.selectbox(
        "Выберите блок:",
        block_ids,
        format_func=lambda x: f"{blocks[x].get('name', x)} ({blocks[x].get('block_type', 'other')})",
        key="var_editor_block"
    )

    selected_block = blocks[selected_block_id]
    variables = selected_block.get("variables", [])
    variables_data = selected_block.get("variables_data", {})

    if not variables:
        st.info("У этого блока нет переменных")
        return

    st.subheader(f"🔧 Редактирование переменных блока: {selected_block['name']}")

    # Выбор переменной
    selected_var = st.selectbox(
        "Выберите переменную:",
        variables,
        key="var_selector"
    )

    # Получаем данные переменной
    var_data = variables_data.get(selected_var, {
        "name": selected_var,
        "description": f"Описание для {selected_var}",
        "values": ["Пример значения 1", "Пример значения 2"],
        "type": "static"
    })

    # Редактирование переменной
    with st.form(key=f"edit_var_form_{selected_var}"):
        st.write(f"**Переменная:** `{selected_var}`")

        description = st.text_input(
            "Описание переменной:",
            value=var_data.get("description", "")
        )

        var_type = st.selectbox(
            "Тип переменной:",
            ["static", "dynamic"],
            index=0 if var_data.get("type", "static") == "static" else 1
        )

        # Значения переменной
        st.markdown("**Значения переменной:**")
        current_values = var_data.get("values", [])
        values_text = "\n".join(current_values)

        new_values = st.text_area(
            "Значения (каждое с новой строки):",
            value=values_text,
            height=200,
            key=f"var_values_{selected_var}"
        )

        col_save1, col_save2 = st.columns(2)
        with col_save1:
            if st.form_submit_button("💾 Сохранить переменную", use_container_width=True):
                # Обновляем данные переменной
                variables_data[selected_var] = {
                    "name": selected_var,
                    "description": description,
                    "type": var_type,
                    "values": [v.strip() for v in new_values.split("\n") if v.strip()]
                }

                # Сохраняем в блок
                selected_block["variables_data"] = variables_data
                if st.session_state.block_manager.save_block(selected_block, variables_data):
                    st.success(f"✅ Переменная '{selected_var}' сохранена!")
                    st.rerun()
                else:
                    st.error(f"❌ Ошибка сохранения переменной")

        with col_save2:
            if st.form_submit_button("🗑️ Удалить переменную", type="secondary", use_container_width=True):
                if selected_var in variables_data:
                    del variables_data[selected_var]
                    # Удаляем из списка переменных блока
                    if selected_var in selected_block.get("variables", []):
                        selected_block["variables"] = [v for v in selected_block["variables"] if v != selected_var]

                    if st.session_state.block_manager.save_block(selected_block, variables_data):
                        st.success(f"✅ Переменная '{selected_var}' удалена!")
                        st.rerun()
                    else:
                        st.error(f"❌ Ошибка удаления переменной")


def show_generation_mode(phase1_data, category, markers):
    """Основной режим - генерация промптов"""

    characteristics = phase1_data.get('characteristics', [])

    if not characteristics:
        st.warning("В данных фазы 1 нет характеристик")
        return

    st.header("🎯 Генерация промптов")

    # Информация
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.info(f"**Категория:** {category}")
    with col_info2:
        st.info(f"**Характеристик:** {len(characteristics)}")

    # Получаем блоки по типам
    blocks = st.session_state.block_manager.get_all_blocks()
    characteristic_blocks = st.session_state.block_manager.get_blocks_by_type("characteristic")
    other_blocks = st.session_state.block_manager.get_blocks_by_type("other")

    # Статистика по характеристикам
    with st.expander("📊 Настройка промптов для характеристик", expanded=True):
        st.write("**Настройте количество промптов для каждой характеристики:**")
        st.caption("Количество промптов, которые будут сгенерированы для КАЖДОГО значения характеристики")

        # Инициализируем словарь для хранения настроек промптов
        if 'phase3_char_settings' not in st.session_state:
            st.session_state.phase3_char_settings = {}

        # Глобальная настройка по умолчанию
        col_global1, col_global2 = st.columns([3, 1])
        with col_global1:
            st.markdown("**Глобальная настройка для всех характеристик:**")
        with col_global2:
            global_prompts = st.number_input(
                "Промптов на значение:",
                min_value=1,
                max_value=20,
                value=st.session_state.get('phase3_global_prompts', 3),
                key="global_prompts_input",
                label_visibility="collapsed"
            )

            if global_prompts != st.session_state.get('phase3_global_prompts', 3):
                st.session_state.phase3_global_prompts = global_prompts
                # Применяем глобальную настройку ко всем характеристикам
                for char in characteristics:
                    char_id = char.get('char_id', '')
                    if char_id:
                        st.session_state.phase3_char_settings[char_id] = {
                            'prompts_per_value': global_prompts,
                            'char_name': char.get('char_name', '')
                        }
                st.rerun()

        st.divider()

        total_values = 0
        total_prompts = 0

        # Таблица настроек для каждой характеристики
        for char in characteristics:
            char_name = char.get('char_name', 'Без названия')
            char_id = char.get('char_id', 'N/A')
            is_unique = char.get('is_unique', False)
            values_count = len(char.get('values', []))

            # Инициализируем настройки для характеристики, если их нет
            if char_id not in st.session_state.phase3_char_settings:
                st.session_state.phase3_char_settings[char_id] = {
                    'prompts_per_value': st.session_state.get('phase3_global_prompts', 3),
                    'char_name': char_name
                }

            # Получаем текущие настройки
            char_settings = st.session_state.phase3_char_settings[char_id]
            current_prompts = char_settings.get('prompts_per_value', 3)

            # Строка настройки
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])

            with col1:
                st.write(f"**{char_name}**")
                st.caption(f"ID: {char_id}")

            with col2:
                st.write(f"**{values_count}**")
                st.caption("значений")

            with col3:
                st.write(f"**{'Unique' if is_unique else 'Regular'}**")

            with col4:
                # Индивидуальная настройка количества промптов
                prompts_per_value = st.number_input(
                    "Промптов:",
                    min_value=1,
                    max_value=20,
                    value=current_prompts,
                    key=f"prompts_{char_id}",
                    label_visibility="collapsed"
                )

                # Сохраняем изменение
                if prompts_per_value != current_prompts:
                    st.session_state.phase3_char_settings[char_id]['prompts_per_value'] = prompts_per_value
                    st.rerun()

            with col5:
                # Расчет для этой характеристики
                char_prompts = values_count * prompts_per_value
                st.write(f"**→ {char_prompts}**")
                st.caption("промптов")

            total_values += values_count
            total_prompts += char_prompts

        st.divider()

        # Итоговая статистика
        col_total1, col_total2, col_total3 = st.columns(3)
        with col_total1:
            st.metric("Всего характеристик", len(characteristics))
        with col_total2:
            st.metric("Всего значений", total_values)
        with col_total3:
            st.metric("Всего промптов", total_prompts)

        # Быстрые действия
        st.markdown("---")
        col_actions1, col_actions2, col_actions3 = st.columns(3)

        with col_actions1:
            if st.button("🔄 Сбросить все к глобальному", use_container_width=True):
                global_val = st.session_state.get('phase3_global_prompts', 3)
                for char_id in st.session_state.phase3_char_settings:
                    st.session_state.phase3_char_settings[char_id]['prompts_per_value'] = global_val
                st.rerun()

        with col_actions2:
            if st.button("⚡ Установить 1 для всех", use_container_width=True):
                for char_id in st.session_state.phase3_char_settings:
                    st.session_state.phase3_char_settings[char_id]['prompts_per_value'] = 1
                st.session_state.phase3_global_prompts = 1
                st.rerun()

        with col_actions3:
            if st.button("🚀 Установить 5 для всех", use_container_width=True):
                for char_id in st.session_state.phase3_char_settings:
                    st.session_state.phase3_char_settings[char_id]['prompts_per_value'] = 5
                st.session_state.phase3_global_prompts = 5
                st.rerun()

    # Настройка для других блоков
    if other_blocks:
        with st.expander("📝 Настройка других блоков (заголовок, описание, применение и т.д.)", expanded=True):
            st.write("**Настройте количество промптов для каждого блока:**")

            # Инициализируем настройки для других блоков
            if 'phase3_other_blocks_settings' not in st.session_state:
                st.session_state.phase3_other_blocks_settings = {}

            other_total_prompts = 0

            for block_id, block in other_blocks.items():
                block_name = block.get('name', block_id)

                # Инициализируем настройки для блока, если их нет
                if block_id not in st.session_state.phase3_other_blocks_settings:
                    st.session_state.phase3_other_blocks_settings[block_id] = {
                        'enabled': True,
                        'prompts_count': 3
                    }

                block_settings = st.session_state.phase3_other_blocks_settings[block_id]

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    enabled = st.checkbox(
                        f"{block_name}",
                        value=block_settings.get('enabled', True),
                        key=f"other_enabled_{block_id}"
                    )

                with col2:
                    prompts_count = st.number_input(
                        "Промптов:",
                        min_value=1,
                        max_value=20,
                        value=block_settings.get('prompts_count', 3),
                        key=f"other_count_{block_id}",
                        label_visibility="collapsed"
                    )

                with col3:
                    st.write(f"**→ {prompts_count if enabled else 0}**")

                # Сохраняем изменения
                if enabled != block_settings.get('enabled', True):
                    st.session_state.phase3_other_blocks_settings[block_id]['enabled'] = enabled

                if prompts_count != block_settings.get('prompts_count', 3):
                    st.session_state.phase3_other_blocks_settings[block_id]['prompts_count'] = prompts_count

                if enabled:
                    other_total_prompts += prompts_count

            st.divider()
            col_other1, col_other2 = st.columns(2)
            with col_other1:
                st.metric("Всего других блоков", len(other_blocks))
            with col_other2:
                st.metric("Всего промптов для других блоков", other_total_prompts)

            # Быстрые действия для других блоков
            st.markdown("---")
            col_actions1, col_actions2, col_actions3 = st.columns(3)

            with col_actions1:
                if st.button("✅ Включить все блоки", use_container_width=True):
                    for block_id in other_blocks:
                        st.session_state.phase3_other_blocks_settings[block_id]['enabled'] = True
                    st.rerun()

            with col_actions2:
                if st.button("❌ Выключить все блоки", use_container_width=True):
                    for block_id in other_blocks:
                        st.session_state.phase3_other_blocks_settings[block_id]['enabled'] = False
                    st.rerun()

            with col_actions3:
                if st.button("🚀 3 промпта для всех", use_container_width=True):
                    for block_id in other_blocks:
                        st.session_state.phase3_other_blocks_settings[block_id]['prompts_count'] = 3
                    st.rerun()

    # Выбор блока для характеристик
    st.subheader("2. Выбор шаблона для генерации")

    # Проверяем и загружаем characteristic блоки
    if not characteristic_blocks:
        st.error("## ❌ Нет доступных блоков для характеристик")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Обновить список блоков", use_container_width=True):
                st.session_state.block_manager.load_blocks()
                st.rerun()

        with col2:
            if st.button("📝 Перейти в режим редактирования", use_container_width=True):
                st.session_state.edit_mode = True
                st.rerun()

        with col3:
            if st.button("🚀 Создать шаблон характеристик", type="primary", use_container_width=True):
                # Создаем стандартный блок для характеристик
                new_block_id, new_block, variables_data = st.session_state.block_manager.create_new_block()
                new_block.update({
                    "block_id": "characteristic_template",
                    "name": "Шаблон для характеристики",
                    "description": "Универсальный шаблон для regular/unique характеристик",
                    "block_type": "characteristic",
                    "template": """Ты должен генерировать текст, полностью исключая определительные конструкции с тире и союзом 'что'.
{стиль_текста}.
Объем: {объем_характеристики}. 
{скобки_характеристика}
{контекст_категория}.
Тут крайне внимательно: {инструкция_характеристика} {название_характеристики} так, чтобы значение {значение_форматированное} было логично вставлено в текст, {подводка_характеристика}
Обязательно используй "{характеристика_маркер}" один раз в тексте.  
Структура предложения: {структура_характеристики}.
{ограничение_повторы}.
{требование_тошноты}.
{стоп}.""",
                    "variables": [
                        "стиль_текста",
                        "объем_характеристики",
                        "структура_характеристики",
                        "подводка_характеристика",
                        "инструкция_характеристика",
                        "ограничение_повторы",
                        "требование_тошноты",
                        "скобки_характеристика"
                    ],
                    "settings": {
                        "маркер_позиция": "начало",
                        "формат_значения_regular": "[[значение]]",
                        "формат_значения_unique": "\"[значение]\"",
                        "добавлять_скобки_переменную": True
                    }
                })

                st.session_state.block_manager.save_block(new_block, variables_data)
                st.session_state.block_manager.load_blocks()
                st.success("✅ Стандартный шаблон характеристик создан!")
                st.rerun()

        return

    # Показываем информацию о доступных блоках
    st.success(f"✅ Доступно шаблонов для характеристик: {len(characteristic_blocks)}")
    if other_blocks:
        st.success(f"✅ Доступно других блоков: {len(other_blocks)}")

    # Выбор блока для характеристик
    block_ids = list(characteristic_blocks.keys())
    selected_block_id = st.selectbox(
        "Выберите шаблон для генерации характеристик:",
        block_ids,
        format_func=lambda x: characteristic_blocks[x].get("name", x),
        key="block_selector"
    )

    # Показать информацию о выбранном блоке
    selected_block = characteristic_blocks[selected_block_id]
    with st.expander("📋 Информация о шаблоне характеристик", expanded=False):
        st.write(f"**Название:** {selected_block.get('name', '')}")
        st.write(f"**Описание:** {selected_block.get('description', '')}")
        st.write(f"**Переменных:** {len(selected_block.get('variables', []))}")

        # Предпросмотр шаблона
        st.markdown("**Предпросмотр:**")
        st.code(selected_block.get('template', ''), language=None)

    # Генерация промптов
    st.subheader("3. Генерация промптов")

    # Показываем предварительный расчет
    total_char_prompts = 0
    for char in characteristics:
        char_id = char.get('char_id', '')
        values_count = len(char.get('values', []))
        char_settings = st.session_state.phase3_char_settings.get(char_id, {})
        prompts_per_value = char_settings.get('prompts_per_value', st.session_state.get('phase3_global_prompts', 3))
        total_char_prompts += values_count * prompts_per_value

    total_other_prompts = 0
    if other_blocks:
        for block_id, settings in st.session_state.phase3_other_blocks_settings.items():
            if settings.get('enabled', False):
                total_other_prompts += settings.get('prompts_count', 0)

    total_all_prompts = total_char_prompts + total_other_prompts

    col_calc1, col_calc2, col_calc3 = st.columns(3)
    with col_calc1:
        st.info(f"**Промптов для характеристик:** {total_char_prompts}")
    with col_calc2:
        if other_blocks:
            st.info(f"**Промптов для других блоков:** {total_other_prompts}")
    with col_calc3:
        st.info(f"**Всего промптов:** {total_all_prompts}")

    # Кнопка генерации
    if st.button("🚀 Сгенерировать все промпты", type="primary", use_container_width=True):
        with st.spinner("Генерация промптов..."):
            # Создаем генератор
            generator = PromptGenerator(
                st.session_state.block_manager,
                st.session_state.variable_manager
            )

            # Сбрасываем ротатор маркеров перед новой генерацией
            if markers:
                st.session_state.marker_rotator = MarkerRotator(markers)

            all_prompts = []

            # 1. Генерируем промпты для характеристик
            for char in characteristics:
                char_id = char.get('char_id', '')
                char_type = "unique" if char.get("is_unique", False) else "regular"

                # Получаем настройки для этой характеристики
                char_settings = st.session_state.phase3_char_settings.get(char_id, {})
                prompts_per_value = char_settings.get('prompts_per_value',
                                                      st.session_state.get('phase3_global_prompts', 3))

                # Генерируем промпты
                prompts = generator.generate_prompts_for_characteristic(
                    characteristic=char,
                    block_id=selected_block_id,
                    num_prompts_per_value=prompts_per_value,
                    char_type=char_type,
                    category=category,
                    markers=markers,
                    marker_rotator=st.session_state.marker_rotator
                )

                all_prompts.extend(prompts)

            # 2. Генерируем промпты для других блоков
            if other_blocks:
                for block_id, settings in st.session_state.phase3_other_blocks_settings.items():
                    if settings.get('enabled', False) and block_id in other_blocks:
                        block = other_blocks[block_id]
                        prompts_count = settings.get('prompts_count', 3)

                        # Генерируем промпты для блока
                        prompts = generator.generate_prompts_for_block(
                            block=block,
                            num_prompts=prompts_count,
                            category=category,
                            markers=markers,
                            marker_rotator=st.session_state.marker_rotator
                        )

                        all_prompts.extend(prompts)

            # Сохраняем промпты в session_state
            st.session_state.phase3_generated_prompts = all_prompts

            # Показываем статистику
            st.success(f"✅ Сгенерировано {len(all_prompts)} промптов!")
            if other_blocks:
                char_prompts = len([p for p in all_prompts if p.get('type') in ['regular', 'unique']])
                other_prompts = len([p for p in all_prompts if p.get('block_type') == 'other'])
                st.success(
                    f"📊 В том числе: {char_prompts} промптов для характеристик, {other_prompts} промптов для других блоков")

            # Сохраняем в общие данные приложения
            if 'app_data' in st.session_state:
                st.session_state.app_data['phase3'] = {
                    'prompts': all_prompts,
                    'category': category,
                    'markers': markers,
                    'characteristics_count': len(characteristics),
                    'other_blocks_count': len(other_blocks) if other_blocks else 0,
                    'total_prompts': len(all_prompts),
                    'char_settings': st.session_state.phase3_char_settings,
                    'other_blocks_settings': st.session_state.phase3_other_blocks_settings
                }

            # Автоскролл к результатам
            st.rerun()

    # Показать сгенерированные промпты
    if st.session_state.phase3_generated_prompts:
        st.subheader("📋 Сгенерированные промпты")

        # Фильтрация
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            # Собираем уникальные имена характеристик и блоков
            char_names = list(set(p['characteristic_name'] for p in st.session_state.phase3_generated_prompts if
                                  'characteristic_name' in p))
            block_names = list(
                set(p['block_name'] for p in st.session_state.phase3_generated_prompts if 'block_name' in p))

            filter_options = ["Все"]
            if char_names:
                filter_options.append("--- Характеристики ---")
                filter_options.extend(sorted(char_names))
            if block_names:
                filter_options.append("--- Другие блоки ---")
                filter_options.extend(sorted(block_names))

            filter_item = st.selectbox(
                "Фильтр по характеристике/блоку:",
                filter_options,
                key="filter_item"
            )

        with col_filter2:
            filter_type = st.selectbox(
                "Фильтр по типу:",
                ["Все", "regular", "unique", "other"],
                key="filter_type"
            )

        with col_filter3:
            items_per_page = st.selectbox(
                "Промптов на странице:",
                [5, 10, 20, 50],
                index=0,
                key="items_per_page"
            )

        # Применяем фильтры
        filtered_prompts = st.session_state.phase3_generated_prompts

        if filter_item != "Все":
            if filter_item.startswith("---"):
                # Пропускаем разделители
                pass
            else:
                filtered_prompts = [
                    p for p in filtered_prompts
                    if (p.get('characteristic_name') == filter_item) or (p.get('block_name') == filter_item)
                ]

        if filter_type != "Все":
            if filter_type == "other":
                filtered_prompts = [p for p in filtered_prompts if p.get('block_type') == 'other']
            else:
                filtered_prompts = [p for p in filtered_prompts if p.get('type') == filter_type]

        # Показываем количество
        st.caption(f"Показано {len(filtered_prompts)} из {len(st.session_state.phase3_generated_prompts)} промптов")

        # Пагинация
        if 'page' not in st.session_state:
            st.session_state.page = 0

        total_pages = max(1, (len(filtered_prompts) + items_per_page - 1) // items_per_page)

        col_pag1, col_pag2, col_pag3 = st.columns([1, 3, 1])
        with col_pag1:
            if st.button("◀️ Предыдущая", disabled=st.session_state.page == 0):
                st.session_state.page -= 1
                st.rerun()

        with col_pag2:
            st.write(f"Страница {st.session_state.page + 1} из {total_pages}")

        with col_pag3:
            if st.button("Следующая ▶️", disabled=st.session_state.page >= total_pages - 1):
                st.session_state.page += 1
                st.rerun()

        # Показываем промпты для текущей страницы
        start_idx = st.session_state.page * items_per_page
        end_idx = min(start_idx + items_per_page, len(filtered_prompts))

        for i, prompt_data in enumerate(filtered_prompts[start_idx:end_idx]):
            # Определяем заголовок для промпта
            if 'characteristic_name' in prompt_data:
                title = f"Характеристика: {prompt_data['characteristic_name']} = {prompt_data['value']} ({prompt_data['type']})"
            else:
                title = f"Блок: {prompt_data['block_name']} (промпт {prompt_data['prompt_num']})"

            with st.expander(f"Промпт #{start_idx + i + 1}: {title}", expanded=False):
                st.markdown('<div class="prompt-block">' + prompt_data['prompt'] + '</div>', unsafe_allow_html=True)

                if 'characteristic_name' in prompt_data:
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.caption(f"**Характеристика:** {prompt_data['characteristic_name']}")
                    with col_info2:
                        st.caption(f"**Значение:** {prompt_data['value']}")
                    with col_info3:
                        st.caption(f"**Тип:** {prompt_data['type']}")
                else:
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.caption(f"**Блок:** {prompt_data['block_name']}")
                    with col_info2:
                        st.caption(f"**Тип блока:** {prompt_data.get('block_type', 'other')}")

        if len(filtered_prompts) > end_idx:
            st.info(f"И ещё {len(filtered_prompts) - end_idx} промптов...")

        # Передача в фазу 4
        st.divider()
        st.subheader("➡️ Передача данных")

        col_transfer1, col_transfer2 = st.columns(2)
        with col_transfer1:
            if st.button("💾 Сохранить для фазы 4", use_container_width=True, key="save_for_phase4"):
                st.session_state.phase3_data = {
                    'prompts': st.session_state.phase3_generated_prompts,
                    'category': category,
                    'markers': markers,
                    'characteristics': characteristics,
                    'generation_settings': {
                        'block_id': selected_block_id,
                        'char_settings': st.session_state.phase3_char_settings,
                        'other_blocks_settings': st.session_state.phase3_other_blocks_settings
                    }
                }
                st.success("✅ Данные сохранены для передачи в фазу 4!")

        with col_transfer2:
            # Экспорт промптов в JSON
            export_data = {
                'category': category,
                'total_prompts': len(st.session_state.phase3_generated_prompts),
                'prompts': st.session_state.phase3_generated_prompts[:100]  # Ограничиваем для размера файла
            }

            st.download_button(
                label="📥 Скачать промпты (JSON)",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"prompts_{category}.json",
                mime="application/json",
                use_container_width=True,
                key="download_prompts"
            )


if __name__ == "__main__":
    main()