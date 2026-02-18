
import html
import json
import random
import re
import streamlit as st
from phase3 import BlockManager, VariableManager, DynamicVariableManager, DynamicVariableProcessor, local_css
from ai_module import AIConfigManager, AIGenerator, AIInstructionManager


class DataLoader:
    """Загрузчик данных из файлов"""

    @staticmethod
    def load_stop_words(stop_words_file="data/stop_words.txt"):
        """Загружает стоп-слова из файла"""
        try:
            with open(stop_words_file, 'r', encoding='utf-8') as f:
                stop_words = [line.strip() for line in f if line.strip()]
                return ", ".join(stop_words)
        except:
            # Возвращаем стандартные стоп-слова
            return "купить, заказать, цена, дешево, скидка, акция"

    @staticmethod
    def load_feature_data(feature_id, feature_data_file="data/features.json"):
        """Загружает дополнительные данные характеристики"""
        try:
            with open(feature_data_file, 'r', encoding='utf-8') as f:
                features_data = json.load(f)
                return features_data.get(feature_id, {})
        except:
            return {}


class WeightedRandomSelector:
    """Взвешенный случайный выбор с ранжированием"""

    @staticmethod
    def weighted_choice(items, weights=None):
        """Выбирает элемент с учетом весов"""
        if not items:
            return None

        # Если веса не указаны, используем равномерное распределение
        if weights is None or len(weights) != len(items):
            return random.choice(items)

        # Проверяем, что все веса неотрицательные
        valid_weights = [max(w, 0) for w in weights]
        total = sum(valid_weights)

        # Если все веса равны 0, используем равномерное распределение
        if total == 0:
            return random.choice(items)

        # Взвешенный случайный выбор
        r = random.uniform(0, total)
        cumulative = 0

        for i, weight in enumerate(valid_weights):
            cumulative += weight
            if r <= cumulative:
                return items[i]

        # На всякий случай возвращаем последний элемент
        return items[-1]


# --- Дополнительные классы для генерации ---
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

    def get_next_marker(self, with_quotes=False):
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


# --- НОВЫЙ КЛАСС: Трекинг использования значений ---
class UsageTracker:
    """Отслеживает использование значений с учетом контекста"""

    def __init__(self, history_window=100):
        self.history = {}  # key -> list of recent choices
        self.total_counts = {}  # key -> total usage count
        self.history_window = history_window

    def get_key(self, block_id, var_name, context_hash=None):
        """Создает ключ для трекинга"""
        if context_hash:
            return f"{block_id}:{var_name}:{context_hash}"
        return f"{block_id}:{var_name}"

    def track_usage(self, key, value):
        """Добавляет использование значения"""
        if key not in self.history:
            self.history[key] = []
            self.total_counts[key] = {}

        # Обновляем историю
        self.history[key].append(value)

        # Ограничиваем размер истории
        if len(self.history[key]) > self.history_window:
            self.history[key].pop(0)

        # Обновляем общий счетчик
        self.total_counts[key][value] = self.total_counts[key].get(value, 0) + 1

    def get_recent_usage(self, key, value):
        """Возвращает количество недавних использований значения"""
        if key not in self.history:
            return 0
        return self.history[key].count(value)

    def get_total_usage(self, key, value):
        """Возвращает общее количество использований"""
        return self.total_counts.get(key, {}).get(value, 0)

    def get_usage_penalty(self, key, value):
        """Рассчитывает штраф за использование (от 0 до 1)"""
        recent_count = self.get_recent_usage(key, value)
        total_count = self.get_total_usage(key, value)

        # Штрафуем за недавнее использование сильнее
        recent_penalty = 1.0 / (recent_count * 2 + 1)

        # И за общее использование (но слабее)
        total_penalty = 1.0 / (total_count * 0.5 + 1)

        return recent_penalty * total_penalty

    def reset_for_key(self, key):
        """Сбрасывает статистику для ключа"""
        if key in self.history:
            self.history[key] = []
        if key in self.total_counts:
            self.total_counts[key] = {}

    def reset_all(self):
        """Сбрасывает всю статистику"""
        self.history = {}
        self.total_counts = {}
class PromptGenerator:
    """Генератор промптов с поддержкой динамических переменных"""

    def __init__(self, block_manager, variable_manager, dynamic_var_manager):
        self.block_manager = block_manager
        self.variable_manager = variable_manager
        self.dynamic_var_manager = dynamic_var_manager
        self.data_loader = DataLoader()
        self.random_selector = WeightedRandomSelector()

        # НОВОЕ: Трекер использования
        self.usage_tracker = UsageTracker(history_window=50)  # Учитываем последние 50 использований

        # Для обратной совместимости - режимы рандомизации
        self.randomization_mode = "adaptive"  # "adaptive", "uniform", "weighted_only"

        # НОВЫЙ МЕТОД: Адаптивный выбор с учетом использования

    def get_adaptive_static_value(self, block_id, var_name, context=None):
        """Возвращает значение статической переменной с учетом истории использования"""
        var_data = self.variable_manager.get_variable_data(block_id, var_name)

        if not var_data or "values" not in var_data or not var_data["values"]:
            return ""

        values_list = var_data["values"]

        # Подготавливаем список значений и базовых весов
        items = []
        base_weights = []

        for item in values_list:
            if isinstance(item, str):
                items.append(item)
                base_weights.append(1.0)
            elif isinstance(item, dict) and "value" in item:
                items.append(item["value"])
                weight = item.get("weight", 1.0)
                if isinstance(weight, str):
                    try:
                        weight = float(weight)
                    except:
                        weight = 1.0
                base_weights.append(max(0.1, weight))  # Минимальный вес 0.1

        if not items:
            return ""

        # Создаем ключ для трекинга
        context_hash = ""
        if context:
            # Создаем упрощенный хэш контекста (только важные поля)
            context_keys = ["категория", "характеристика", "значение", "тип"]
            context_str = "|".join(str(context.get(k, "")) for k in context_keys)
            import hashlib
            context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]

        tracker_key = self.usage_tracker.get_key(block_id, var_name, context_hash)

        # Рассчитываем скорректированные веса
        adjusted_weights = []
        for i, value in enumerate(items):
            base_weight = base_weights[i]

            if self.randomization_mode == "uniform":
                # Равномерное распределение (старый режим)
                adjusted = 1.0
            elif self.randomization_mode == "weighted_only":
                # Только по базовым весам (старый режим)
                adjusted = base_weight
            else:
                # Адаптивный режим: учитываем использование
                penalty = self.usage_tracker.get_usage_penalty(tracker_key, value)
                adjusted = base_weight * penalty

            adjusted_weights.append(adjusted)

        # Взвешенный выбор
        chosen = self.random_selector.weighted_choice(items, adjusted_weights)

        # Отслеживаем использование
        self.usage_tracker.track_usage(tracker_key, chosen)

        return self.escape_html(chosen)

    def generate_prompts_for_block(self, block, num_prompts, category="", markers=None, marker_rotator=None):
        """Генерирует промпты для блока (не характеристика)"""

        if not block:
            return []

        prompts = []

        for prompt_num in range(num_prompts):
            # Подготавливаем контекст для "other" блоков
            context = {
                "категория": self.escape_html(category),
                "стоп_слова": self.data_loader.load_stop_words(),
                "prompt_num": prompt_num + 1,
                "total_prompts": num_prompts,
                "тип": "other",
                "block_id": block.get("block_id", ""),
                "block_type": block.get("block_type", "other")
            }

            # Добавляем маркер в контекст, если есть
            if markers and marker_rotator:
                marker = marker_rotator.get_next_marker(with_quotes=True)
                context["маркер"] = marker
                context["маркер_заголовка"] = marker
                context["маркер_описания"] = marker
                context["маркер_применения"] = marker
                context["маркер_блока"] = marker
                context["характеристика_маркер"] = marker

            # Генерируем промпт с правильным типом блока
            prompt = self.generate_single_prompt(block, context, char_type=None)

            if prompt:
                prompts.append({
                    "block_id": block.get("block_id", ""),
                    "block_name": block.get("name", ""),
                    "block_type": block.get("block_type", "other"),
                    "prompt_num": prompt_num + 1,
                    "prompt": prompt,
                    "context": context
                })

        return prompts

    def generate_single_other_block_prompt(self, block, context):
        """Генерирует промпт для блока (не характеристика)"""

        template = block.get("template", "")

        # 1. Обрабатываем динамические переменные
        if self.dynamic_var_manager:
            processor = self.dynamic_var_manager.get_processor()
            template = processor.render_template_with_context(template, context, include_dynamic=True)

        # 2. Обрабатываем статические переменные с взвешенным выбором
        for var_name in block.get("variables", []):
            placeholder = f"{{{var_name}}}"
            if placeholder in template:
                var_value = self.get_weighted_static_value(block["block_id"], var_name)
                # Если переменная содержит плейсхолдер маркера, заменяем его
                if "{маркер}" in var_value and "маркер" in context:
                    var_value = var_value.replace("{маркер}", context["маркер"])
                if "{маркер_заголовка}" in var_value and "маркер_заголовка" in context:
                    var_value = var_value.replace("{маркер_заголовка}", context["маркер_заголовка"])
                if "{маркер_описания}" in var_value and "маркер_описания" in context:
                    var_value = var_value.replace("{маркер_описания}", context["маркер_описания"])
                if "{характеристика_маркер}" in var_value and "характеристика_маркер" in context:
                    var_value = var_value.replace("{характеристика_маркер}", context["характеристика_маркер"])

                template = template.replace(placeholder, var_value)

        # 3. Заменяем оставшиеся плейсхолдеры маркера
        if "маркер" in context:
            possible_placeholders = [
                "{маркер_заголовка}",
                "{маркер_описания}",
                "{маркер_применения}",
                "{маркер_блока}",
                "{характеристика_маркер}",
                "{маркер}",
                "[МАРКЕР]",
                "{МАРКЕР}"
            ]
            for placeholder in possible_placeholders:
                if placeholder in template:
                    template = template.replace(placeholder, context["маркер"])

        # 4. Очищаем результат
        template = re.sub(r'\n{3,}', '\n\n', template.strip())

        return template

    def escape_html(self, text):
        """Экранирует HTML-сущности в тексте"""
        if not isinstance(text, str):
            text = str(text)
        return html.escape(text)



    def get_weighted_static_value(self, block_id, var_name):
        """Возвращает значение статической переменной с учетом весов и истории использования"""
        # Используем новый адаптивный метод без контекста для обратной совместимости
        return self.get_adaptive_static_value(block_id, var_name)

    # Обновим метод для AI-переменных:
    def get_weighted_ai_value(self, block_id, var_name, context):
        """Получает значение AI-переменной с учетом контекста, весов и использования"""
        # Инициализируем менеджер инструкций если нужно
        if 'ai_instruction_manager' not in st.session_state:
            st.session_state.ai_instruction_manager = AIInstructionManager()

        # Получаем сохраненные инструкции для этого контекста
        instructions = st.session_state.ai_instruction_manager.get_instruction(
            block_id, var_name, context
        )

        if instructions:
            all_items = []

            for instruction in instructions:
                if isinstance(instruction, str):
                    # Разбиваем по точке с запятой и убираем пробелы
                    items = [item.strip() for item in instruction.split(';') if item.strip()]
                    all_items.extend(items)
                elif isinstance(instruction, list):
                    # Если уже список, добавляем как есть
                    all_items.extend(instruction)

            if all_items:
                # Создаем ключ для трекинга
                context_keys = ["категория", "характеристика", "значение", "тип"]
                context_str = "|".join(str(context.get(k, "")) for k in context_keys)
                import hashlib
                context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]

                tracker_key = self.usage_tracker.get_key(block_id, var_name, context_hash)

                # Рассчитываем веса с учетом использования
                weights = []
                for item in all_items:
                    # Базовый вес
                    base_weight = 1.0

                    if self.randomization_mode == "uniform":
                        adjusted = 1.0
                    elif self.randomization_mode == "weighted_only":
                        adjusted = base_weight
                    else:
                        # Адаптивный режим
                        penalty = self.usage_tracker.get_usage_penalty(tracker_key, item)
                        adjusted = base_weight * penalty

                    weights.append(adjusted)

                # Выбираем ОДИН пункт с учетом весов
                chosen_item = self.random_selector.weighted_choice(all_items, weights)

                # Отслеживаем использование
                self.usage_tracker.track_usage(tracker_key, chosen_item)

                return self.escape_html(chosen_item)

        # Если нет AI-инструкций, используем адаптивные статические значения
        return self.get_adaptive_static_value(block_id, var_name, context)

    # НОВЫЙ МЕТОД: Сброс трекера использования
    def reset_usage_tracking(self):
        """Сбрасывает статистику использования"""
        self.usage_tracker.reset_all()

    # НОВЫЙ МЕТОД: Установка режима рандомизации
    def set_randomization_mode(self, mode):
        """Устанавливает режим рандомизации"""
        valid_modes = ["adaptive", "uniform", "weighted_only"]
        if mode in valid_modes:
            self.randomization_mode = mode
        else:
            self.randomization_mode = "adaptive"

    def prepare_context(self, characteristic=None, category="", char_type="regular",
                        feature_data=None, additional_context=None):
        """Подготавливает контекст для подстановки"""
        context = {
            "категория": self.escape_html(category),
            "стоп_слова": self.data_loader.load_stop_words(),
            "маркер": "[МАРКЕР]",
            "название_характеристики": "",
            "значение": "",
            "тип": char_type
        }

        # Добавляем данные характеристики
        if characteristic:
            context.update({
                "название_характеристики": self.escape_html(characteristic.get("char_name", "")),
                "значение": self.escape_html(characteristic.get("value", "")),
                "характеристика": self.escape_html(characteristic.get("char_name", ""))
            })

        # Добавляем feature_data
        if feature_data:
            for key, value in feature_data.items():
                safe_key = key.replace("-", "_").replace(" ", "_")
                context[safe_key] = self.escape_html(value)

        # Добавляем дополнительный контекст
        if additional_context:
            for key, value in additional_context.items():
                context[key] = self.escape_html(value)

        return context

    def generate_prompts_for_characteristic(self, characteristic, block_id, num_prompts_per_value,
                                            char_type="regular", category="", markers=None,
                                            marker_rotator=None, feature_id=None):
        """Генерирует промпты для характеристики"""

        block = self.block_manager.get_block(block_id)
        if not block:
            return []

        prompts = []

        # Загружаем дополнительные данные характеристики
        feature_data = {}
        if feature_id:
            feature_data = self.data_loader.load_feature_data(feature_id)

        # Получаем значения характеристики
        values_list = characteristic.get("values", [])
        if not values_list:
            return []

        # Обрабатываем каждое значение
        for value_item in values_list:
            value = value_item.get("value", "")

            for prompt_num in range(num_prompts_per_value):
                # Создаем характеристику с конкретным значением
                char_with_value = characteristic.copy()
                char_with_value["value"] = value

                # Подготавливаем контекст
                context = self.prepare_context(
                    characteristic=char_with_value,
                    category=category,
                    char_type=char_type,
                    feature_data=feature_data,
                    additional_context={
                        "prompt_num": prompt_num + 1,
                        "total_prompts": num_prompts_per_value
                    }
                )

                # Добавляем маркер в контекст
                if markers and marker_rotator:
                    marker = marker_rotator.get_next_marker(with_quotes=True)
                    context["маркер"] = marker
                    context["характеристика_маркер"] = marker

                # Генерируем промпт
                prompt = self.generate_single_prompt(block, context, char_type)

                if prompt:
                    prompts.append({
                        "characteristic_id": characteristic.get("char_id", ""),
                        "characteristic_name": characteristic.get("char_name", ""),
                        "value": value,
                        "prompt_num": prompt_num + 1,
                        "type": char_type,
                        "prompt": prompt,
                        "context": context,
                        "feature_id": feature_id
                    })

        return prompts

    # В phase4.py в классе PromptGenerator:


    def get_ai_variable_value(self, block_id, var_name, context):
        """Получает значение AI-переменной с учетом контекста"""

        if 'ai_instruction_manager' not in st.session_state:
            st.session_state.ai_instruction_manager = AIInstructionManager()

        # Создаем упрощенный контекст для поиска
        search_context = {
            "категория": context.get("категория", ""),
            "характеристика": context.get("характеристика", context.get("название_характеристики", "")),
            "тип": context.get("тип", "regular"),
            "значение": context.get("значение", "")
        }

        # Ищем инструкции с проверкой контекста (используем новый метод)
        instructions = st.session_state.ai_instruction_manager.get_instruction(
            block_id, var_name, search_context
        )

        if instructions:
            # Выбираем случайный пункт из найденных инструкций
            if instructions:
                return self.escape_html(random.choice(instructions))

        # Если не нашли по точному контексту, ищем любые инструкции для этой характеристики
        # Более гибкий поиск - только по характеристике и категории
        if search_context["характеристика"]:
            all_contexts = st.session_state.ai_instruction_manager.get_all_contexts_for_variable(
                block_id, var_name
            )

            for ctx_info in all_contexts:
                stored_ctx = ctx_info.get("context", {})
                # Проверяем совпадение категории и характеристики
                if (stored_ctx.get("категория") == search_context["категория"] and
                        stored_ctx.get("характеристика") == search_context["характеристика"]):

                    # Нашли подходящий контекст
                    context_hash = ctx_info["hash"]
                    instructions = st.session_state.ai_instruction_manager.get_instruction(
                        block_id, var_name, stored_ctx
                    )

                    if instructions:
                        return self.escape_html(random.choice(instructions))

        # Логируем, если не нашли
        if st.session_state.get('debug_mode', False):
            st.warning(f"Не найдены AI-инструкции для: {var_name} в контексте {search_context}")

        # Пробуем получить любые инструкции для этой переменной (fallback)
        all_instructions = st.session_state.ai_instruction_manager.get_instruction(block_id, var_name)
        if all_instructions and isinstance(all_instructions, list) and len(all_instructions) > 0:
            return self.escape_html(random.choice(all_instructions))

        # Последний fallback - стандартные значения
        var_data = self.variable_manager.get_variable_data(block_id, var_name)
        if var_data and "values" in var_data and var_data["values"]:
            # Пытаемся разбить стандартные значения
            all_values = []
            for value in var_data["values"]:
                if isinstance(value, str):
                    items = [item.strip() for item in value.split(';') if item.strip()]
                    all_values.extend(items)

            if all_values:
                return self.escape_html(random.choice(all_values))

        return ""

    def generate_single_prompt(self, block, context, char_type=None):
        """Генерирует один промпт с поддержкой AI-переменных"""

        # Отладка: логируем контекст
        if st.session_state.get('debug_ai', False):
            st.info(f"🔍 Контекст для генерации: {context.get('характеристика', 'N/A')}")

        template = block.get("template", "")
        block_type = block.get("block_type", "characteristic" if char_type else "other")
        settings = block.get("settings", {})

        # 1. Обрабатываем AI-переменные (ПЕРВЫЕ, так как они могут содержать другие переменные)
        for var_name in block.get("variables", []):
            placeholder = f"{{{var_name}}}"
            if placeholder in template:
                var_data = self.variable_manager.get_variable_data(block["block_id"], var_name)
                if var_data and var_data.get("type") == "ai":
                    # Это AI-переменная
                    if block_type == "other":
                        # Для блоков "other" используем упрощенный контекст
                        block_context = {
                            "категория": context.get("категория", ""),
                            "тип": "other",
                            "block_id": block["block_id"],
                            "var_name": var_name
                        }
                    else:
                        # Для characteristic блоков используем полный контекст
                        block_context = context

                    ai_value = self.get_weighted_ai_value(block["block_id"], var_name, block_context)
                    template = template.replace(placeholder, ai_value)

        # 2. Обрабатываем динамические переменные
        if self.dynamic_var_manager:
            processor = self.dynamic_var_manager.get_processor()
            template = processor.render_template_with_context(template, context, include_dynamic=True)

        # 3. Форматированное значение (только для characteristic блоков)
        if char_type == "unique":
            format_template = settings.get("формат_значения_unique", "\"[значение]\"")
            value_formatted = format_template.replace("[значение]", context.get("значение", ""))
            value_formatted = value_formatted.replace("значение", context.get("значение", ""))
            template = template.replace("{значение_форматированное}", value_formatted)
        elif char_type == "regular":
            format_template = settings.get("формат_значения_regular", "[[значение]]")
            value_formatted = format_template.replace("[значение]", context.get("значение", ""))
            value_formatted = value_formatted.replace("значение", context.get("значение", ""))
            template = template.replace("{значение_форматированное}", value_formatted)

        # 4. Обрабатываем скобки_характеристика для regular характеристик
        if char_type == "regular" and settings.get("добавлять_скобки_переменную", True):
            brackets_value = self.get_weighted_static_value(block["block_id"], "скобки_характеристика")
            template = template.replace("{скобки_характеристика}", brackets_value)
        else:
            template = template.replace("{скобки_характеристика}", "")

        # 5. Обрабатываем остальные статические переменные с взвешенным выбором
        # 5. Обрабатываем остальные статические переменные с адаптивным выбором
        for var_name in block.get("variables", []):
            # Пропускаем уже обработанные
            if var_name in ["скобки_характеристика", "значение_форматированное"]:
                continue

            placeholder = f"{{{var_name}}}"
            if placeholder in template:
                var_data = self.variable_manager.get_variable_data(block["block_id"], var_name)

                if var_data and var_data.get("type") == "ai":
                    # Уже обработали выше
                    continue
                else:
                    # Для всех типов переменных используем адаптивный выбор с контекстом
                    # Создаем упрощенный контекст для переменной
                    var_context = {
                        "категория": context.get("категория", ""),
                        "характеристика": context.get("характеристика", ""),
                        "значение": context.get("значение", ""),
                        "тип": context.get("тип", ""),
                        "block_id": block["block_id"],
                        "var_name": var_name
                    }

                    var_value = self.get_adaptive_static_value(block["block_id"], var_name, var_context)

                # Если переменная содержит плейсхолдеры, заменяем их
                if var_value and isinstance(var_value, str):
                    # Подставляем маркер если есть в контексте
                    if "{характеристика_маркер}" in var_value and "характеристика_маркер" in context:
                        var_value = var_value.replace("{характеристика_маркер}", context["характеристика_маркер"])
                    if "{маркер}" in var_value and "маркер" in context:
                        var_value = var_value.replace("{маркер}", context["маркер"])

                    # Подставляем другие переменные из контекста
                    for key, val in context.items():
                        placeholder_key = f"{{{key}}}"
                        if placeholder_key in var_value:
                            var_value = var_value.replace(placeholder_key, str(val))

                template = template.replace(placeholder, var_value)

                # Если переменная содержит плейсхолдеры, заменяем их
                if var_value and isinstance(var_value, str):
                    # Подставляем маркер если есть в контексте
                    if "{характеристика_маркер}" in var_value and "характеристика_маркер" in context:
                        var_value = var_value.replace("{характеристика_маркер}", context["характеристика_маркер"])
                    if "{маркер}" in var_value and "маркер" in context:
                        var_value = var_value.replace("{маркер}", context["маркер"])

                    # Подставляем другие переменные из контекста
                    for key, val in context.items():
                        placeholder_key = f"{{{key}}}"
                        if placeholder_key in var_value:
                            var_value = var_value.replace(placeholder_key, str(val))

                template = template.replace(placeholder, var_value)

        # 6. Заменяем оставшиеся плейсхолдеры маркера
        if "характеристика_маркер" in context:
            template = template.replace("{характеристика_маркер}", context["характеристика_маркер"])
        if "маркер" in context:
            template = template.replace("{маркер}", context["маркер"])

        # 7. Очищаем результат
        template = re.sub(r'\n{3,}', '\n\n', template.strip())

        return template


# --- Основное приложение фазы 4 ---
def main():
    st.set_page_config(page_title="Data Harvester Phase 4 - Генерация промптов", layout="wide")
    local_css()
    st.title("🚀 Фаза 4: Генерация промптов")
    st.markdown("---")

    # --- Инициализация менеджеров ---
    if 'block_manager' not in st.session_state:
        st.session_state.block_manager = BlockManager()

    if 'variable_manager' not in st.session_state:
        st.session_state.variable_manager = VariableManager(st.session_state.block_manager)

    if 'dynamic_var_manager' not in st.session_state:
        st.session_state.dynamic_var_manager = DynamicVariableManager()

    # Инициализация генератора
    if 'prompt_generator' not in st.session_state:
        st.session_state.prompt_generator = PromptGenerator(
            st.session_state.block_manager,
            st.session_state.variable_manager,
            st.session_state.dynamic_var_manager
        )

    if 'marker_rotator' not in st.session_state:
        st.session_state.marker_rotator = None

    # Инициализация переменных сессии
    if 'phase4_generated_prompts' not in st.session_state:
        st.session_state.phase4_generated_prompts = []

    if 'phase4_global_prompts' not in st.session_state:
        st.session_state.phase4_global_prompts = 3

    if 'phase4_char_settings' not in st.session_state:
        st.session_state.phase4_char_settings = {}

    if 'phase4_other_blocks_settings' not in st.session_state:
        st.session_state.phase4_other_blocks_settings = {}

    if 'phase4_page' not in st.session_state:
        st.session_state.phase4_page = 0

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

    # Проверяем наличие данных
    if not phase1_data or not phase1_data.get('characteristics'):
        st.error("""
        ## ❌ Данные фазы 1 не загружены

        Для работы фазы 4 необходимо выполнить фазу 1.

        **Решение:**
        1. Перейдите к фазе 1
        2. Загрузите JSON файл
        3. Выберите характеристики
        4. Нажмите "Сформировать итоговый массив"
        5. Вернитесь к фазе 4
        """)
        return

    # --- Боковая панель ---
    with st.sidebar:
        st.header("⚙️ Настройки фазы 4")

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
        st.header("🤖 Управление AI")

        if st.button("⚙️ Настройки AI", use_container_width=True):
            # Открываем интерфейс настроек AI
            st.session_state.show_ai_config = True

        if st.button("🔄 Перегенерировать AI-инструкции", use_container_width=True):
            # Здесь можно добавить логику перегенерации
            st.info("Функция перегенерации AI-инструкций")

        st.divider()
        # Глобальная настройка
        st.header("🎯 Глобальная настройка")

        global_prompts = st.number_input(
            "Промптов на значение (по умолчанию):",
            min_value=1,
            max_value=20,
            value=st.session_state.phase4_global_prompts,
            help="Будет применено ко всем характеристикам, если не настроено индивидуально"
        )

        if global_prompts != st.session_state.phase4_global_prompts:
            st.session_state.phase4_global_prompts = global_prompts
            st.rerun()

        # Кнопка применения глобальной настройки
        if st.button("📋 Применить ко всем характеристикам", use_container_width=True):
            if phase1_data and 'characteristics' in phase1_data:
                for char in phase1_data['characteristics']:
                    char_id = char.get('char_id', '')
                    if char_id:
                        if char_id not in st.session_state.phase4_char_settings:
                            st.session_state.phase4_char_settings[char_id] = {}
                        st.session_state.phase4_char_settings[char_id]['prompts_per_value'] = global_prompts
            st.success(f"Применено {global_prompts} промптов на значение для всех характеристик!")
            st.rerun()

        st.divider()

        # Управление
        if st.button("🔄 Сбросить ротацию маркеров", use_container_width=True):
            if markers:
                st.session_state.marker_rotator = MarkerRotator(markers)
                st.success("Ротация маркеров сброшена!")
                st.rerun()

        st.divider()
        st.header("🎲 Настройки рандомизации")

        # Режим рандомизации
        randomization_mode = st.selectbox(
            "Режим выбора значений:",
            ["adaptive", "uniform", "weighted_only"],
            index=0,
            format_func=lambda x: {
                "adaptive": "Адаптивный (учитывает использование)",
                "uniform": "Равномерный (чистый рандом)",
                "weighted_only": "Только по весам (старый режим)"
            }[x],
            help="Как выбирать значения переменных"
        )

        # Применяем режим
        if st.session_state.prompt_generator.randomization_mode != randomization_mode:
            st.session_state.prompt_generator.randomization_mode = randomization_mode
            st.rerun()

        # Сброс статистики использования
        if st.button("🔄 Сбросить статистику использования", use_container_width=True):
            st.session_state.prompt_generator.reset_usage_tracking()
            st.success("Статистика использования сброшена!")
            st.rerun()

        st.divider()


        st.divider()
        # (опционально) можно оставить ссылку на main_app
        if st.button("🏠 Вернуться к главному меню",
                     use_container_width=True,
                     type="secondary"):
            if 'current_phase' in st.session_state:
                st.session_state.current_phase = 1  # или сохранить текущую фазу
            st.rerun()

        # Переход к редактированию
        if st.button("📝 Перейти к редактированию блоков", use_container_width=True):
            # Здесь должна быть логика перехода к фазе 3
            st.info("Перейдите на страницу фазы 3 для редактирования блоков")
            st.page_link("phase3.py", label="Открыть фазу 3")

    # --- Основной контент ---
    show_generation_mode(phase1_data, category, markers)


def show_generation_mode(phase1_data, category, markers):
    """Основной режим - генерация промптов"""
    if 'selected_regular_block_id' not in st.session_state:
        st.session_state.selected_regular_block_id = None
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

    # Создаем отдельные блоки для unique и regular характеристик
    # Создаем отдельные блоки для unique и regular характеристик
    unique_blocks = {}
    regular_blocks = {}

    for block_id, block in characteristic_blocks.items():
        # Определяем тип характеристики по настройкам блока
        settings = block.get('settings', {})
        char_type = settings.get('characteristic_type', 'regular')

        if char_type == 'unique':
            unique_blocks[block_id] = block
        else:
            regular_blocks[block_id] = block

    # Для обратной совместимости: если по настройкам не нашли unique,
    # проверяем название (старая логика)
    if not unique_blocks:
        for block_id, block in characteristic_blocks.items():
            block_name = block.get('name', '').lower()
            if 'unique' in block_name:
                unique_blocks[block_id] = block

    # Остальные блоки считаем regular
    for block_id, block in characteristic_blocks.items():
        if block_id not in unique_blocks and block_id not in regular_blocks:
            regular_blocks[block_id] = block

    # Статистика по характеристикам
    with st.expander("📊 Настройка промптов для характеристик", expanded=True):
        st.write("**Настройте количество промптов для каждой характеристики:**")
        st.caption("Количество промптов, которые будут сгенерированы для КАЖДОГО значения характеристики")

        # Инициализируем словарь для хранения настроек промптов
        if 'phase4_char_settings' not in st.session_state:
            st.session_state.phase4_char_settings = {}

        # Глобальная настройка по умолчанию
        col_global1, col_global2 = st.columns([3, 1])
        with col_global1:
            st.markdown("**Глобальная настройка для всех характеристик:**")
        with col_global2:
            global_prompts = st.number_input(
                "Промптов на значение:",
                min_value=1,
                max_value=20,
                value=st.session_state.get('phase4_global_prompts', 3),
                key="global_prompts_input",
                label_visibility="collapsed"
            )

            if global_prompts != st.session_state.get('phase4_global_prompts', 3):
                st.session_state.phase4_global_prompts = global_prompts
                # Применяем глобальную настройку ко всем характеристикам
                for char in characteristics:
                    char_id = char.get('char_id', '')
                    if char_id:
                        st.session_state.phase4_char_settings[char_id] = {
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
            if char_id not in st.session_state.phase4_char_settings:
                st.session_state.phase4_char_settings[char_id] = {
                    'prompts_per_value': st.session_state.get('phase4_global_prompts', 3),
                    'char_name': char_name
                }

            # Получаем текущие настройки
            char_settings = st.session_state.phase4_char_settings[char_id]
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
                    st.session_state.phase4_char_settings[char_id]['prompts_per_value'] = prompts_per_value
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
                global_val = st.session_state.get('phase4_global_prompts', 3)
                for char_id in st.session_state.phase4_char_settings:
                    st.session_state.phase4_char_settings[char_id]['prompts_per_value'] = global_val
                st.rerun()

        with col_actions2:
            if st.button("⚡ Установить 1 для всех", use_container_width=True):
                for char_id in st.session_state.phase4_char_settings:
                    st.session_state.phase4_char_settings[char_id]['prompts_per_value'] = 1
                st.session_state.phase4_global_prompts = 1
                st.rerun()

        with col_actions3:
            if st.button("🚀 Установить 5 для всех", use_container_width=True):
                for char_id in st.session_state.phase4_char_settings:
                    st.session_state.phase4_char_settings[char_id]['prompts_per_value'] = 5
                st.session_state.phase4_global_prompts = 5
                st.rerun()

    # Настройка для других блоков
    if other_blocks:
        with st.expander("📝 Настройка других блоков (заголовок, описание, применение и т.д.)", expanded=True):
            st.write("**Настройте количество промптов для каждого блока:**")

            # Инициализируем настройки для других блоков
            if 'phase4_other_blocks_settings' not in st.session_state:
                st.session_state.phase4_other_blocks_settings = {}

            other_total_prompts = 0

            for block_id, block in other_blocks.items():
                block_name = block.get('name', block_id)

                # Инициализируем настройки для блока, если их нет
                if block_id not in st.session_state.phase4_other_blocks_settings:
                    st.session_state.phase4_other_blocks_settings[block_id] = {
                        'enabled': True,
                        'prompts_count': 3
                    }

                block_settings = st.session_state.phase4_other_blocks_settings[block_id]

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
                    st.session_state.phase4_other_blocks_settings[block_id]['enabled'] = enabled

                if prompts_count != block_settings.get('prompts_count', 3):
                    st.session_state.phase4_other_blocks_settings[block_id]['prompts_count'] = prompts_count

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
                        st.session_state.phase4_other_blocks_settings[block_id]['enabled'] = True
                    st.rerun()

            with col_actions2:
                if st.button("❌ Выключить все блоки", use_container_width=True):
                    for block_id in other_blocks:
                        st.session_state.phase4_other_blocks_settings[block_id]['enabled'] = False
                    st.rerun()

            with col_actions3:
                if st.button("🚀 3 промпта для всех", use_container_width=True):
                    for block_id in other_blocks:
                        st.session_state.phase4_other_blocks_settings[block_id]['prompts_count'] = 3
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
            if st.button("📝 Перейти к редактированию", use_container_width=True):
                st.page_link("phase3.py", label="Открыть фазу 3")

        with col3:
            if st.button("🚀 Создать шаблоны характеристик", type="primary", use_container_width=True):
                # Создаем стандартные блоки для unique и regular характеристик

                # Regular шаблон
                regular_block_id, regular_block, regular_variables = st.session_state.block_manager.create_new_block()
                regular_block.update({
                    "block_id": "characteristic_regular_template",
                    "name": "Шаблон для Regular характеристики",
                    "description": "Шаблон для regular характеристик",
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
                        "добавлять_скобки_переменную": True,
                        "characteristic_type": "regular"
                    }
                })

                # Unique шаблон
                unique_block_id, unique_block, unique_variables = st.session_state.block_manager.create_new_block()
                unique_block.update({
                    "block_id": "characteristic_unique_template",
                    "name": "Шаблон для Unique характеристики",
                    "description": "Шаблон для unique характеристик",
                    "block_type": "characteristic",
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

                # Сохраняем оба шаблона
                st.session_state.block_manager.save_block(regular_block, regular_variables)
                st.session_state.block_manager.save_block(unique_block, unique_variables)
                st.session_state.block_manager.load_blocks()
                st.success("✅ Шаблоны для regular и unique характеристик созданы!")
                st.rerun()

        return

    # Показываем информацию о доступных блоках
    st.success(f"✅ Доступно шаблонов для характеристик: {len(characteristic_blocks)}")
    st.info(f"📋 Из них: {len(regular_blocks)} для regular, {len(unique_blocks)} для unique характеристик")

    if other_blocks:
        st.success(f"✅ Доступно других блоков: {len(other_blocks)}")

    # Выбор блока для regular характеристик
    # Выбор блока для regular характеристик
    if regular_blocks:
        regular_block_ids = list(regular_blocks.keys())

        # Инициализация в session_state, если нет
        if 'selected_regular_block_id' not in st.session_state:
            # По умолчанию выбираем первый блок
            st.session_state.selected_regular_block_id = regular_block_ids[0]

        # Проверяем, что сохраненный ID все еще существует
        if st.session_state.selected_regular_block_id not in regular_block_ids:
            st.session_state.selected_regular_block_id = regular_block_ids[0]

        selected_regular_block_id = st.selectbox(
            "Выберите шаблон для Regular характеристик:",
            regular_block_ids,
            format_func=lambda x: regular_blocks[x].get("name", x),
            key="regular_block_selector"
        )

        # Сохраняем выбор
        if selected_regular_block_id != st.session_state.selected_regular_block_id:
            st.session_state.selected_regular_block_id = selected_regular_block_id
            st.rerun()
    else:
        selected_regular_block_id = None

    # Выбор блока для unique характеристик
    if unique_blocks:
        unique_block_ids = list(unique_blocks.keys())

        # Инициализация в session_state, если нет
        if 'selected_unique_block_id' not in st.session_state:
            st.session_state.selected_unique_block_id = unique_block_ids[0]

        # Проверяем, что сохраненный ID все еще существует
        if st.session_state.selected_unique_block_id not in unique_block_ids:
            st.session_state.selected_unique_block_id = unique_block_ids[0]

        selected_unique_block_id = st.selectbox(
            "Выберите шаблон для Unique характеристик:",
            unique_block_ids,
            format_func=lambda x: unique_blocks[x].get("name", x),
            key="unique_block_selector"
        )

        # Сохраняем выбор
        if selected_unique_block_id != st.session_state.selected_unique_block_id:
            st.session_state.selected_unique_block_id = selected_unique_block_id
            st.rerun()
    else:
        selected_unique_block_id = selected_regular_block_id if regular_blocks else None
        if selected_unique_block_id:
            st.warning("⚠️ Не найден шаблон для unique характеристик. Будет использован шаблон для regular.")

    # Генерация промптов
    st.subheader("3. Генерация промптов")

    # Показываем предварительный расчет
    total_char_prompts = 0
    for char in characteristics:
        char_id = char.get('char_id', '')
        values_count = len(char.get('values', []))
        char_settings = st.session_state.phase4_char_settings.get(char_id, {})
        prompts_per_value = char_settings.get('prompts_per_value', st.session_state.get('phase4_global_prompts', 3))
        total_char_prompts += values_count * prompts_per_value

    total_other_prompts = 0
    if other_blocks:
        for block_id, settings in st.session_state.phase4_other_blocks_settings.items():
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
            # Сбрасываем ротатор маркеров перед новой генерацией
            if markers:
                st.session_state.marker_rotator = MarkerRotator(markers)

            # НОВОЕ: Сбрасываем статистику использования (опционально)
            # Раскомментируйте если хотите сбрасывать статистику при каждой генерации:
            st.session_state.prompt_generator.reset_usage_tracking()

            all_prompts = []

            # 1. Генерируем промпты для характеристик
            for char in characteristics:
                char_id = char.get('char_id', '')
                char_type = "unique" if char.get("is_unique", False) else "regular"

                # Выбираем соответствующий блок
                if char_type == "unique" and unique_blocks:
                    selected_block_id = st.session_state.selected_unique_block_id
                else:
                    selected_block_id = st.session_state.selected_regular_block_id

                # Получаем настройки для этой характеристики
                char_settings = st.session_state.phase4_char_settings.get(char_id, {})
                prompts_per_value = char_settings.get('prompts_per_value',
                                                      st.session_state.get('phase4_global_prompts', 3))

                # Генерируем промпты
                prompts = st.session_state.prompt_generator.generate_prompts_for_characteristic(
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
                for block_id, settings in st.session_state.phase4_other_blocks_settings.items():
                    if settings.get('enabled', False) and block_id in other_blocks:
                        block = other_blocks[block_id]
                        prompts_count = settings.get('prompts_count', 3)

                        # Генерируем промпты для блока
                        prompts = st.session_state.prompt_generator.generate_prompts_for_block(
                            block=block,
                            num_prompts=prompts_count,
                            category=category,
                            markers=markers,
                            marker_rotator=st.session_state.marker_rotator
                        )

                        all_prompts.extend(prompts)

            # Сохраняем промпты в session_state
            st.session_state.phase4_generated_prompts = all_prompts

            # Показываем статистику
            st.success(f"✅ Сгенерировано {len(all_prompts)} промптов!")
            if other_blocks:
                char_prompts = len([p for p in all_prompts if p.get('type') in ['regular', 'unique']])
                other_prompts = len([p for p in all_prompts if p.get('block_type') == 'other'])
                st.success(
                    f"📊 В том числе: {char_prompts} промптов для характеристик, {other_prompts} промптов для других блоков")

            # Сохраняем в общие данные приложения
            if 'app_data' in st.session_state:
                st.session_state.app_data['phase4'] = {
                    'prompts': all_prompts,
                    'category': category,
                    'markers': markers,
                    'characteristics_count': len(characteristics),
                    'other_blocks_count': len(other_blocks) if other_blocks else 0,
                    'total_prompts': len(all_prompts),
                    'char_settings': st.session_state.phase4_char_settings,
                    'other_blocks_settings': st.session_state.phase4_other_blocks_settings
                }

            # Автоскролл к результатам
            st.rerun()

    # Показать сгенерированные промпты
    if st.session_state.phase4_generated_prompts:
        st.subheader("📋 Сгенерированные промпты")

        # Фильтрация
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            # Собираем уникальные имена характеристик и блоков
            char_names = list(set(p['characteristic_name'] for p in st.session_state.phase4_generated_prompts if
                                  'characteristic_name' in p))
            block_names = list(
                set(p['block_name'] for p in st.session_state.phase4_generated_prompts if 'block_name' in p))

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
        filtered_prompts = st.session_state.phase4_generated_prompts

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
        st.caption(f"Показано {len(filtered_prompts)} из {len(st.session_state.phase4_generated_prompts)} промптов")

        # Пагинация
        total_pages = max(1, (len(filtered_prompts) + items_per_page - 1) // items_per_page)

        col_pag1, col_pag2, col_pag3 = st.columns([1, 3, 1])
        with col_pag1:
            if st.button("◀️ Предыдущая", disabled=st.session_state.phase4_page == 0):
                st.session_state.phase4_page -= 1
                st.rerun()

        with col_pag2:
            st.write(f"Страница {st.session_state.phase4_page + 1} из {total_pages}")

        with col_pag3:
            if st.button("Следующая ▶️", disabled=st.session_state.phase4_page >= total_pages - 1):
                st.session_state.phase4_page += 1
                st.rerun()

        # Показываем промпты для текущей страницы
        start_idx = st.session_state.phase4_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(filtered_prompts))

        for i, prompt_data in enumerate(filtered_prompts[start_idx:end_idx]):
            # Определяем заголовок для промпта
            if 'characteristic_name' in prompt_data:
                title = f"Характеристика: {prompt_data['characteristic_name']} = {prompt_data['value']} ({prompt_data['type']})"
            else:
                title = f"Блок: {prompt_data['block_name']} (промпт {prompt_data['prompt_num']})"

            with st.expander(f"Промпт #{start_idx + i + 1}: {title}", expanded=False):
                st.markdown(prompt_data['prompt'], unsafe_allow_html=False)

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

        # Экспорт промптов
        st.divider()
        st.subheader("💾 Экспорт данных")

        col_export1, col_export2 = st.columns(2)
        with col_export1:
            # Экспорт промпты в JSON
            export_data = {
                'category': category,
                'total_prompts': len(st.session_state.phase4_generated_prompts),
                'prompts': st.session_state.phase4_generated_prompts[:100]  # Ограничиваем для размера файла
            }

            st.download_button(
                label="📥 Скачать промпты (JSON)",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"prompts_{category}.json",
                mime="application/json",
                use_container_width=True,
                key="download_prompts"
            )

        with col_export2:
            # Сохранение настроек
            if st.button("💾 Сохранить настройки генерации", use_container_width=True, key="save_generation_settings"):
                st.session_state.phase4_settings = {
                    'char_settings': st.session_state.phase4_char_settings,
                    'other_blocks_settings': st.session_state.phase4_other_blocks_settings,
                    'selected_regular_block_id': st.session_state.selected_regular_block_id,
                    'selected_unique_block_id': st.session_state.selected_unique_block_id,
                    'global_prompts': st.session_state.phase4_global_prompts
                }
                st.success("✅ Настройки сохранены!")

        st.divider()
        # Вместо текущего expander'а "Статистика использования значений" используйте:
        with st.expander("📊 Детальная статистика использования значений", expanded=False):
            if st.button("📈 Показать детальную статистику", key="show_detailed_stats"):
                # Собираем статистику по всем блокам
                all_stats = []

                # Проверяем, есть ли данные в трекере
                tracker = st.session_state.prompt_generator.usage_tracker

                if tracker.history:
                    for key, history_list in tracker.history.items():
                        # Разбираем ключ
                        parts = key.split(":")
                        if len(parts) >= 2:
                            block_id = parts[0]
                            var_name = parts[1]

                            # Получаем блок
                            block = st.session_state.block_manager.get_block(block_id)
                            block_name = block.get('name', block_id) if block else block_id

                            # Анализируем историю
                            if history_list:
                                last_value = history_list[-1] if history_list else "нет"
                                usage_count = len(history_list)

                                all_stats.append({
                                    "Блок": block_name,
                                    "Переменная": var_name,
                                    "Последнее значение": last_value,
                                    "Использований": usage_count
                                })

                    if all_stats:
                        st.dataframe(all_stats, use_container_width=True)
                    else:
                        st.info("Статистика использования пока пуста")
                else:
                    st.info("Статистика использования пока не собрана")



if __name__ == "__main__":
    main()