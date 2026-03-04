
import html
import json
from pathlib import Path
import re
import shutil
import streamlit as st
import time
from ai_module import AIConfigManager, AIGenerator, AIInstructionManager


def init_ai_managers():
    """Инициализация менеджеров AI"""
    if 'ai_config_manager' not in st.session_state:
        st.session_state.ai_config_manager = AIConfigManager()

    if 'ai_generator' not in st.session_state:
        st.session_state.ai_generator = AIGenerator(st.session_state.ai_config_manager)

    if 'ai_instruction_manager' not in st.session_state:
        st.session_state.ai_instruction_manager = AIInstructionManager()


def show_ai_variable_generator(block_id, var_name, var_data):
    """Интерфейс для генерации AI-инструкций"""

    init_ai_managers()

    st.markdown("### 🤖 Генерация AI-инструкций")

    # Выбор провайдера
    provider = st.selectbox(
        "AI провайдер:",
        ["openai", "deepseek"],
        index=0 if st.session_state.ai_config_manager.config["default_provider"] == "openai" else 1,
        key=f"ai_provider_{block_id}_{var_name}"
    )

    # Промпт для генерации
    prompt_template = st.text_area(
        "Промпт для AI:",
        value=var_data.get("ai_prompt", ""),
        height=200,
        key=f"ai_prompt_{block_id}_{var_name}",
        help="Используйте {категория}, {характеристика}, {значение} для подстановки контекста"
    )

    # Количество вариантов
    num_variants = st.number_input(
        "Количество вариантов:",
        min_value=1,
        max_value=10,
        value=var_data.get("ai_num_variants", 1),
        key=f"ai_num_variants_{block_id}_{var_name}"
    )

    # Контекст для генерации
    with st.expander("⚙️ Контекст для генерации"):
        st.info("Контекст будет автоматически подставляться из данных фазы 2")

        # Показываем пример контекста
        example_context = {
            "категория": "Адаптер котла",
            "характеристика": "Диаметр",
            "значение": "115 мм",
            "тип": "regular"
        }
        st.json(example_context)

    # Кнопки генерации
    col_gen1, col_gen2, col_gen3 = st.columns(3)

    with col_gen1:
        if st.button("🧪 Тестовая генерация", key=f"test_gen_{block_id}_{var_name}"):
            with st.spinner("Генерация тестового варианта..."):
                test_context = {
                    "категория": "Тестовая категория",
                    "характеристика": "Тестовая характеристика",
                    "значение": "Тестовое значение",
                    "тип": "regular"
                }

                results = st.session_state.ai_generator.generate_instruction(
                    prompt_template,
                    test_context,
                    provider=provider,
                    num_variants=1
                )

                if results and results[0]["success"]:
                    st.success("✅ Тестовая генерация успешна!")
                    st.text_area("Результат:", value=results[0]["text"], height=150)
                else:
                    st.error(f"❌ Ошибка: {results[0].get('error', 'Неизвестная ошибка')}")

    with col_gen2:
        if st.button("🚀 Сгенерировать для всех характеристик",
                     key=f"gen_all_{block_id}_{var_name}"):

            # Получаем данные из фазы 2
            phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
            category = phase2_data.get('category', '')
            characteristics = st.session_state.get('loaded_data', {}).get('characteristics', [])

            if not category or not characteristics:
                st.error("❌ Нет данных из фазы 2. Загрузите данные сначала.")
                return

            with st.spinner(f"Генерация инструкций для {len(characteristics)} характеристик..."):
                results = st.session_state.ai_generator.batch_generate_for_characteristics(
                    prompt_template,
                    characteristics,
                    category,
                    provider=provider
                )

                # Сохраняем результаты
                saved_count = 0
                for char_id, char_results in results.items():
                    if char_results:
                        # Для regular характеристик
                        if isinstance(char_results, list) and len(char_results) > 0 and isinstance(char_results[0],
                                                                                                   dict):
                            # Это unique - результаты для каждого значения
                            for value_result in char_results:
                                context = {
                                    "категория": category,
                                    "характеристика": next((c.get('char_name', '') for c in characteristics
                                                            if c.get('char_id') == char_id), ''),
                                    "значение": value_result.get("value", ""),
                                    "тип": "unique"
                                }

                                values = [r["text"] for r in value_result.get("results", []) if r.get("success")]

                                if values:
                                    st.session_state.ai_instruction_manager.save_instruction(
                                        block_id,
                                        var_name,
                                        values,
                                        context
                                    )
                                    saved_count += len(values)
                        else:
                            # Это regular - общие результаты
                            context = {
                                "категория": category,
                                "характеристика": next((c.get('char_name', '') for c in characteristics
                                                        if c.get('char_id') == char_id), ''),
                                "тип": "regular"
                            }

                            values = [r["text"] for r in char_results if r.get("success")]

                            if values:
                                st.session_state.ai_instruction_manager.save_instruction(
                                    block_id,
                                    var_name,
                                    values,
                                    context
                                )
                                saved_count += len(values)

                st.success(f"✅ Сгенерировано и сохранено {saved_count} инструкций!")
                st.rerun()

    with col_gen3:
        if st.button("🔄 Загрузить сохраненные инструкции",
                     key=f"load_saved_{block_id}_{var_name}"):
            # Загружаем сохраненные инструкции для этой переменной
            instructions = st.session_state.ai_instruction_manager.get_instruction(block_id, var_name)

            if instructions:
                # Обновляем значения переменной
                var_data["values"] = instructions
                st.success(f"✅ Загружено {len(instructions)} сохраненных инструкций")
                st.rerun()
            else:
                st.info("Нет сохраненных инструкций для этой переменной")

    # Редактор сохраненных инструкций
    st.markdown("### 📝 Редактирование сохраненных инструкций")

    # Получаем все сохраненные инструкции для этой переменной
    if block_id in st.session_state.ai_instruction_manager.instructions:
        if var_name in st.session_state.ai_instruction_manager.instructions[block_id]:
            for context_hash, instruction_data in st.session_state.ai_instruction_manager.instructions[block_id][
                var_name].items():
                context = instruction_data.get("context", {})
                values = instruction_data.get("values", [])

                with st.expander(f"Контекст: {context.get('характеристика', 'Общий')} ({context.get('тип', 'N/A')})"):
                    st.json(context)

                    for idx, value in enumerate(values):
                        col_edit1, col_edit2 = st.columns([4, 1])
                        with col_edit1:
                            new_value = st.text_area(
                                f"Инструкция {idx + 1}:",
                                value=value,
                                height=100,
                                key=f"edit_{block_id}_{var_name}_{context_hash}_{idx}"
                            )

                        with col_edit2:
                            if st.button("💾", key=f"save_{block_id}_{var_name}_{context_hash}_{idx}"):
                                if st.session_state.ai_instruction_manager.update_instruction_value(
                                        block_id, var_name, context_hash, idx, new_value
                                ):
                                    st.success("Сохранено!")
                                    st.rerun()

                    # Удаление всего контекста
                    if st.button("🗑️ Удалить все инструкции для этого контекста",
                                 key=f"delete_{block_id}_{var_name}_{context_hash}"):
                        if st.session_state.ai_instruction_manager.delete_instruction(
                                block_id, var_name, context_hash
                        ):
                            st.success("Удалено!")
                            st.rerun()

    # Сохраняем AI-настройки в var_data
    var_data["ai_prompt"] = prompt_template
    var_data["ai_num_variants"] = num_variants
    var_data["ai_provider"] = provider

    return var_data
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
    .edit-mode {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Новый класс для обработки динамических переменных ---
class DynamicVariableProcessor:
    """Универсальный обработчик динамических переменных"""

    def __init__(self, dynamic_var_manager):
        self.dynamic_var_manager = dynamic_var_manager

    def render_template_with_context(self, template, context_data=None, include_dynamic=True):
        """Рендерит шаблон с подстановкой контекста"""
        if not template:
            return template

        # Копируем шаблон для работы
        result = template

        # Подготавливаем контекст
        context = context_data or {}

        # Заменяем динамические переменные
        if include_dynamic:
            result = self._replace_dynamic_variables(result, context)

        # Заменяем статические переменные (оставляем как есть для фазы 3)
        # В фазе 3 мы не заменяем их реальными значениями
        # В фазе 4 они будут заменены отдельно

        return result

    def _replace_dynamic_variables(self, template, context):
        """Заменяет динамические переменные в шаблоне"""
        # Находим все переменные в шаблоне
        variables = re.findall(r'\{([^}]+)\}', template)

        for var_name in variables:
            # Пропускаем статические переменные без данных
            var_data = self.dynamic_var_manager.get_dynamic_variable(var_name)
            if not var_data:
                continue

            # Получаем значение с подстановкой контекста
            value = self._get_dynamic_value_with_context(var_name, var_data, context)

            # Экранируем HTML в значении
            if value:
                escaped_value = html.escape(str(value))
                template = template.replace(f"{{{var_name}}}", escaped_value)

        return template

    def _get_dynamic_value_with_context(self, var_name, var_data, context):
        """Получает значение динамической переменной с подстановкой контекста"""
        values = var_data.get("values", [])
        if not values:
            return ""

        # Выбираем случайное значение
        import random
        value = random.choice(values)

        # Подставляем контекстные данные
        if context:
            for key, val in context.items():
                placeholder = f"{{{key}}}"
                if placeholder in value:
                    # Экранируем HTML в подставляемом значении
                    escaped_val = html.escape(str(val))
                    value = value.replace(placeholder, escaped_val)

        return value

    def get_context_for_preview(self):
        """Возвращает контекст для предпросмотра в фазе 3"""
        return {
            "категория": "Смартфоны",
            "стоп-слова": "купить, заказать, цена, дешево",
            "характеристика": "диагональ экрана",
            "значение": "6.5 дюймов",
            "маркер": "[МАРКЕР]",
            "название_характеристики": "Диагональ экрана"
        }


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
                "settings": {},  # Упрощаем настройки
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


class DynamicVariableManager:
    """Управление динамическими переменными"""

    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.dynamic_vars_file = self.config_dir / "dynamic_variables.json"
        self.dynamic_vars = {}
        self.processor = None
        self.load_dynamic_variables()

    def get_processor(self):
        """Возвращает процессор для работы с динамическими переменными"""
        if not self.processor:
            self.processor = DynamicVariableProcessor(self)
        return self.processor

    def load_dynamic_variables(self):
        """Загружает динамические переменные из файла"""
        if self.dynamic_vars_file.exists():
            try:
                with open(self.dynamic_vars_file, 'r', encoding='utf-8') as f:
                    self.dynamic_vars = json.load(f)
            except Exception as e:
                st.error(f"Ошибка загрузки динамических переменных: {e}")
                self.dynamic_vars = self.get_default_dynamic_vars()
        else:
            self.dynamic_vars = self.get_default_dynamic_vars()
            self.save_dynamic_variables()

    def save_dynamic_variables(self):
        """Сохраняет динамические переменные в файл"""
        try:
            with open(self.dynamic_vars_file, 'w', encoding='utf-8') as f:
                json.dump(self.dynamic_vars, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Ошибка сохранения динамических переменных: {e}")
            return False

    def get_default_dynamic_vars(self):
        """Возвращает динамические переменные по умолчанию"""
        return {
            "стоп": {
                "name": "стоп",
                "description": "Стоп-слова и ограничения",
                "values": [
                    "Не используй слова: очень, самый, лучший",
                    "Избегай: купить, заказать, цена",
                    "Не упоминай бренды и названия компаний",
                    "Не используй восклицательные знаки",
                    "Избегай клишированных фраз"
                ],
                "type": "dynamic",
                "source": "config"
            },
            "контекст_категория": {
                "name": "контекст_категория",
                "description": "Контекст и категория товара",
                "values": ["{подставляется_из_данных}"],
                "type": "dynamic",
                "source": "data"
            },
            "значение_форматированное": {
                "name": "значение_форматированное",
                "description": "Отформатированное значение характеристики",
                "values": ["{подставляется_на_основе_типа_характеристики}"],
                "type": "dynamic",
                "source": "processing"
            },
            "название_характеристики": {
                "name": "название_характеристики",
                "description": "Название текущей характеристики",
                "values": ["{подставляется_из_данных}"],
                "type": "dynamic",
                "source": "data"
            },
            "характеристика_маркер": {
                "name": "характеристика_маркер",
                "description": "Маркер для вставки в текст характеристики",
                "values": ["{маркер_позиция}"],
                "type": "dynamic",
                "source": "config"
            },
            "маркер": {
                "name": "маркер",
                "description": "Маркер для других типов блоков",
                "values": ["[МАРКЕР]"],
                "type": "dynamic",
                "source": "config"
            }
        }

    def get_dynamic_variable(self, var_name):
        """Получает динамическую переменную по имени"""
        return self.dynamic_vars.get(var_name)

    def update_dynamic_variable(self, var_name, var_data):
        """Обновляет динамическую переменную"""
        self.dynamic_vars[var_name] = var_data
        return self.save_dynamic_variables()

    def get_all_dynamic_vars(self):
        """Возвращает все динамические переменные"""
        return self.dynamic_vars


class VariableManager:
    """Управление переменными (упрощенная версия)"""

    def __init__(self, block_manager):
        self.block_manager = block_manager

    def get_all_variables_with_data(self, block_id):
        """Возвращает все переменные блока с их данными"""
        block = self.get_block(block_id)
        if not block:
            return {}

        result = {}

        # Добавляем статические переменные
        static_vars = block.get("variables", [])
        variables_data = block.get("variables_data", {})

        for var_name in static_vars:
            if var_name in variables_data:
                result[var_name] = variables_data[var_name]
            else:
                result[var_name] = {
                    "name": var_name,
                    "description": f"Описание для {var_name}",
                    "values": [f"Значение для {var_name}"],
                    "type": "static"
                }

        return result

    def get_variable_data(self, block_id, var_name):
        """Получает данные переменной из блока"""
        block = self.block_manager.get_block(block_id)
        if not block:
            return None

        variables_data = block.get("variables_data", {})
        return variables_data.get(var_name)

    def save_variable(self, block_id, var_name, var_data):
        """Сохраняет переменную"""
        block = self.block_manager.get_block(block_id)
        if not block:
            return False

        if "variables_data" not in block:
            block["variables_data"] = {}

        block["variables_data"][var_name] = var_data
        return self.block_manager.save_block(block, block["variables_data"])

    def get_block(self, block_id):
        """Получает блок по ID"""
        return self.block_manager.get_block(block_id)


# --- Основное приложение фазы 3 ---
def main():
    st.set_page_config(page_title="Data Harvester Phase 3 - Редактирование блоков", layout="wide")
    local_css()
    st.title("📝 Фаза 3: Редактирование блоков и шаблонов")
    st.markdown("---")

    # --- Инициализация менеджеров ---
    if 'block_manager' not in st.session_state:
        st.session_state.block_manager = BlockManager()

    if 'variable_manager' not in st.session_state:
        st.session_state.variable_manager = VariableManager(st.session_state.block_manager)

    # Инициализация менеджера динамических переменных
    if 'dynamic_var_manager' not in st.session_state:
        st.session_state.dynamic_var_manager = DynamicVariableManager()

    # --- Боковая панель ---


    # --- Основной контент ---
    show_edit_mode()

def show_ai_variables_overview():
    st.subheader("🤖 Все AI-переменные")

    if 'ai_instruction_manager' not in st.session_state:
        init_ai_managers()

    # Получаем текущую категорию
    phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
    current_category = phase2_data.get('category', '')
    if not current_category:
        st.warning("⚠️ Категория не загружена. Статус и предпросмотр будут недоступны. Загрузите данные в фазе 2.")

    blocks = st.session_state.block_manager.get_all_blocks()
    ai_vars = []
    for block_id, block in blocks.items():
        variables_data = block.get("variables_data", {})
        for var_name, var_data in variables_data.items():
            if var_data.get("type") == "ai":
                ai_vars.append((block_id, block, var_name, var_data))

    if not ai_vars:
        st.info("Нет AI-переменных. Создайте их во вкладке «Редактирование статических переменных» → AI.")
        return

    # --- Кнопки управления выбором ---
    col1, col2, col3, col4 = st.columns([1, 1, 2, 4])
    with col1:
        if st.button("✅ Выбрать всё", key="select_all_ai", use_container_width=True):
            for b_id, _, v_name, _ in ai_vars:
                st.session_state[f"chk_{b_id}_{v_name}"] = True
            st.rerun()
    with col2:
        if st.button("❌ Снять всё", key="deselect_all_ai", use_container_width=True):
            for b_id, _, v_name, _ in ai_vars:
                st.session_state[f"chk_{b_id}_{v_name}"] = False
            st.rerun()
    with col3:
        if st.button("🚀 Массовая генерация", type="primary", key="mass_gen_ai", use_container_width=True):
            selected = []
            for b_id, _, v_name, _ in ai_vars:
                if st.session_state.get(f"chk_{b_id}_{v_name}", False):
                    selected.append((b_id, v_name))
            if selected:
                st.session_state.ai_mass_selected = selected
                st.session_state.ai_mass_generation_requested = True
                st.rerun()
            else:
                st.warning("Не выбрано ни одной переменной")
    with col4:
        st.caption("Выберите переменные для массовой генерации")

    st.divider()

    # --- Заголовки таблицы ---
    cols = st.columns([0.5, 2, 2, 1, 2, 3, 3])  # Увеличили последнюю колонку для двух кнопок
    cols[0].write("")
    cols[1].write("**Переменная**")
    cols[2].write("**Блок**")
    cols[3].write("**Тип**")
    cols[4].write("**Статус**")
    cols[5].write("**Предпросмотр (для текущей категории)**")
    cols[6].write("**Действия**")

    # --- Строки ---
    for block_id, block, var_name, var_data in ai_vars:
        col_chk, col_var, col_block, col_type, col_status, col_preview, col_action = st.columns([0.5, 2, 2, 1, 2, 3, 3])

        with col_chk:
            default_val = st.session_state.get(f"chk_{block_id}_{var_name}", False)
            st.checkbox(
                f"Выбрать {var_name}",
                value=default_val,
                key=f"chk_{block_id}_{var_name}",
                label_visibility="collapsed"
            )

        with col_var:
            st.write(f"`{var_name}`")

        with col_block:
            st.write(block.get("name", block_id)[:30])

        with col_type:
            btype = block.get("block_type", "other")
            st.write("📊" if btype == "characteristic" else "📄")

        with col_status:
            if has_ai_values(block_id, var_name):
                st.success("✅ сгенерирована")
            else:
                st.error("❌ не сгенерирована")

        with col_preview:
            preview = ""
            if 'ai_instruction_manager' in st.session_state and current_category:
                ai_mgr = st.session_state.ai_instruction_manager
                if block_id in ai_mgr.instructions and var_name in ai_mgr.instructions[block_id]:
                    for ctx_data in ai_mgr.instructions[block_id][var_name].values():
                        context = ctx_data.get("context", {})
                        if context.get("категория") == current_category:
                            values = ctx_data.get("values", [])
                            if values:
                                preview = values[0][:100] + ("..." if len(values[0]) > 100 else "")
                                break
            if preview:
                st.write(preview)
            else:
                st.caption("нет для этой категории")

        with col_action:
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                if st.button("🚀", key=f"gen_{block_id}_{var_name}", help="Генерировать"):
                    st.session_state.ai_overview_selected = (block_id, var_name)
                    st.rerun()
            with subcol2:
                if st.button("📋", key=f"view_{block_id}_{var_name}", help="Просмотреть все инструкции"):
                    st.session_state.ai_view_selected = (block_id, var_name)
                    st.rerun()

    st.divider()

    # --- Массовая генерация (без изменений) ---
    if st.session_state.get("ai_mass_generation_requested", False):
        selected = st.session_state.get("ai_mass_selected", [])
        if not selected:
            st.warning("Нет выбранных переменных")
            st.session_state.ai_mass_generation_requested = False
        else:
            st.session_state.ai_mass_generation_requested = False
            with st.spinner("Массовая генерация..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                results_log = []
                for i, (b_id, v_name) in enumerate(selected):
                    status_text.text(f"Обработка {i+1}/{len(selected)}: {b_id} / {v_name}")
                    block = st.session_state.block_manager.get_block(b_id)
                    if block is None:
                        results_log.append({"block": b_id, "var": v_name, "success": 0, "errors": 1})
                        progress_bar.progress((i + 1) / len(selected))
                        continue
                    var_data = block.get("variables_data", {}).get(v_name)
                    if var_data is None:
                        results_log.append({"block": block.get("name", b_id), "var": v_name, "success": 0, "errors": 1})
                        progress_bar.progress((i + 1) / len(selected))
                        continue
                    if block.get("block_type") == "characteristic":
                        res = batch_generate_for_characteristic(b_id, v_name, var_data, block)
                    else:
                        res = batch_generate_for_other(b_id, v_name, var_data, block)
                    results_log.append({
                        "block": block.get("name", b_id),
                        "var": v_name,
                        "success": res.get("success", 0),
                        "errors": res.get("errors", 0)
                    })
                    progress_bar.progress((i + 1) / len(selected))
                progress_bar.empty()
                status_text.empty()
                total_success = sum(r["success"] for r in results_log)
                total_errors = sum(r["errors"] for r in results_log)
                st.success(f"✅ Массовая генерация завершена. Успешно: {total_success}, ошибок: {total_errors}")
                with st.expander("Подробности"):
                    for log in results_log:
                        st.write(f"**{log['block']} / {log['var']}**: успех {log['success']}, ошибок {log['errors']}")
                st.rerun()

    # --- Индивидуальная генерация ---
    if "ai_overview_selected" in st.session_state:
        block_id, var_name = st.session_state.ai_overview_selected
        block = st.session_state.block_manager.get_block(block_id)
        if block is None or var_name not in block.get("variables_data", {}):
            st.error("Данные устарели, вернитесь к списку")
            del st.session_state.ai_overview_selected
            st.rerun()
        var_data = block["variables_data"][var_name]
        st.markdown("---")
        st.markdown(f"### Генерация для `{var_name}` (блок: **{block.get('name')}**)")
        if block.get("block_type") == "characteristic":
            show_ai_generation_for_characteristics(block_id, var_name, var_data, block)
        else:
            show_ai_generation_for_other_blocks(block_id, var_name, var_data, block)
        if st.button("← Назад к списку AI-переменных", key="back_to_ai_list"):
            del st.session_state.ai_overview_selected
            st.rerun()

    if "ai_view_selected" in st.session_state:
        block_id, var_name = st.session_state.ai_view_selected
        block = st.session_state.block_manager.get_block(block_id)
        if block is None or var_name not in block.get("variables_data", {}):
            st.error("Данные устарели, вернитесь к списку")
            del st.session_state.ai_view_selected
            st.rerun()
        st.markdown("---")
        st.markdown(f"### 📋 Все инструкции для `{var_name}` (блок: **{block.get('name')}**)")
        show_ai_instructions_full(block_id, var_name, block)
        if st.button("← Назад к списку AI-переменных"):
            del st.session_state.ai_view_selected
            st.rerun()
def show_edit_mode():
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Управление блоками",
        "✏️ Редактирование блока",
        "📊 Обзор переменных",          # было "🔧 Редактирование статических переменных"
        "🌀 Редактирование динамических переменных",
        "🤖 Управление AI‑переменными"
    ])

    with tab1:
        show_blocks_management()

    with tab2:
        show_block_editor()

    with tab3:
        show_variables_overview()

    with tab4:
        show_dynamic_variables_editor()
    with tab5:
        show_ai_variables_overview()


def show_dynamic_variables_editor():
    """Редактор динамических переменных"""

    # Инициализация менеджера динамических переменных
    if 'dynamic_var_manager' not in st.session_state:
        st.session_state.dynamic_var_manager = DynamicVariableManager()

    dynamic_vars = st.session_state.dynamic_var_manager.get_all_dynamic_vars()

    st.subheader("🌀 Редактирование динамических переменных")
    st.markdown("""
    **Динамические переменные** - это переменные, которые подставляются из различных источников:
    - 📁 **config** - из файла конфигурации
    - 📊 **data** - из загруженных данных
    - 🔄 **processing** - генерируются при обработке

    Эти переменные можно использовать в любом блоке!
    """)

    # Список динамических переменных
    with st.expander("📋 Список динамических переменных", expanded=True):
        if dynamic_vars:
            cols = st.columns(4)
            for idx, (var_name, var_data) in enumerate(dynamic_vars.items()):
                with cols[idx % 4]:
                    var_type = var_data.get("type", "dynamic")
                    source = var_data.get("source", "unknown")
                    source_icon = {
                        "config": "⚙️",
                        "data": "📊",
                        "processing": "🔄",
                        "unknown": "❓"
                    }.get(source, "❓")

                    st.markdown(f"""
                    <div style="
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 8px;
                        border: 1px solid #dee2e6;
                        margin-bottom: 10px;
                    ">
                        <div style="font-weight: bold; color: #495057;">{{{var_name}}}</div>
                        <div style="font-size: 0.8em; color: #6c757d; margin-top: 5px;">
                            {var_data.get('description', '')}
                        </div>
                        <div style="font-size: 0.7em; color: #adb5bd; margin-top: 5px;">
                            {source_icon} {source} • {len(var_data.get('values', []))} значений
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Нет динамических переменных")

    st.divider()

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        if st.button("📤 Экспорт в JSON", use_container_width=True):
            dynamic_vars = st.session_state.dynamic_var_manager.get_all_dynamic_vars()
            json_str = json.dumps(dynamic_vars, ensure_ascii=False, indent=2)
            st.download_button(
                label="Скачать JSON",
                data=json_str,
                file_name="dynamic_variables.json",
                mime="application/json",
                use_container_width=True
            )

    with col_exp2:
        uploaded_file = st.file_uploader("Импорт из JSON", type=['json'], key="dynamic_vars_import")
        if uploaded_file is not None:
            try:
                imported_vars = json.load(uploaded_file)
                if st.button("Импортировать", use_container_width=True):
                    st.session_state.dynamic_var_manager.dynamic_vars = imported_vars
                    if st.session_state.dynamic_var_manager.save_dynamic_variables():
                        st.success("✅ Динамические переменные импортированы!")
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Ошибка импорта: {e}")

    # Редактирование конкретной динамической переменной
    st.markdown("### ✏️ Редактирование динамической переменной")

    # Выбор переменной для редактирования
    var_options = list(dynamic_vars.keys())
    if var_options:
        selected_var = st.selectbox(
            "Выберите переменную для редактирования:",
            var_options,
            format_func=lambda x: f"{{{x}}} - {dynamic_vars[x].get('description', '')}"
        )

        if selected_var:
            var_data = dynamic_vars[selected_var]

            with st.form(key=f"edit_dynamic_var_{selected_var}"):
                st.write(f"**Редактирование:** `{{{selected_var}}}`")

                col1, col2 = st.columns(2)
                with col1:
                    description = st.text_input(
                        "Описание:",
                        value=var_data.get("description", "")
                    )

                with col2:
                    source = st.selectbox(
                        "Источник:",
                        ["config", "data", "processing", "unknown"],
                        index=["config", "data", "processing", "unknown"].index(
                            var_data.get("source", "unknown")
                        )
                    )

                # Значения переменной
                st.markdown("**Значения переменной (для source=config):**")
                st.caption("Для source=data или processing значения генерируются автоматически")

                current_values = var_data.get("values", [])
                values_text = "\n".join(current_values)

                new_values = st.text_area(
                    "Значения (каждое с новой строки):",
                    value=values_text,
                    height=150,
                    disabled=(source != "config")
                )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Сохранить изменения", use_container_width=True):
                        # Обновляем данные переменной
                        updated_data = {
                            "name": selected_var,
                            "description": description,
                            "type": "dynamic",
                            "source": source,
                            "values": [v.strip() for v in new_values.split("\n") if v.strip()]
                        }

                        if st.session_state.dynamic_var_manager.update_dynamic_variable(selected_var, updated_data):
                            st.success(f"✅ Динамическая переменная '{{{selected_var}}}' сохранена!")
                            st.rerun()
                        else:
                            st.error(f"❌ Ошибка сохранения")

                with col_btn2:
                    # Кнопка для добавления новой переменной
                    if st.form_submit_button("➕ Создать новую", type="secondary", use_container_width=True):
                        st.session_state.new_dynamic_var_name = ""
                        st.rerun()

        # Создание новой динамической переменной
        with st.expander("➕ Создать новую динамическую переменную", expanded=False):
            new_var_name = st.text_input(
                "Имя переменной (без фигурных скобок):",
                value=st.session_state.get("new_dynamic_var_name", "")
            )

            new_var_desc = st.text_input("Описание:")
            new_var_source = st.selectbox("Источник:", ["config", "data", "processing"])

            if new_var_source == "config":
                new_var_values = st.text_area("Значения (каждое с новой строки):", height=100)
            else:
                new_var_values = ""
                st.info(f"Для источника '{new_var_source}' значения будут генерироваться автоматически")

            if st.button("Создать", key="create_new_dynamic_var"):
                if new_var_name and not new_var_name.startswith("{") and not new_var_name.endswith("}"):
                    new_var_data = {
                        "name": new_var_name,
                        "description": new_var_desc or f"Описание для {new_var_name}",
                        "type": "dynamic",
                        "source": new_var_source,
                        "values": [v.strip() for v in new_var_values.split("\n") if v.strip()] if new_var_values else []
                    }

                    if st.session_state.dynamic_var_manager.update_dynamic_variable(new_var_name, new_var_data):
                        st.success(f"✅ Создана новая динамическая переменная '{{{new_var_name}}}'")
                        del st.session_state.new_dynamic_var_name
                        st.rerun()
                    else:
                        st.error("❌ Ошибка создания переменной")
                else:
                    st.error("❌ Введите корректное имя переменной")

    else:
        st.info("Сначала создайте динамические переменные")

        if st.button("🔄 Загрузить стандартные динамические переменные"):
            st.session_state.dynamic_var_manager.dynamic_vars = st.session_state.dynamic_var_manager.get_default_dynamic_vars()
            if st.session_state.dynamic_var_manager.save_dynamic_variables():
                st.success("✅ Загружены стандартные динамические переменные")
                st.rerun()

def show_variables_overview():
    """Отображает все переменные (статические и AI) с привязкой к блокам"""
    st.subheader("📊 Обзор всех переменных")

    blocks = st.session_state.block_manager.get_all_blocks()
    if not blocks:
        st.info("Нет созданных блоков")
        return

    # Собираем переменные
    all_vars = []
    for block_id, block in blocks.items():
        block_name = block.get("name", block_id)
        variables_data = block.get("variables_data", {})
        for var_name, var_data in variables_data.items():
            var_type = var_data.get("type", "static")
            if var_type in ["static", "ai"]:
                all_vars.append({
                    "block_id": block_id,
                    "block_name": block_name,
                    "var_name": var_name,
                    "type": var_type,
                    "values_count": len(var_data.get("values", [])),
                    "description": var_data.get("description", "")
                })

    if not all_vars:
        st.info("Нет статических или AI-переменных")
        return

    # Фильтры
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        type_filter = st.multiselect(
            "Тип переменной",
            options=["static", "ai"],
            default=["static", "ai"],
            format_func=lambda x: "Статическая" if x == "static" else "AI"
        )
    with col_f2:
        blocks_list = sorted(set(v["block_name"] for v in all_vars))
        block_filter = st.multiselect("Блок", options=blocks_list, default=[])

    filtered = [v for v in all_vars if v["type"] in type_filter]
    if block_filter:
        filtered = [v for v in filtered if v["block_name"] in block_filter]

    if filtered:
        st.markdown(f"**Найдено переменных: {len(filtered)}**")

        # Заголовки таблицы
        cols = st.columns([2, 2, 1, 1, 2, 2])
        cols[0].write("**Переменная**")
        cols[1].write("**Блок**")
        cols[2].write("**Тип**")
        cols[3].write("**Кол-во значений**")
        cols[4].write("**Описание**")
        cols[5].write("**Действия**")

        for var in filtered:
            row = st.columns([2, 2, 1, 1, 2, 2])
            row[0].write(f"`{var['var_name']}`")
            row[1].write(var['block_name'])
            row[2].write("📝" if var['type'] == "static" else "🤖")
            row[3].write(str(var['values_count']))
            row[4].caption(var['description'][:50] + ("..." if len(var['description']) > 50 else ""))
            with row[5]:
                if st.button("✏️", key=f"goto_{var['block_id']}_{var['var_name']}", help="Перейти к блоку"):
                    st.session_state.current_edit_block = var['block_id']
                    st.rerun()
    else:
        st.info("Нет переменных, соответствующих фильтрам")
def show_blocks_management():
    """Управление блоками: список, создание, удаление"""
    st.subheader("📋 Управление блоками")

    blocks = st.session_state.block_manager.get_all_blocks()

    if not blocks:
        st.info("Блоки не найдены. Создайте первый блок.")

    # Создание нового блока
    st.markdown("### ➕ Создать новый блок")

    col_create1, col_create2, col_create3, col_create4 = st.columns([2, 2, 1, 1])

    with col_create1:
        if blocks:
            base_block_options = ["(пустой блок)"] + list(blocks.keys())
            base_block = st.selectbox(
                "На основе блока:",
                base_block_options,
                format_func=lambda
                    x: "(пустой блок)" if x == "(пустой блок)" else f"{blocks[x].get('name', x)} ({blocks[x].get('block_type', 'other')})",
                key="new_block_base"
            )
        else:
            base_block = "(пустой блок)"

    with col_create2:
        block_type = st.selectbox(
            "Тип блока:",
            ["characteristic", "other"],
            format_func=lambda x: "Характеристика" if x == "characteristic" else "Другой блок",
            key="new_block_type"
        )

    with col_create3:
        # Для characteristic блоков выбираем подтип
        if block_type == "characteristic":
            characteristic_type = st.selectbox(
                "Тип характеристики:",
                ["regular", "unique"],
                format_func=lambda x: "Regular (обычная)" if x == "regular" else "Unique (уникальная)",
                key="new_char_type"
            )
        else:
            characteristic_type = None

    with col_create4:
        create_disabled = block_type == "characteristic" and characteristic_type is None
        if st.button("Создать", use_container_width=True, disabled=create_disabled):
            base_block_id = None if base_block == "(пустой блок)" else base_block

            new_block_id, new_block, variables_data = st.session_state.block_manager.create_new_block(base_block_id)

            # Устанавливаем тип блока
            new_block["block_type"] = block_type

            # Для characteristic блоков добавляем информацию о типе в название и настройки
            if block_type == "characteristic":
                if base_block == "(пустой блок)":
                    # Создаем новые шаблоны для regular и unique
                    if characteristic_type == "regular":
                        new_block.update({
                            "name": "Шаблон для Regular характеристики",
                            "description": "Шаблон для regular характеристик",
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
                                "добавлять_скобки_переменную": True,
                                "characteristic_type": "regular"
                            }
                        })
                    else:  # unique
                        new_block.update({
                            "name": "Шаблон для Unique характеристики",
                            "description": "Шаблон для unique характеристик",
                            "template": """Ты должен генерировать текст, полностью исключая определительные конструкции с тире и союзом 'что'.
{стиль_текста}.
Объем: {объем_характеристики}. 
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
                                "требование_тошноты"
                            ],
                            "settings": {
                                "маркер_позиция": "начало",
                                "формат_значения_regular": "[[значение]]",
                                "формат_значения_unique": "\"[значение]\"",
                                "добавлять_скобки_переменную": False,
                                "characteristic_type": "unique"
                            }
                        })
                else:
                    # При копировании сохраняем тип характеристики из базового блока
                    if "settings" in new_block and "characteristic_type" in new_block["settings"]:
                        # Уже есть тип
                        pass
                    else:
                        # Устанавливаем тип из выбранного
                        if "settings" not in new_block:
                            new_block["settings"] = {}
                        new_block["settings"]["characteristic_type"] = characteristic_type

                # Базовые переменные для characteristic блоков
                if base_block == "(пустой блок)":
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
                        }
                    }

                    # Добавляем скобки только для regular
                    if characteristic_type == "regular":
                        variables_data["скобки_характеристика"] = {
                            "name": "скобки_характеристика",
                            "description": "Указание про скобки для regular характеристик",
                            "values": [
                                "Значение характеристики заключено в двойные квадратные скобки",
                                "Значение в [[ ]] нужно использовать как есть",
                                "Обрати внимание: значение в [[ ]]"
                            ],
                            "type": "static"
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
        # Фильтрация блоков
        filter_type = st.selectbox(
            "Фильтр по типу:",
            ["Все", "characteristic", "other"],
            format_func=lambda x: "Все" if x == "Все" else ("Характеристика" if x == "characteristic" else "Другие блоки")
        )

        filtered_blocks = blocks
        if filter_type != "Все":
            filtered_blocks = {k: v for k, v in blocks.items() if v.get("block_type") == filter_type}

        for block_id, block in filtered_blocks.items():
            block_type = block.get("block_type", "other")
            block_type_display = "Характеристика" if block_type == "characteristic" else "Другой блок"

            # Для characteristic блоков показываем дополнительную информацию
            char_type_info = ""
            if block_type == "characteristic":
                char_type = block.get("settings", {}).get("characteristic_type", "regular")
                char_type_info = f" • {char_type.upper()}"

            col_list1, col_list2, col_list3, col_list4 = st.columns([3, 2, 1, 1])

            with col_list1:
                st.write(f"**{block.get('name', 'Без названия')}**")
                st.caption(f"ID: {block_id}{char_type_info}")
                if block.get('description'):
                    st.caption(
                        block.get('description')[:100] + "..." if len(block.get('description')) > 100 else block.get(
                            'description'))

            with col_list2:
                st.markdown(f'<span class="block-type-chip block-type-{block_type}">{block_type_display}</span>',
                            unsafe_allow_html=True)

            with col_list3:
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

        # Для characteristic блоков - выбор типа характеристики
        if block_type == "characteristic":
            char_type = st.selectbox(
                "Тип характеристики:",
                ["regular", "unique"],
                index=0 if selected_block.get("settings", {}).get("characteristic_type", "regular") == "regular" else 1,
                format_func=lambda x: "Regular (обычная)" if x == "regular" else "Unique (уникальная)"
            )

            # Информация о форматах значений
            st.info("""
            **Форматы значений:**
            - Regular характеристики: `[[значение]]`
            - Unique характеристики: `"[значение]"`
            """)

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
                    # Автоматически добавляем/убираем переменную скобки в зависимости от типа
                    variables_list = [v.strip() for v in new_vars_text.split("\n") if v.strip()]

                    if char_type == "regular":
                        # Для regular характеристик добавляем скобки_характеристика если еще нет
                        if "скобки_характеристика" not in variables_list:
                            variables_list.append("скобки_характеристика")
                    else:  # unique
                        # Для unique характеристик убираем скобки_характеристика если есть
                        if "скобки_характеристика" in variables_list:
                            variables_list.remove("скобки_характеристика")

                    selected_block["variables"] = variables_list

                    selected_block["settings"] = {
                        "маркер_позиция": "начало",  # фиксированное значение
                        "формат_значения_regular": "[[значение]]",  # фиксированное значение
                        "формат_значения_unique": "\"[значение]\"",  # фиксированное значение
                        "добавлять_скобки_переменную": (char_type == "regular"),  # автоматически
                        "characteristic_type": char_type
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
    # После формы редактирования блока добавляем управление статическими переменными
    st.markdown("---")
    st.subheader("📦 Переменные этого блока")

    # Получаем текущие переменные блока
    variables = selected_block.get("variables", [])
    variables_data = selected_block.get("variables_data", {})
    template = selected_block.get("template", "")

    # Определяем динамические переменные, доступные в системе
    dynamic_var_names = []
    if 'dynamic_var_manager' in st.session_state:
        dynamic_var_names = list(st.session_state.dynamic_var_manager.get_all_dynamic_vars().keys())

    # Разделяем переменные по типам
    static_vars = []
    ai_vars = []
    dynamic_vars = []

    for var_name in variables:
        var_type = variables_data.get(var_name, {}).get("type", "static")
        if var_type == "ai":
            ai_vars.append(var_name)
        elif var_name in dynamic_var_names:
            dynamic_vars.append(var_name)
        else:
            static_vars.append(var_name)

    # Добавляем переменные, которые есть только в шаблоне, но не в списке variables
    template_vars = set(re.findall(r'\{([^}]+)\}', template))
    for var_name in template_vars:
        if var_name not in variables:
            # Автоматически добавляем в список, но не создаём данные
            if var_name not in variables:
                variables.append(var_name)
                # Определяем предполагаемый тип
                if var_name in dynamic_var_names:
                    dynamic_vars.append(var_name)
                else:
                    # По умолчанию считаем статической, но данные не создаём
                    static_vars.append(var_name)
                    # Можно создать пустую запись, но лучше оставить на усмотрение пользователя
                    # Для простоты пока не создаём
                    pass

    # Создаём табы для разных типов переменных
    tab_static, tab_ai, tab_dynamic = st.tabs([
        f"📝 Статические ({len(static_vars)})",
        f"🤖 AI ({len(ai_vars)})",
        f"🌀 Динамические ({len(dynamic_vars)})"
    ])

    # --- Вкладка статических переменных ---
    with tab_static:
        # Кнопка добавления новой статической переменной
        with st.expander("➕ Добавить новую статическую переменную", expanded=False):
            new_static_name = st.text_input(
                "Имя переменной (без фигурных скобок)",
                key=f"new_static_{selected_block_id}"
            )
            col_new1, col_new2 = st.columns([3, 1])
            with col_new1:
                if st.button("Создать статическую", key=f"create_static_{selected_block_id}") and new_static_name:
                    if new_static_name not in variables:
                        variables.append(new_static_name)
                        variables_data[new_static_name] = {
                            "name": new_static_name,
                            "description": f"Статическая переменная {new_static_name}",
                            "type": "static",
                            "values": ["Пример значения 1", "Пример значения 2"]
                        }
                        selected_block["variables"] = variables
                        selected_block["variables_data"] = variables_data
                        if st.session_state.block_manager.save_block(selected_block, variables_data):
                            st.success(f"Переменная '{new_static_name}' создана")
                            st.rerun()
                    else:
                        st.error("Переменная с таким именем уже существует")

        # Список статических переменных для редактирования
        if static_vars:
            for var_name in static_vars:
                var_data = variables_data.get(var_name, {
                    "name": var_name,
                    "description": f"Статическая переменная {var_name}",
                    "type": "static",
                    "values": []
                })
                with st.expander(f"📝 {var_name}", expanded=False):
                    with st.form(key=f"edit_static_{selected_block_id}_{var_name}"):
                        desc = st.text_input("Описание", value=var_data.get("description", ""))
                        values_text = "\n".join(var_data.get("values", []))
                        new_values = st.text_area("Значения (каждое с новой строки)", value=values_text, height=150)

                        col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
                        with col_act1:
                            if st.form_submit_button("💾 Сохранить"):
                                var_data["description"] = desc
                                var_data["values"] = [v.strip() for v in new_values.split("\n") if v.strip()]
                                variables_data[var_name] = var_data
                                selected_block["variables_data"] = variables_data
                                if st.session_state.block_manager.save_block(selected_block, variables_data):
                                    st.success(f"Переменная '{var_name}' сохранена")
                                    st.rerun()
                        with col_act2:
                            if st.form_submit_button("🗑️ Удалить"):
                                if st.session_state.get(f"confirm_del_static_{selected_block_id}_{var_name}", False):
                                    variables.remove(var_name)
                                    del variables_data[var_name]
                                    selected_block["variables"] = variables
                                    selected_block["variables_data"] = variables_data
                                    if st.session_state.block_manager.save_block(selected_block, variables_data):
                                        st.success(f"Переменная '{var_name}' удалена")
                                        st.rerun()
                                else:
                                    st.session_state[f"confirm_del_static_{selected_block_id}_{var_name}"] = True
                                    st.warning("Нажмите 'Удалить' ещё раз для подтверждения")
                        with col_act3:
                            # Кнопка преобразования в AI
                            if st.form_submit_button("🤖 Преобразовать в AI"):
                                var_data["type"] = "ai"
                                var_data["ai_prompt"] = "Сгенерируй текст для {характеристика}..."
                                var_data["ai_num_variants"] = 3
                                var_data["ai_provider"] = "openai"
                                variables_data[var_name] = var_data
                                selected_block["variables_data"] = variables_data
                                if st.session_state.block_manager.save_block(selected_block, variables_data):
                                    st.success(f"Переменная '{var_name}' теперь AI")
                                    st.rerun()
        else:
            st.info("Нет статических переменных")

    # --- Вкладка AI переменных ---
    with tab_ai:
        # Кнопка добавления новой AI переменной
        with st.expander("➕ Добавить новую AI переменную", expanded=False):
            new_ai_name = st.text_input(
                "Имя переменной (без фигурных скобок)",
                key=f"new_ai_{selected_block_id}"
            )
            if st.button("Создать AI", key=f"create_ai_{selected_block_id}") and new_ai_name:
                if new_ai_name not in variables:
                    variables.append(new_ai_name)
                    # Базовый промпт в зависимости от типа блока
                    if block_type == "characteristic":
                        base_prompt = """Сгенерируй перечень аналитических тезисов для характеристики {характеристика} в категории {категория}."""
                    else:
                        base_prompt = "Сгенерируй контент для категории {контекст_категория}."
                    variables_data[new_ai_name] = {
                        "name": new_ai_name,
                        "description": f"AI переменная {new_ai_name}",
                        "type": "ai",
                        "ai_prompt": base_prompt,
                        "ai_num_variants": 3,
                        "ai_provider": "openai",
                        "values": []
                    }
                    selected_block["variables"] = variables
                    selected_block["variables_data"] = variables_data
                    if st.session_state.block_manager.save_block(selected_block, variables_data):
                        st.success(f"AI переменная '{new_ai_name}' создана")
                        st.rerun()
                else:
                    st.error("Переменная с таким именем уже существует")

        # Список AI переменных для редактирования
        if ai_vars:
            for var_name in ai_vars:
                var_data = variables_data.get(var_name, {
                    "name": var_name,
                    "description": f"AI переменная {var_name}",
                    "type": "ai",
                    "ai_prompt": "",
                    "ai_num_variants": 3,
                    "ai_provider": "openai",
                    "values": []
                })
                with st.expander(f"🤖 {var_name}", expanded=False):
                    with st.form(key=f"edit_ai_{selected_block_id}_{var_name}"):
                        desc = st.text_input("Описание", value=var_data.get("description", ""))
                        provider = st.selectbox(
                            "Провайдер",
                            ["openai", "deepseek"],
                            index=0 if var_data.get("ai_provider", "openai") == "openai" else 1
                        )
                        num_variants = st.number_input(
                            "Количество вариантов",
                            min_value=1, max_value=10,
                            value=var_data.get("ai_num_variants", 3)
                        )
                        prompt = st.text_area(
                            "Промпт для AI",
                            value=var_data.get("ai_prompt", ""),
                            height=150
                        )

                        col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
                        with col_act1:
                            if st.form_submit_button("💾 Сохранить настройки"):
                                var_data.update({
                                    "description": desc,
                                    "ai_provider": provider,
                                    "ai_num_variants": num_variants,
                                    "ai_prompt": prompt
                                })
                                variables_data[var_name] = var_data
                                selected_block["variables_data"] = variables_data
                                if st.session_state.block_manager.save_block(selected_block, variables_data):
                                    st.success(f"AI переменная '{var_name}' сохранена")
                                    st.rerun()
                        with col_act2:
                            if st.form_submit_button("🚀 Генерировать"):
                                # Сохраняем и переходим к генерации
                                var_data.update({
                                    "description": desc,
                                    "ai_provider": provider,
                                    "ai_num_variants": num_variants,
                                    "ai_prompt": prompt
                                })
                                variables_data[var_name] = var_data
                                selected_block["variables_data"] = variables_data
                                st.session_state.block_manager.save_block(selected_block, variables_data)
                                st.session_state.current_ai_var_for_generation = var_name
                                st.session_state.current_block_for_ai = selected_block_id
                                st.rerun()
                        with col_act3:
                            if st.form_submit_button("🗑️ Удалить"):
                                if st.session_state.get(f"confirm_del_ai_{selected_block_id}_{var_name}", False):
                                    variables.remove(var_name)
                                    del variables_data[var_name]
                                    selected_block["variables"] = variables
                                    selected_block["variables_data"] = variables_data
                                    if st.session_state.block_manager.save_block(selected_block, variables_data):
                                        st.success(f"AI переменная '{var_name}' удалена")
                                        st.rerun()
                                else:
                                    st.session_state[f"confirm_del_ai_{selected_block_id}_{var_name}"] = True
                                    st.warning("Нажмите 'Удалить' ещё раз для подтверждения")

                    # Если выбрана генерация для этой переменной
                    if (st.session_state.get("current_ai_var_for_generation") == var_name and
                            st.session_state.get("current_block_for_ai") == selected_block_id):
                        st.markdown("---")
                        if block_type == "characteristic":
                            show_ai_generation_for_characteristics(selected_block_id, var_name, var_data,
                                                                   selected_block)
                        else:
                            show_ai_generation_for_other_blocks(selected_block_id, var_name, var_data, selected_block)
                        if st.button("❌ Отменить генерацию", key=f"cancel_gen_ai_{var_name}"):
                            del st.session_state.current_ai_var_for_generation
                            del st.session_state.current_block_for_ai
                            st.rerun()
        else:
            st.info("Нет AI переменных")

    # --- Вкладка динамических переменных ---
    with tab_dynamic:
        if dynamic_vars:
            st.info("Динамические переменные настраиваются во вкладке «🌀 Редактирование динамических переменных».")
            for var_name in dynamic_vars:
                var_info = st.session_state.dynamic_var_manager.get_dynamic_variable(var_name)
                with st.expander(f"🌀 {var_name}", expanded=False):
                    if var_info:
                        st.write(f"**Описание:** {var_info.get('description', '')}")
                        st.write(f"**Источник:** {var_info.get('source', 'unknown')}")
                        if var_info.get('source') == 'config':
                            values = var_info.get('values', [])
                            st.write(f"**Количество значений:** {len(values)}")
                            if values:
                                st.write("**Примеры:**")
                                for val in values[:3]:
                                    st.write(f"- {val}")
                    else:
                        st.write("Информация о переменной не найдена")
        else:
            st.info(
                "Динамические переменные не используются в этом блоке. Чтобы добавить, используйте `{имя}` в шаблоне и создайте переменную во вкладке «🌀 Редактирование динамических переменных».")

    # Информация о переменных блока
    with st.expander("📊 Статистика по переменным", expanded=False):
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Всего переменных", len(variables))
        with col_stat2:
            st.metric("Статических", len(static_vars))
        with col_stat3:
            st.metric("AI", len(ai_vars))
        if dynamic_vars:
            st.metric("Динамических", len(dynamic_vars))


# Заменить функцию show_ai_generation_for_characteristics на новую версию:
def show_ai_generation_for_characteristics(block_id, var_name, var_data, block):
    """Показывает интерфейс генерации AI для characteristic блоков с отображением промпта и ответа"""

    # Проверяем наличие данных из фазы 2
    phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
    category = phase2_data.get('category', '')
    characteristics = st.session_state.get('loaded_data', {}).get('characteristics', [])

    if not category:
        st.error("❌ Нет данных о категории. Загрузите данные в фазу 2.")
        return

    st.success(f"✅ Категория: **{category}**")
    st.info(f"📊 Найдено характеристик: **{len(characteristics)}**")

    # Определяем тип характеристики (regular/unique)
    char_type = block.get("settings", {}).get("characteristic_type", "regular")

    # Показываем характеристики для генерации
    with st.expander("📋 Характеристики для генерации", expanded=True):
        char_selection = {}

        for char in characteristics:
            char_id = char.get('char_id', '')
            char_name = char.get('char_name', 'Без названия')
            is_unique = char.get('is_unique', False)
            values_count = len(char.get('values', []))

            # Фильтруем по типу, если нужно
            if char_type == "regular" and is_unique:
                continue  # Пропускаем unique характеристики для regular блоков
            elif char_type == "unique" and not is_unique:
                continue  # Пропускаем regular характеристики для unique блоков

            col_char1, col_char2, col_char3, col_char4 = st.columns([3, 1, 1, 1])
            with col_char1:
                st.write(f"**{char_name}**")
                st.caption(f"ID: {char_id}")
            with col_char2:
                st.write(f"**{values_count}**")
                st.caption("значений")
            with col_char3:
                st.write(f"**{'Unique' if is_unique else 'Regular'}**")
            with col_char4:
                char_selection[char_id] = st.checkbox(
                    "Выбрать",
                    value=True,
                    key=f"select_char_{block_id}_{var_name}_{char_id}"
                )

        if not char_selection:
            st.warning(f"Нет характеристик типа '{char_type}' для генерации")
            return

        st.divider()
        selected_count = sum(char_selection.values())
        st.write(f"**Выбрано:** {selected_count} характеристик")

    # Проверка API ключа
    if 'ai_config_manager' not in st.session_state:
        st.warning("⚠️ Менеджер AI не инициализирован")
        if st.button("🔄 Инициализировать AI", key=f"init_ai_{block_id}_{var_name}"):
            init_ai_managers()
            st.rerun()
        return

    provider = var_data.get("ai_provider", "openai")
    provider_config = st.session_state.ai_config_manager.get_provider_config(provider)

    if not provider_config.get("api_key"):
        st.error(f"❌ API ключ для провайдера '{provider}' не настроен!")

        if st.button("⚙️ Настроить API ключ", use_container_width=True, key=f"setup_api_{block_id}_{var_name}"):
            st.session_state.show_ai_config = True
            st.rerun()
        return

    # Кнопка запуска генерации
    if st.button("🚀 Запустить генерацию AI-инструкций", type="primary",
                 use_container_width=True, key=f"run_gen_{block_id}_{var_name}"):

        with st.spinner("Генерация AI-инструкций..."):
            # Инициализируем менеджеры если нужно
            init_ai_managers()

            # Фильтруем выбранные характеристики
            selected_chars = [c for c in characteristics if
                              char_selection.get(c.get('char_id', ''))]

            # Список для хранения всех результатов с промптами и ответами
            all_generation_results = []

            progress_bar = st.progress(0)

            for idx, char in enumerate(selected_chars):
                char_id = char.get('char_id', '')
                char_name = char.get('char_name', '')
                is_unique = char.get('is_unique', False)
                values = char.get('values', [])

                # Обновляем прогресс
                progress = (idx + 1) / len(selected_chars)
                progress_bar.progress(progress)

                if is_unique:
                    # Для unique характеристик генерируем для каждого значения
                    for value_item in values:
                        value = value_item.get('value', '')

                        context = {
                            "категория": category,
                            "характеристика": char_name,
                            "значение": value,
                            "тип": "unique",
                            "block_id": block_id,
                            "var_name": var_name
                        }

                        # Формируем финальный промпт с подстановкой контекста
                        final_prompt = var_data.get("ai_prompt", "")
                        for key, val in context.items():
                            placeholder = f"{{{key}}}"
                            final_prompt = final_prompt.replace(placeholder, str(val))

                        # Генерируем инструкции с возвратом полного ответа
                        results = st.session_state.ai_generator.generate_instruction(
                            var_data.get("ai_prompt", ""),
                            context,
                            provider=provider,
                            num_variants=1,
                            return_full_response=True
                        )

                        if results and results[0]["success"]:
                            instruction = results[0]["text"]
                            full_response = results[0].get("full_response", {})

                            # Сохраняем результат с промптом и ответом
                            all_generation_results.append({
                                "характеристика": char_name,
                                "значение": value,
                                "тип": "unique",
                                "промпт": final_prompt,
                                "ответ": instruction,
                                "полный_ответ": full_response,
                                "результат": results[0]
                            })

                            # Сохраняем инструкцию
                            st.session_state.ai_instruction_manager.save_instruction(
                                block_id,
                                var_name,
                                [instruction],
                                context,
                                {
                                    "provider": provider,
                                    "char_id": char_id,
                                    "char_name": char_name,
                                    "value": value
                                }
                            )
                        else:
                            error_msg = results[0].get('error', 'Неизвестная ошибка') if results else 'Нет ответа'
                            all_generation_results.append({
                                "характеристика": char_name,
                                "значение": value,
                                "тип": "unique",
                                "промпт": final_prompt,
                                "ошибка": error_msg
                            })
                else:
                    # Для regular характеристик генерируем общую инструкцию
                    context = {
                        "категория": category,
                        "характеристика": char_name,
                        "тип": "regular",
                        "block_id": block_id,
                        "var_name": var_name
                    }

                    # Формируем финальный промпт с подстановкой контекста
                    final_prompt = var_data.get("ai_prompt", "")
                    for key, val in context.items():
                        placeholder = f"{{{key}}}"
                        final_prompt = final_prompt.replace(placeholder, str(val))

                    # Генерируем несколько вариантов с возвратом полного ответа
                    results = st.session_state.ai_generator.generate_instruction(
                        var_data.get("ai_prompt", ""),
                        context,
                        provider=provider,
                        num_variants=var_data.get("ai_num_variants", 1),
                        return_full_response=True
                    )

                    successful_results = []
                    for i, result in enumerate(results):
                        if result.get("success"):
                            successful_results.append(result["text"])

                            all_generation_results.append({
                                "характеристика": char_name,
                                "тип": "regular",
                                "вариант": i + 1,
                                "промпт": final_prompt,
                                "ответ": result["text"],
                                "полный_ответ": result.get("full_response", {}),
                                "результат": result
                            })
                        else:
                            all_generation_results.append({
                                "характеристика": char_name,
                                "тип": "regular",
                                "вариант": i + 1,
                                "промпт": final_prompt,
                                "ошибка": result.get('error', 'Неизвестная ошибка')
                            })

                    if successful_results:
                        # Сохраняем инструкции
                        st.session_state.ai_instruction_manager.save_instruction(
                            block_id,
                            var_name,
                            successful_results,
                            context,
                            {
                                "provider": provider,
                                "char_id": char_id,
                                "char_name": char_name
                            }
                        )

            progress_bar.empty()

            # Отображаем все результаты с промптами и ответами
            st.markdown("### 📊 Результаты генерации с промптами и ответами")

            # Счетчики
            success_count = sum(1 for r in all_generation_results if "ответ" in r)
            error_count = sum(1 for r in all_generation_results if "ошибка" in r)

            st.metric("✅ Успешно", success_count)
            st.metric("❌ Ошибок", error_count)

            # Показываем все результаты в аккордеоне
            for i, result in enumerate(all_generation_results):
                if "ошибка" in result:
                    with st.expander(f"❌ {i + 1}. {result['характеристика']} - ОШИБКА", expanded=False):
                        st.error(f"**Ошибка:** {result['ошибка']}")
                        st.markdown("**Отправленный промпт:**")
                        st.code(result['промпт'], language="markdown")
                else:
                    title = f"{i + 1}. {result['характеристика']}"
                    if "значение" in result:
                        title += f" = {result['значение']}"
                    if "вариант" in result:
                        title += f" (вариант {result['вариант']})"

                    with st.expander(f"✅ {title}", expanded=False):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Отправленный промпт:**")
                            st.code(result['промпт'], language="markdown")

                        with col2:
                            st.markdown("**Ответ ИИ:**")
                            st.code(result['ответ'], language="markdown")

                        # Показываем полный ответ API если есть
                        if "полный_ответ" in result and result["полный_ответ"]:
                            with st.expander("📄 Полный ответ API", expanded=False):
                                st.json(result["полный_ответ"])

                        # Редактирование ответа
                        st.markdown("**✏️ Редактировать ответ:**")
                        edited_response = st.text_area(
                            f"Редактирование ответа {i + 1}:",
                            value=result['ответ'],
                            height=200,
                            key=f"edit_response_{block_id}_{var_name}_{i}"
                        )

                        if st.button(f"💾 Сохранить изменения", key=f"save_edit_{block_id}_{var_name}_{i}"):
                            # Обновляем сохраненную инструкцию
                            if "значение" in result:  # unique характеристика
                                # Нужно найти и обновить соответствующую инструкцию
                                context_for_update = {
                                    "категория": category,
                                    "характеристика": result['характеристика'],
                                    "значение": result.get('значение', ''),
                                    "тип": result['тип']
                                }
                                # Находим хэш контекста
                                context_hash = st.session_state.ai_instruction_manager.find_matching_context_hash(
                                    block_id, var_name, context_for_update
                                )
                                if context_hash:
                                    # Обновляем значение
                                    st.session_state.ai_instruction_manager.update_full_instruction(
                                        block_id, var_name, context_hash, 0, edited_response
                                    )
                                    st.success("✅ Ответ обновлен!")
                                    st.rerun()
                            else:  # regular характеристика
                                # Для regular характеристик нужно обновить соответствующий вариант
                                context_for_update = {
                                    "категория": category,
                                    "характеристика": result['характеристика'],
                                    "тип": result['тип']
                                }
                                context_hash = st.session_state.ai_instruction_manager.find_matching_context_hash(
                                    block_id, var_name, context_for_update
                                )
                                if context_hash:
                                    variant_idx = result.get('вариант', 1) - 1
                                    st.session_state.ai_instruction_manager.update_full_instruction(
                                        block_id, var_name, context_hash, variant_idx, edited_response
                                    )
                                    st.success("✅ Ответ обновлен!")
                                    st.rerun()

            if success_count > 0:
                st.success(f"✅ Сгенерировано {success_count} AI-инструкций!")
            else:
                st.error("❌ Не удалось сгенерировать ни одну инструкцию")


def show_ai_generation_for_other_blocks(block_id, var_name, var_data, block):
    """Показывает интерфейс генерации AI для других типов блоков с отображением промпта и ответа"""

    st.info("""
    **Генерация для общих блоков**    """)

    # Проверяем наличие данных из фазы 2
    phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
    category = phase2_data.get('category', '')

    if not category:
        st.error("❌ Нет данных о категории. Загрузите данные в фазу 2.")
        return

    st.success(f"✅ Категория для генерации: **{category}**")

    # Количество вариантов
    num_variants = st.number_input(
        "Количество вариантов для генерации:",
        min_value=1,
        max_value=10,
        value=var_data.get("ai_num_variants", 3),
        key=f"num_variants_{block_id}_{var_name}"
    )

    # Проверка API ключа
    if 'ai_config_manager' not in st.session_state:
        st.warning("⚠️ Менеджер AI не инициализирован")
        if st.button("🔄 Инициализировать AI", key=f"init_ai_other_{block_id}_{var_name}"):
            init_ai_managers()
            st.rerun()
        return

    provider = var_data.get("ai_provider", "openai")
    provider_config = st.session_state.ai_config_manager.get_provider_config(provider)

    if not provider_config.get("api_key"):
        st.error(f"❌ API ключ для провайдера '{provider}' не настроен!")
        if st.button("⚙️ Настроить API ключ", use_container_width=True, key=f"setup_api_other_{block_id}_{var_name}"):
            st.session_state.show_ai_config = True
            st.rerun()
        return

    # УБРАЛИ тестовую генерацию - оставляем только основную

    # Кнопка основной генерации
    if st.button("🚀 Запустить генерацию", type="primary",
                 use_container_width=True, key=f"main_gen_{block_id}_{var_name}"):

        with st.spinner(f"Генерация {num_variants} вариантов..."):
            init_ai_managers()

            # Контекст для блока "other" - только категория
            context = {
                "категория": category,
                "тип": "other",
                "block_id": block_id,
                "var_name": var_name
            }

            # Формируем финальный промпт с подстановкой контекста
            final_prompt = var_data.get("ai_prompt", "")
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                final_prompt = final_prompt.replace(placeholder, str(value))

            # Генерируем инструкции с возвратом полного ответа
            results = st.session_state.ai_generator.generate_instruction(
                var_data.get("ai_prompt", ""),
                context,
                provider=provider,
                num_variants=num_variants,
                return_full_response=True
            )

            # Отображаем все результаты
            st.markdown("### 📊 Результаты генерации")

            success_count = 0
            error_count = 0

            for i, result in enumerate(results):
                if result.get("success"):
                    success_count += 1

                    with st.expander(f"✅ Вариант {i + 1} (успешно)", expanded=False):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Отправленный промпт:**")
                            st.code(final_prompt, language="markdown")

                        with col2:
                            st.markdown("**Ответ ИИ:**")
                            st.code(result["text"], language="markdown")

                        # Показываем полный ответ API если есть
                        if "full_response" in result and result["full_response"]:
                            with st.expander("📄 Полный ответ API", expanded=False):
                                st.json(result["full_response"])

                        # Редактирование ответа
                        st.markdown("**✏️ Редактировать ответ:**")
                        edited_response = st.text_area(
                            f"Редактирование варианта {i + 1}:",
                            value=result["text"],
                            height=200,
                            key=f"edit_other_{block_id}_{var_name}_{i}"
                        )

                        if st.button(f"💾 Сохранить изменения", key=f"save_edit_other_{block_id}_{var_name}_{i}"):
                            # Сохраняем отредактированный вариант
                            successful_results = [r["text"] for r in results if r.get("success")]
                            # Заменяем соответствующий результат
                            successful_results[i] = edited_response

                            # Сохраняем инструкции с контекстом блока
                            st.session_state.ai_instruction_manager.save_instruction(
                                block_id,
                                var_name,
                                successful_results,
                                context,
                                {
                                    "provider": provider,
                                    "block_type": "other",
                                    "num_variants": num_variants
                                }
                            )

                            st.success("✅ Ответ обновлен!")
                            st.rerun()
                else:
                    error_count += 1
                    with st.expander(f"❌ Вариант {i + 1} (ошибка)", expanded=False):
                        st.error(f"**Ошибка:** {result.get('error', 'Неизвестная ошибка')}")
                        st.markdown("**Отправленный промпт:**")
                        st.code(final_prompt, language="markdown")

            # Статистика
            st.metric("✅ Успешно", success_count)
            st.metric("❌ Ошибок", error_count)

            successful_results = [r["text"] for r in results if r.get("success")]

            if successful_results:
                # Сохраняем инструкции с контекстом блока
                st.session_state.ai_instruction_manager.save_instruction(
                    block_id,
                    var_name,
                    successful_results,
                    context,
                    {
                        "provider": provider,
                        "block_type": "other",
                        "num_variants": num_variants
                    }
                )

                st.success(f"✅ Сгенерировано {len(successful_results)} вариантов!")
            else:
                st.error("❌ Не удалось сгенерировать ни одного варианта")

def show_variables_editor():
    """Редактор переменных с поддержкой AI"""

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

    # Добавляем табы для разных типов переменных
    tab_static, tab_ai, tab_dynamic = st.tabs(["📝 Статические", "🤖 AI", "🌀 Динамические"])

    with tab_static:
        # Статические переменные
        static_vars = [v for v in variables if variables_data.get(v, {}).get("type", "static") == "static"]

        if not static_vars:
            st.info("Нет статических переменных. Создайте новую переменную или используйте AI/динамические переменные.")

            # Кнопка создания новой статической переменной
            new_static_var_name = st.text_input("Название новой статической переменной:")
            if st.button("➕ Создать статическую переменную") and new_static_var_name:
                # Добавляем переменную в список
                variables.append(new_static_var_name)
                variables_data[new_static_var_name] = {
                    "name": new_static_var_name,
                    "description": f"Статическаяsss переменная: {new_static_var_name}",
                    "type": "static",
                    "values": [f"Значение для {new_static_var_name} 1", f"Значение для {new_static_var_name} 2"]
                }

                # Сохраняем блок
                selected_block["variables"] = variables
                selected_block["variables_data"] = variables_data
                st.session_state.block_manager.save_block(selected_block, variables_data)
                st.success(f"Создана статическая переменная '{new_static_var_name}'")
                st.rerun()
        else:
            selected_static_var = st.selectbox(
                "Выберите статическую переменную:",
                static_vars,
                key="var_selector_static"
            )

            if selected_static_var:
                var_data = variables_data.get(selected_static_var, {
                    "name": selected_static_var,
                    "description": f"Описание для {selected_static_var}",
                    "type": "static",
                    "values": ["Пример значения 1", "Пример значения 2"]
                })

                # Редактирование статической переменной
                with st.form(key=f"edit_static_var_form_{selected_static_var}"):
                    st.write(f"**Статическая переменная:** `{selected_static_var}`")

                    description = st.text_input(
                        "Описание переменной:",
                        value=var_data.get("description", "")
                    )

                    # Значения переменной
                    st.markdown("**Значения переменной:**")
                    current_values = var_data.get("values", [])
                    values_text = "\n".join(current_values)

                    new_values = st.text_area(
                        "Значения (каждое с новой строки):",
                        value=values_text,
                        height=200,
                        key=f"static_values_{selected_static_var}"
                    )

                    col_save1, col_save2 = st.columns(2)
                    with col_save1:
                        if st.form_submit_button("💾 Сохранить переменную", use_container_width=True):
                            # Обновляем данные переменной
                            variables_data[selected_static_var] = {
                                "name": selected_static_var,
                                "description": description,
                                "type": "static",
                                "values": [v.strip() for v in new_values.split("\n") if v.strip()]
                            }

                            # Сохраняем в блок
                            selected_block["variables_data"] = variables_data
                            if st.session_state.block_manager.save_block(selected_block, variables_data):
                                st.success(f"✅ Переменная '{selected_static_var}' сохранена!")
                                st.rerun()
                            else:
                                st.error(f"❌ Ошибка сохранения переменной")

                    with col_save2:
                        if st.form_submit_button("🗑️ Удалить переменную", type="secondary", use_container_width=True):
                            # Удаляем из списка переменных блока
                            if selected_static_var in variables:
                                variables.remove(selected_static_var)

                            # Удаляем из variables_data
                            if selected_static_var in variables_data:
                                del variables_data[selected_static_var]

                            # Сохраняем блок
                            selected_block["variables"] = variables
                            selected_block["variables_data"] = variables_data
                            if st.session_state.block_manager.save_block(selected_block, variables_data):
                                st.success(f"✅ Переменная '{selected_static_var}' удалена!")
                                st.rerun()

    # В функции show_variables_editor, в разделе AI (таб "🤖 AI"):

    with tab_ai:
        # AI переменные
        ai_vars = [v for v in variables if variables_data.get(v, {}).get("type") == "ai"]

        # Кнопка создания новой AI переменной (всегда видна)
        with st.expander("➕ Создать новую AI переменную", expanded=False):
            col_new1, col_new2 = st.columns([3, 1])
            with col_new1:
                new_ai_var_name = st.text_input(
                    "Название новой AI переменной:",
                    key="new_ai_var_name_input"
                )

            with col_new2:
                if st.button("➕ Создать", use_container_width=True, key="create_new_ai_var_btn") and new_ai_var_name:
                    # Проверяем, что переменная не существует
                    if new_ai_var_name in variables:
                        st.error(f"Переменная '{new_ai_var_name}' уже существует!")
                    else:
                        # Добавляем переменную в список
                        variables.append(new_ai_var_name)

                        # Базовый промпт для AI переменной (зависит от типа блока)
                        base_ai_prompt = ""
                        if selected_block.get("block_type") == "characteristic":
                            char_type = selected_block.get("settings", {}).get("characteristic_type", "regular")
                            if char_type == "regular":
                                base_ai_prompt = """Сгенерируй линейный перечень (8-12 пунктов) обобщённых аналитических тезисов-вопросов, разделённых “;”, для глубокого инженерно-технического анализа заданной ХАРАКТЕРИСТИКИ в рамках указанной КАТЕГОРИИ продукции.

    Категория: {категория}
    Характеристика: {характеристика}

    Формат вывода:
    - Требуется: Строго один абзац, где пункты разделены только точкой с запятой (;). Не используй маркеры списка (цифры, точки, тире), не разбивай на отдельные строки. Каждый пункт должен начинаться с глагола-запроса в повелительном наклонении.
    - Пример формата: Опиши...; укажи...; поясни...; объясни...; (и так далее).

    Каждый тезис должен:
    - Начинаться с глагола-запроса (опиши, укажи, поясни, объясни, покажи, расскажи, оцени, сравни, определи).
    - Содержать общие формулировки, на место которых потом можно будет подставить конкретное значение характеристики. Использовать местоимения и выражения типа 'данная характеристика', 'этот параметр', 'выбранное значение'.
    - Фокусироваться на практическом влиянии: на применение, монтаж, эксплуатацию, надёжность, стоимость и безопасность в рамках указанной категории.
    - Быть строго техническим и нейтральным, без упоминания конкретных марок, типоразмеров, ГОСТов или торговых названий."""
                            else:  # unique
                                base_ai_prompt = """Сгенерируй техническое описание для конкретного значения характеристики в рамках указанной категории.

    Категория: {категория}
    Характеристика: {характеристика}
    Значение: {значение}

    Требования:
    1. Сфокусируйся на конкретном значении характеристики
    2. Объясни практическую значимость этого значения
    3. Сравни с другими возможными значениями (если уместно)
    4. Укажи преимущества и особенности этого конкретного значения
    5. Будь технически точным, но понятным"""
                        else:
                            # Для других типов блоков
                            base_ai_prompt = """Сгенерируй контент на основе предоставленного контекста.

    Контекст:
    {контекст_категория}

    Требования:
    1. Будь информативным и полезным
    2. Используй технический, но понятный язык
    3. Избегай маркетинговых клише
    4. Сфокусируйся на практической пользе"""

                        variables_data[new_ai_var_name] = {
                            "name": new_ai_var_name,
                            "description": f"AI переменная: {new_ai_var_name}",
                            "type": "ai",
                            "ai_prompt": base_ai_prompt,
                            "ai_num_variants": 3,
                            "ai_provider": "openai",
                            "ai_context_type": selected_block.get("block_type", "other"),
                            "values": []
                        }

                        # Сохраняем блок
                        selected_block["variables"] = variables
                        selected_block["variables_data"] = variables_data
                        st.session_state.block_manager.save_block(selected_block, variables_data)
                        st.success(f"Создана AI переменная '{new_ai_var_name}'")
                        st.rerun()

        # Редактирование существующих AI переменных
        if ai_vars:
            st.markdown("### ✏️ Редактирование AI переменных")

            # Создаем табы для каждой AI переменной
            ai_tabs = st.tabs([f"🤖 {var}" for var in ai_vars])

            for tab_idx, ai_var in enumerate(ai_vars):
                with ai_tabs[tab_idx]:
                    var_data = variables_data.get(ai_var, {
                        "name": ai_var,
                        "description": f"Описание для {ai_var}",
                        "type": "ai",
                        "ai_prompt": "",
                        "ai_num_variants": 3,
                        "ai_provider": "openai",
                        "ai_context_type": selected_block.get("block_type", "other"),
                        "values": []
                    })

                    # Основные поля переменной
                    st.markdown(f"#### AI переменная: `{ai_var}`")

                    with st.form(key=f"edit_ai_var_form_{ai_var}_{tab_idx}"):
                        description = st.text_input(
                            "Описание переменной:",
                            value=var_data.get("description", ""),
                            key=f"ai_desc_{ai_var}_{tab_idx}"
                        )

                        # AI настройки
                        st.markdown("##### 🤖 Настройки AI генерации")

                        col_ai1, col_ai2 = st.columns(2)
                        with col_ai1:
                            ai_provider = st.selectbox(
                                "AI провайдер:",
                                ["openai", "deepseek"],
                                index=0 if var_data.get("ai_provider", "openai") == "openai" else 1,
                                key=f"ai_provider_{ai_var}_{tab_idx}"
                            )

                        with col_ai2:
                            ai_num_variants = st.number_input(
                                "Количество вариантов:",
                                min_value=1,
                                max_value=10,
                                value=var_data.get("ai_num_variants", 3),
                                key=f"ai_num_variants_{ai_var}_{tab_idx}"
                            )

                        # Промпт для AI
                        st.markdown("##### 📝 Промпт для генерации")
                        st.caption("""
                        Доступные переменные для подстановки:
                        - Для characteristic блоков: {категория}, {характеристика}, {значение}, {тип}
                        - Для других блоков: {контекст_категория}, {маркер}
                        """)

                        ai_prompt = st.text_area(
                            "Промпт:",
                            value=var_data.get("ai_prompt", ""),
                            height=300,
                            key=f"ai_prompt_{ai_var}_{tab_idx}"
                        )

                        # Кнопки управления
                        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
                        with col_btn1:
                            save_btn = st.form_submit_button("💾 Сохранить настройки", use_container_width=True)
                            if save_btn:
                                # Обновляем данные переменной
                                var_data.update({
                                    "description": description,
                                    "type": "ai",
                                    "ai_prompt": ai_prompt,
                                    "ai_num_variants": ai_num_variants,
                                    "ai_provider": ai_provider,
                                    "ai_context_type": selected_block.get("block_type", "other")
                                })

                                variables_data[ai_var] = var_data
                                selected_block["variables_data"] = variables_data
                                if st.session_state.block_manager.save_block(selected_block, variables_data):
                                    st.success(f"✅ Настройки AI переменной '{ai_var}' сохранены!")
                                    st.rerun()

                        with col_btn2:
                            if st.form_submit_button("🚀 Генерировать", type="primary", use_container_width=True):
                                # Сохраняем сначала настройки
                                var_data.update({
                                    "description": description,
                                    "type": "ai",
                                    "ai_prompt": ai_prompt,
                                    "ai_num_variants": ai_num_variants,
                                    "ai_provider": ai_provider
                                })

                                variables_data[ai_var] = var_data
                                selected_block["variables_data"] = variables_data
                                st.session_state.block_manager.save_block(selected_block, variables_data)

                                # Устанавливаем контекст для генерации
                                st.session_state.current_ai_var_for_generation = ai_var
                                st.session_state.current_block_for_ai = selected_block_id
                                st.session_state.current_ai_tab_idx = tab_idx
                                st.rerun()

                        with col_btn3:
                            if st.form_submit_button("🗑️ Удалить", type="secondary", use_container_width=True):
                                # Подтверждение удаления
                                if st.session_state.get(f"confirm_delete_{ai_var}", False):
                                    # Удаляем из списка переменных блока
                                    if ai_var in variables:
                                        variables.remove(ai_var)

                                    # Удаляем из variables_data
                                    if ai_var in variables_data:
                                        del variables_data[ai_var]

                                    # Удаляем сохраненные инструкции
                                    if 'ai_instruction_manager' in st.session_state:
                                        st.session_state.ai_instruction_manager.delete_instruction(
                                            selected_block_id, ai_var
                                        )

                                    # Сохраняем блок
                                    selected_block["variables"] = variables
                                    selected_block["variables_data"] = variables_data
                                    if st.session_state.block_manager.save_block(selected_block, variables_data):
                                        st.success(f"✅ AI переменная '{ai_var}' удалена!")
                                        st.rerun()
                                else:
                                    st.session_state[f"confirm_delete_{ai_var}"] = True
                                    st.warning(
                                        f"Нажмите '🗑️ Удалить' еще раз для подтверждения удаления переменной '{ai_var}'")
                                    st.rerun()

                    # Если для этой переменной выбрана генерация
                    if (hasattr(st.session_state, 'current_ai_var_for_generation') and
                            st.session_state.current_ai_var_for_generation == ai_var and
                            hasattr(st.session_state, 'current_block_for_ai') and
                            st.session_state.current_block_for_ai == selected_block_id):

                        st.markdown("---")
                        st.markdown("### 🚀 Генерация AI-инструкций")

                        # Определяем тип блока и соответствующий контекст генерации
                        block_type = selected_block.get("block_type", "other")

                        if block_type == "characteristic":
                            # Генерация для characteristic блоков
                            show_ai_generation_for_characteristics(
                                selected_block_id, ai_var, var_data, selected_block
                            )
                        else:
                            # Генерация для других типов блоков
                            show_ai_generation_for_other_blocks(
                                selected_block_id, ai_var, var_data, selected_block
                            )

                        # Кнопка отмены генерации
                        if st.button("❌ Отменить генерацию", key=f"cancel_gen_{ai_var}", use_container_width=True):
                            del st.session_state.current_ai_var_for_generation
                            if hasattr(st.session_state, 'current_block_for_ai'):
                                del st.session_state.current_block_for_ai
                            if hasattr(st.session_state, 'current_ai_tab_idx'):
                                del st.session_state.current_ai_tab_idx
                            st.rerun()

        else:
            st.info("""
            **AI переменные**

            AI переменные позволяют генерировать динамический контент с помощью искусственного интеллекта.

            **Преимущества:**
            - Автоматическая генерация уникального контента
            - Адаптация под разные типы блоков
            - Поддержка нескольких AI провайдеров
            - Сохранение и редактирование сгенерированных результатов

            **Как использовать:**
            1. Создайте новую AI переменную с помощью кнопки выше
            2. Настройте промпт для генерации
            3. Запустите генерацию для создания контента
            4. Редактируйте и сохраняйте результаты

            **Поддерживаемые типы блоков:**
            - Characteristic блоки: генерация для характеристик товаров
            - Other блоки: генерация общего контента (введения, заключения и т.д.)
            """)

    with tab_dynamic:
        # Динамические переменные (извлекаем из блока)
        dynamic_vars = []

        # Ищем динамические переменные в шаблоне
        template = selected_block.get("template", "")
        all_vars_in_template = re.findall(r'\{([^}]+)\}', template)

        # Получаем список динамических переменных из менеджера
        if 'dynamic_var_manager' in st.session_state:
            dynamic_var_names = list(st.session_state.dynamic_var_manager.get_all_dynamic_vars().keys())

            # Находим пересечение - переменные, которые есть и в шаблоне и в динамических
            dynamic_vars = [v for v in dynamic_var_names if v in all_vars_in_template]

        if not dynamic_vars:
            st.info("""
            **Динамические переменные**

            Динамические переменные автоматически подставляются из конфигурации.
            Они доступны для использования в любом блоке.

            Чтобы добавить динамическую переменную:
            1. Перейдите на вкладку "🌀 Редактирование динамических переменных"
            2. Создайте новую динамическую переменную
            3. Используйте `{название_переменной}` в шаблоне блока

            **Примеры доступных динамических переменных:**
            - `{стоп}` - стоп-слова и ограничения
            - `{контекст_категория}` - категория товара
            - `{значение_форматированное}` - значение характеристики
            - `{название_характеристики}` - название характеристики
            - `{характеристика_маркер}` - маркер для характеристик
            - `{маркер}` - общий маркер
            """)
        else:
            st.success(f"✅ Найдено {len(dynamic_vars)} динамических переменных в шаблоне")

            for dyn_var in dynamic_vars:
                # Получаем информацию о динамической переменной
                if 'dynamic_var_manager' in st.session_state:
                    var_info = st.session_state.dynamic_var_manager.get_dynamic_variable(dyn_var)

                    if var_info:
                        with st.expander(f"Динамическая переменная: `{{{dyn_var}}}`"):
                            st.write(f"**Описание:** {var_info.get('description', 'Нет описания')}")
                            st.write(f"**Источник:** {var_info.get('source', 'unknown')}")

                            values = var_info.get("values", [])
                            if values and var_info.get("source") == "config":
                                st.write(f"**Количество значений:** {len(values)}")
                                st.write("**Примеры значений:**")
                                for val in values[:3]:  # Показываем первые 3 значения
                                    st.write(f"- {val}")
                                if len(values) > 3:
                                    st.write(f"... и еще {len(values) - 3} значений")

            st.info(
                "💡 Для редактирования динамических переменных перейдите на соответствующую вкладку в основном интерфейсе")

    # Информация о переменных блока
    with st.expander("📊 Статистика по переменным", expanded=False):
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Всего переменных", len(variables))
        with col_stat2:
            static_count = len([v for v in variables if variables_data.get(v, {}).get("type", "static") == "static"])
            st.metric("Статических", static_count)
        with col_stat3:
            ai_count = len([v for v in variables if variables_data.get(v, {}).get("type") == "ai"])
            st.metric("AI", ai_count)

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

                # Для characteristic блоков устанавливаем characteristic_type по умолчанию, если не указан
                if block_data.get("block_type") == "characteristic":
                    if "settings" not in block_data:
                        block_data["settings"] = {}
                    if "characteristic_type" not in block_data["settings"]:
                        # Определяем по названию
                        block_name = block_data.get("name", "").lower()
                        if "unique" in block_name:
                            block_data["settings"]["characteristic_type"] = "unique"
                        else:
                            block_data["settings"]["characteristic_type"] = "regular"

                # Загружаем переменные
                if variables_file.exists():
                    with open(variables_file, 'r', encoding='utf-8') as f:
                        block_data["variables_data"] = json.load(f)
                else:
                    block_data["variables_data"] = {}

                self.blocks[block_data["block_id"]] = block_data

            except Exception as e:
                st.error(f"Ошибка загрузки блока {block_dir.name}: {e}")
# В конец phase3.py (перед if __name__ == "__main__":)
def save_data_to_app_state():
    """Сохраняет данные фазы 3 в общее состояние приложения"""
    if 'app_data' in st.session_state:
        # Можно сохранять информацию о блоках
        blocks = st.session_state.block_manager.get_all_blocks()
        if blocks:
            st.session_state.app_data['phase3'] = {
                'blocks_count': len(blocks),
                'characteristic_blocks': len([b for b in blocks.values() if b.get('block_type') == 'characteristic']),
                'other_blocks': len([b for b in blocks.values() if b.get('block_type') == 'other'])
            }
            return True
    return False
# ===== Новые функции для массовой генерации AI =====
# ===== Новые функции для массовой генерации AI =====
def batch_generate_for_characteristic(block_id, var_name, var_data, block):
    """
    Генерирует AI-инструкции для characteristic-блока без UI.
    Возвращает словарь со статистикой: {'success': int, 'errors': int}
    """
    # Получаем данные из фазы 2
    phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
    category = phase2_data.get('category', '')
    characteristics = st.session_state.get('loaded_data', {}).get('characteristics', [])

    if not category or not characteristics:
        return {"success": 0, "errors": 0, "error": "Нет данных категории или характеристик"}

    provider = var_data.get("ai_provider", "openai")
    prompt_template = var_data.get("ai_prompt", "")
    num_variants = var_data.get("ai_num_variants", 1)

    success_count = 0
    error_count = 0

    for char in characteristics:
        char_id = char.get('char_id')
        char_name = char.get('char_name')
        is_unique = char.get('is_unique', False)
        values = char.get('values', [])

        if is_unique:
            for value_item in values:
                value = value_item.get('value', '')
                context = {
                    "категория": category,
                    "характеристика": char_name,
                    "значение": value,
                    "тип": "unique",
                    "block_id": block_id,
                    "var_name": var_name
                }
                try:
                    gen_results = st.session_state.ai_generator.generate_instruction(
                        prompt_template, context, provider=provider, num_variants=1
                    )
                    if gen_results and gen_results[0].get("success"):
                        instruction = gen_results[0]["text"]
                        st.session_state.ai_instruction_manager.save_instruction(
                            block_id, var_name, [instruction], context,
                            {"provider": provider, "char_id": char_id, "char_name": char_name, "value": value}
                        )
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1
        else:
            context = {
                "категория": category,
                "характеристика": char_name,
                "тип": "regular",
                "block_id": block_id,
                "var_name": var_name
            }
            try:
                gen_results = st.session_state.ai_generator.generate_instruction(
                    prompt_template, context, provider=provider, num_variants=num_variants
                )
                successful = [r["text"] for r in gen_results if r.get("success")]
                if successful:
                    st.session_state.ai_instruction_manager.save_instruction(
                        block_id, var_name, successful, context,
                        {"provider": provider, "char_id": char_id, "char_name": char_name}
                    )
                    success_count += len(successful)
                error_count += sum(1 for r in gen_results if not r.get("success"))
            except Exception:
                error_count += num_variants

    return {"success": success_count, "errors": error_count}


def batch_generate_for_other(block_id, var_name, var_data, block):
    """
    Генерирует AI-инструкции для other-блока без UI.
    Возвращает статистику.
    """
    phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
    category = phase2_data.get('category', '')

    if not category:
        return {"success": 0, "errors": 0, "error": "Нет категории"}

    provider = var_data.get("ai_provider", "openai")
    prompt_template = var_data.get("ai_prompt", "")
    num_variants = var_data.get("ai_num_variants", 3)

    context = {
        "категория": category,
        "тип": "other",
        "block_id": block_id,
        "var_name": var_name
    }

    try:
        gen_results = st.session_state.ai_generator.generate_instruction(
            prompt_template, context, provider=provider, num_variants=num_variants
        )
        successful = [r["text"] for r in gen_results if r.get("success")]
        if successful:
            st.session_state.ai_instruction_manager.save_instruction(
                block_id, var_name, successful, context,
                {"provider": provider, "block_type": "other", "num_variants": num_variants}
            )
        return {"success": len(successful), "errors": num_variants - len(successful)}
    except Exception as e:
        return {"success": 0, "errors": num_variants, "error": str(e)}


def has_ai_values(block_id, var_name):
    """
    Возвращает True, если для данной переменной существуют инструкции,
    сгенерированные для текущей категории (из фазы 2).
    """
    # Текущая категория
    phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
    current_category = phase2_data.get('category', '')

    if not current_category:
        return False

    # Получаем менеджер инструкций
    ai_mgr = st.session_state.get('ai_instruction_manager')
    if not ai_mgr:
        return False

    # Проверяем наличие данных для блока и переменной
    if block_id not in ai_mgr.instructions:
        return False
    if var_name not in ai_mgr.instructions[block_id]:
        return False

    # Перебираем все сохранённые контексты для этой переменной
    for context_hash, data in ai_mgr.instructions[block_id][var_name].items():
        context = data.get("context", {})
        # Проверяем, что категория совпадает и есть значения
        if context.get("категория") == current_category:
            if data.get("values"):
                return True

    return False

def show_ai_instructions_full(block_id, var_name, block):
    """Отображает все сгенерированные инструкции для AI-переменной с возможностью редактирования"""
    if 'ai_instruction_manager' not in st.session_state:
        st.error("Менеджер AI не инициализирован")
        return

    # Получаем текущую категорию из данных фазы 2
    phase2_data = st.session_state.get('phase2_data') or st.session_state.get('app_data', {}).get('phase2', {})
    current_category = phase2_data.get('category', '')

    if not current_category:
        st.warning("⚠️ Категория не загружена. Невозможно отфильтровать инструкции. Загрузите данные в фазе 2.")
        return

    ai_mgr = st.session_state.ai_instruction_manager

    if block_id not in ai_mgr.instructions or var_name not in ai_mgr.instructions[block_id]:
        st.info("Нет сохранённых инструкций для этой переменной.")
        return

    instructions_dict = ai_mgr.instructions[block_id][var_name]

    # Фильтруем только те контексты, у которых категория совпадает с текущей
    filtered_items = []
    for context_hash, data in instructions_dict.items():
        context = data.get("context", {})
        if context.get("категория") == current_category:
            filtered_items.append((context_hash, data))

    if not filtered_items:
        st.info(f"Нет инструкций для текущей категории «{current_category}».")
        return

    # Отображаем отфильтрованные инструкции с возможностью редактирования
    for context_hash, data in filtered_items:
        context = data.get("context", {})
        values = data.get("values", [])
        original_values = data.get("original_values", [])
        metadata = data.get("metadata", {})

        # Заголовок в зависимости от типа
        context_type = context.get("тип", "unknown")
        characteristic = context.get("характеристика", "")
        value = context.get("значение", "")

        if context_type == "regular":
            title = f"**Regular**: {characteristic}"
        elif context_type == "unique":
            title = f"**Unique**: {characteristic} = {value}"
        elif context_type == "other":
            title = f"**Other**: блок {block.get('name', block_id)}"
        else:
            title = f"**Контекст**: {current_category} / {characteristic}"

        with st.expander(title, expanded=False):
            st.markdown("**Контекст генерации:**")
            st.json(context)

            if metadata:
                st.markdown("**Метаданные:**")
                st.json(metadata)

            # Редактирование инструкций
            st.markdown("**Редактирование инструкций:**")

            # Если есть оригинальные значения (полные ответы) – редактируем их
            if original_values:
                for idx, orig in enumerate(original_values):
                    col_edit1, col_edit2 = st.columns([5, 1])
                    with col_edit1:
                        new_value = st.text_area(
                            f"Вариант {idx+1}:",
                            value=orig,
                            height=150,
                            key=f"edit_full_{block_id}_{var_name}_{context_hash}_{idx}"
                        )
                    with col_edit2:
                        if st.button("💾", key=f"save_full_{block_id}_{var_name}_{context_hash}_{idx}"):
                            # Обновляем полное значение и переразбиваем на пункты
                            if ai_mgr.update_full_instruction(block_id, var_name, context_hash, idx, new_value):
                                st.success("✅ Сохранено!")
                                st.rerun()
            else:
                # Если нет оригинальных, редактируем разбитые пункты
                for idx, val in enumerate(values):
                    col_edit1, col_edit2 = st.columns([5, 1])
                    with col_edit1:
                        new_val = st.text_area(
                            f"Пункт {idx+1}:",
                            value=val,
                            height=100,
                            key=f"edit_split_{block_id}_{var_name}_{context_hash}_{idx}"
                        )
                    with col_edit2:
                        if st.button("💾", key=f"save_split_{block_id}_{var_name}_{context_hash}_{idx}"):
                            if ai_mgr.update_instruction_value(block_id, var_name, context_hash, idx, new_val):
                                st.success("✅ Сохранено!")
                                st.rerun()

            # Кнопка удаления всех инструкций для этого контекста
            if st.button("🗑️ Удалить все инструкции для этого контекста",
                         key=f"delete_ctx_{block_id}_{var_name}_{context_hash}"):
                if ai_mgr.delete_instruction(block_id, var_name, context_hash):
                    st.success("✅ Инструкции удалены!")
                    st.rerun()


if __name__ == "__main__":
    main()