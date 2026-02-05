import streamlit as st
import re
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict


class VariableManager:
    """Управление системными переменными"""

    def __init__(self):
        self.variables_dir = Path("config/variables")
        self.variables_dir.mkdir(parents=True, exist_ok=True)

        # Дефолтные переменные
        self.default_system_vars = {
            "город": {
                "variants": [
                    {"value": "{system городе}", "context": "в [город]е"},
                    {"value": "{system по_городу}", "context": "по [город]у"},
                    {"value": "{system город}", "context": "[город]"}
                ],
                "description": "Название города"
            },
            "название товара": {
                "variants": [{"value": "{system название_товара}", "context": ""}],
                "description": "Название товара"
            },
            "цена": {
                "variants": [{"value": "{system цена_товара}, руб.", "context": ""}],
                "description": "Цена товара"
            },
            "единица измерения": {
                "variants": [{"value": "{system количество}", "context": ""}],
                "description": "Единица измерения"
            },
            "телефон": {
                "variants": [{"value": "8 495 969-51-08", "context": ""}],
                "description": "Телефон компании"
            },
            "email": {
                "variants": [{"value": "msk@steelborg.ru", "context": ""}],
                "description": "Email компании"
            },
            "компания": {
                "variants": [{"value": "Steelborg", "context": ""}],
                "description": "Название компании"
            },
            "категория РП": {
                "variants": [{"value": "{system название_категории_РП}", "context": ""}],
                "description": "Категория в родительном падеже"
            },
            "категория ВП": {
                "variants": [{"value": "{system название_категории_ВП}", "context": ""}],
                "description": "Категория в винительном падеже"
            },
            "категория ИП": {
                "variants": [{"value": "{system название_категории}", "context": ""}],
                "description": "Категория в именительном падеже"
            }
        }

        self.system_vars = {}
        self.load_variables()

    def load_variables(self):
        """Загружает переменные из файла или создает дефолтные"""
        var_file = self.variables_dir / "system_variables.json"

        if var_file.exists():
            try:
                with open(var_file, 'r', encoding='utf-8') as f:
                    self.system_vars = json.load(f)
            except:
                self.system_vars = self.default_system_vars
                self.save_variables()
        else:
            self.system_vars = self.default_system_vars
            self.save_variables()

    def save_variables(self):
        """Сохраняет переменные в файл"""
        var_file = self.variables_dir / "system_variables.json"
        with open(var_file, 'w', encoding='utf-8') as f:
            json.dump(self.system_vars, f, ensure_ascii=False, indent=2)

    def get_variable_variants(self, var_name: str) -> List[Dict]:
        """Возвращает варианты для переменной"""
        var_info = self.system_vars.get(var_name)
        if var_info:
            return var_info.get("variants", [])
        return []

    def get_best_variant(self, var_name: str, context: str) -> str:
        """Выбирает лучший вариант переменной по контексту"""
        variants = self.get_variable_variants(var_name)
        if not variants:
            return f"{{system {var_name}}}"

        if len(variants) == 1:
            return variants[0]["value"]

        context_lower = context.lower()
        for variant in variants:
            variant_context = variant.get("context", "").lower()
            if variant_context and variant_context in context_lower:
                return variant["value"]

        return variants[0]["value"]

    def add_variable(self, name: str, variants: List[Dict], description: str = ""):
        """Добавляет новую переменную"""
        self.system_vars[name] = {
            "variants": variants,
            "description": description
        }
        self.save_variables()

    def edit_variable(self, old_name: str, new_name: str, variants: List[Dict], description: str = ""):
        """Редактирует переменную"""
        if old_name in self.system_vars:
            self.system_vars[new_name] = {
                "variants": variants,
                "description": description
            }
            if old_name != new_name:
                del self.system_vars[old_name]
            self.save_variables()

    def delete_variable(self, name: str):
        """Удаляет переменную"""
        if name in self.system_vars:
            del self.system_vars[name]
            self.save_variables()


class TextProcessor:
    """Обработка текстов и вставка переменных"""

    def __init__(self, variable_manager: VariableManager):
        self.vm = variable_manager
        self.pattern = re.compile(r'\[([^\]]+)\]')

    def extract_variables(self, text: str) -> List[Tuple[str, int, int]]:
        """Извлекает все переменные из текста в формате [переменная]"""
        matches = []
        for match in self.pattern.finditer(text):
            var_name = match.group(1).strip()
            start, end = match.span()
            matches.append((var_name, start, end))
        return matches

    def process_block(self, block: Dict, characteristics: List[Dict]) -> Dict:
        """Обрабатывает один текстовый блок"""
        original_text = block.get("edited_text", "")
        block_type = block.get("type", "")
        char_name = block.get("characteristic_name", "")
        char_value = block.get("characteristic_value", "")

        variables = self.extract_variables(original_text)
        processed_text = original_text
        replacements = []
        errors = []
        warnings = []
        offset = 0

        for var_name, start, end in variables:
            original_var = original_text[start:end]

            if block_type == "regular":
                if not char_name:
                    errors.append(f"Regular блок без characteristic_name: {original_var}")
                    replacement = f"{{prop {var_name}}}"
                else:
                    char_found = False
                    for char in characteristics:
                        if char.get("name") == char_name or char.get("value") == var_name:
                            replacement = f"{{prop {char_name}}}"
                            char_found = True
                            break

                    if not char_found:
                        errors.append(f"Не найдена характеристика '{char_name}' для: {original_var}")
                        replacement = f"{{prop {char_name}}}"
            else:
                replacement = self.vm.get_best_variant(var_name, original_text[max(0, start - 10):end + 10])

            new_start = start + offset
            new_end = end + offset
            processed_text = processed_text[:new_start] + replacement + processed_text[new_end:]
            offset += len(replacement) - (end - start)

            replacements.append({
                "original": original_var,
                "replacement": replacement,
                "position": (start, end)
            })

        if block_type == "regular" and not variables:
            errors.append("Regular блок должен содержать хотя бы одну переменную в квадратных скобках []")

        return {
            "original_text": original_text,
            "processed_text": processed_text,
            "replacements": replacements,
            "errors": errors,
            "warnings": warnings,
            "has_errors": len(errors) > 0,
            "has_warnings": len(warnings) > 0,
            "variables_count": len(variables)
        }


@dataclass
class FragmentBlock:
    """Класс для хранения информации о блоке фрагмента"""
    id: str
    fragment_name: str  # Название блока (например: Категория_Диаметр)
    original_text: str
    processed_text: str
    block_type: str  # regular, unique, other
    characteristic_name: Optional[str] = None
    characteristic_value: Optional[str] = None
    category: Optional[str] = None
    properties: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'id': self.id,
            'fragment_name': self.fragment_name,
            'original_text': self.original_text,
            'processed_text': self.processed_text,
            'block_type': self.block_type,
            'characteristic_name': self.characteristic_name,
            'characteristic_value': self.characteristic_value,
            'category': self.category,
            'properties': self.properties,
            'errors': self.errors,
            'warnings': self.warnings
        }


class EnhancedTextProcessor(TextProcessor):
    """Расширенный процессор текстов с автоматической подстановкой"""

    def __init__(self, variable_manager: VariableManager):
        super().__init__(variable_manager)

    def smart_process_block(self, block: Dict, characteristics: List[Dict]) -> Dict:
        """Умная обработка блока с автоматической подстановкой"""

        original_text = block.get("edited_text", "")
        block_type = block.get("type", "")
        char_name = block.get("characteristic_name", "")
        char_value = block.get("characteristic_value", "")

        # Извлекаем переменные
        variables = self.extract_variables(original_text)

        # Если нет переменных в regular блоке, пытаемся найти значение
        if block_type == 'regular' and not variables and char_name:
            # Ищем соответствующее значение в характеристиках
            matching_chars = []
            for char in characteristics:
                if char.get("name") == char_name:
                    # Нашли характеристику, теперь ищем значения
                    char_data = char.get("data", {})
                    if isinstance(char_data, dict):
                        # Для словаря значений
                        for key, value in char_data.items():
                            if key and value:
                                matching_chars.append({
                                    'name': char_name,
                                    'value': value,
                                    'key': key
                                })
                    elif isinstance(char_data, list):
                        # Для списка значений
                        for item in char_data:
                            if isinstance(item, dict) and 'value' in item:
                                matching_chars.append({
                                    'name': char_name,
                                    'value': item['value'],
                                    'key': item.get('key', '')
                                })

            # Если нашли значения, формируем варианты подстановки
            if matching_chars:
                # Создаем несколько вариантов текста
                variants = []
                for match in matching_chars:
                    # Формируем текст с подстановкой
                    variant_text = original_text + f" [{match['value']}]"
                    variants.append({
                        'text': variant_text,
                        'value': match['value'],
                        'key': match['key']
                    })

                return {
                    'original_text': original_text,
                    'processed_text': '',  # Будет определен позже
                    'variants': variants,
                    'has_variants': True,
                    'char_name': char_name,
                    'char_values': [v['value'] for v in variants],
                    'errors': [],
                    'warnings': ["Найдены возможные значения для подстановки"]
                }

        # Обычная обработка
        return self.process_block(block, characteristics)


class FragmentManager:
    """Управление фрагментами и их свойствами"""

    def __init__(self, category: str):
        self.category = category
        self.fragments: List[FragmentBlock] = []
        self.fragment_names: Set[str] = set()  # Уникальные названия фрагментов
        self.fragment_properties: Dict[str, List[Dict]] = defaultdict(list)  # fragment_name -> свойства
        self.template_order: List[str] = []  # Порядок фрагментов в шаблоне

    def add_block(self, block_data: Dict) -> FragmentBlock:
        """Добавляет блок и формирует его название по правилам"""

        # Определяем базовое название по типу блока
        if block_data.get('type') == 'regular':
            # Regular: Категория_характеристика
            char_name = block_data.get('characteristic_name', '')
            fragment_name = f"{self.category}_{char_name}" if char_name else f"{self.category}_unknown"

        elif block_data.get('type') == 'unique':
            # Unique: Категория_характеристика_значение
            char_name = block_data.get('characteristic_name', '')
            char_value = block_data.get('characteristic_value', '')

            # Очищаем значение для использования в названии
            clean_value = self._clean_value_for_name(char_value)

            if char_name and clean_value:
                fragment_name = f"{self.category}_{char_name}_{clean_value}"
            elif char_name:
                fragment_name = f"{self.category}_{char_name}"
            else:
                fragment_name = f"{self.category}_unique_unknown"

        else:  # other
            # Other: Категория_название_блока
            block_name = block_data.get('block_name', '')
            if block_name:
                clean_name = self._clean_value_for_name(block_name)
                fragment_name = f"{self.category}_{clean_name}"
            else:
                fragment_name = f"{self.category}_other"

        # Создаем объект блока
        fragment_block = FragmentBlock(
            id=block_data.get('id', f"block_{len(self.fragments)}"),
            fragment_name=fragment_name,
            original_text=block_data.get('original_text', ''),
            processed_text=block_data.get('processed_text', ''),
            block_type=block_data.get('type', 'unknown'),
            characteristic_name=block_data.get('characteristic_name'),
            characteristic_value=block_data.get('characteristic_value'),
            category=self.category,
            errors=block_data.get('errors', []),
            warnings=block_data.get('warnings', [])
        )

        # Формируем свойства фрагмента
        self._extract_properties(fragment_block)

        # Добавляем блок
        self.fragments.append(fragment_block)
        self.fragment_names.add(fragment_name)

        return fragment_block

    def _clean_value_for_name(self, value: str) -> str:
        """Очищает значение для использования в названии фрагмента"""
        if not value:
            return ""

        # Заменяем недопустимые символы на _
        cleaned = re.sub(r'[^\w\s-]', '', value.lower())
        cleaned = re.sub(r'[\s-]+', '_', cleaned)
        cleaned = cleaned.strip('_')

        # Ограничиваем длину
        if len(cleaned) > 50:
            cleaned = cleaned[:50]

        return cleaned

    def update_template_order(self, old_name: str, new_name: str):
        """Обновляет порядок фрагментов при переименовании"""
        if old_name in self.template_order:
            index = self.template_order.index(old_name)
            self.template_order[index] = new_name

    def remove_from_template_order(self, fragment_names: List[str]):
        """Удаляет фрагменты из порядка"""
        self.template_order = [name for name in self.template_order if name not in fragment_names]

    def add_to_template_order(self, fragment_name: str, position: int = -1):
        """Добавляет фрагмент в порядок"""
        if fragment_name not in self.template_order:
            if position == -1:
                self.template_order.append(fragment_name)
            else:
                self.template_order.insert(position, fragment_name)
    def _extract_properties(self, fragment: FragmentBlock):
        """Извлекает свойства из фрагмента"""
        properties = []

        if fragment.block_type == 'regular':
            # Для regular: характеристика без значения (значение будет подставляться)
            if fragment.characteristic_name:
                properties.append({
                    'characteristic': fragment.characteristic_name,
                    'value': None,  # Значение будет из данных товара
                    'is_unique': False
                })

        elif fragment.block_type == 'unique':
            # Для unique: характеристика и уникальное значение
            if fragment.characteristic_name and fragment.characteristic_value:
                properties.append({
                    'characteristic': fragment.characteristic_name,
                    'value': fragment.characteristic_value,
                    'is_unique': True
                })

        # Добавляем свойства в фрагмент и в общий пул
        fragment.properties = properties
        for prop in properties:
            self.fragment_properties[fragment.fragment_name].append(prop)

    def merge_fragments(self, fragment_names: List[str], new_name: str):
        """Склеивает несколько фрагментов в один"""
        if not fragment_names or len(fragment_names) < 2:
            return False

        # Проверяем, что все фрагменты существуют
        for frag_name in fragment_names:
            if frag_name not in self.fragment_names:
                return False

        # Обновляем названия у соответствующих блоков
        for fragment in self.fragments:
            if fragment.fragment_name in fragment_names:
                fragment.fragment_name = new_name

        # Обновляем список уникальных названий
        self.fragment_names.difference_update(fragment_names)
        self.fragment_names.add(new_name)

        # Обновляем свойства
        merged_properties = []
        for frag_name in fragment_names:
            if frag_name in self.fragment_properties:
                merged_properties.extend(self.fragment_properties[frag_name])
                del self.fragment_properties[frag_name]

        if merged_properties:
            self.fragment_properties[new_name] = merged_properties

        # Обновляем порядок в шаблоне
        # Находим первую позицию из сливаемых фрагментов
        positions = [i for i, name in enumerate(self.template_order) if name in fragment_names]
        if positions:
            first_position = min(positions)
            # Удаляем старые названия
            self.template_order = [name for name in self.template_order if name not in fragment_names]
            # Вставляем новое название на позицию первого удаленного
            self.template_order.insert(first_position, new_name)
        else:
            # Если не нашли в порядке, добавляем в конец
            self.template_order.append(new_name)

        return True

    def rename_fragment(self, old_name: str, new_name: str):
        """Переименовывает фрагмент"""
        if old_name not in self.fragment_names:
            return False

        # Обновляем названия у блоков
        for fragment in self.fragments:
            if fragment.fragment_name == old_name:
                fragment.fragment_name = new_name

        # Обновляем списки
        self.fragment_names.remove(old_name)
        self.fragment_names.add(new_name)

        # Обновляем свойства
        if old_name in self.fragment_properties:
            self.fragment_properties[new_name] = self.fragment_properties.pop(old_name)

        # Обновляем порядок в шаблоне
        if old_name in self.template_order:
            index = self.template_order.index(old_name)
            self.template_order[index] = new_name

        return True

    def get_fragment_blocks(self, fragment_name: str) -> List[FragmentBlock]:
        """Возвращает все блоки с указанным названием фрагмента"""
        return [f for f in self.fragments if f.fragment_name == fragment_name]

    def get_all_properties_table(self) -> List[Dict]:
        """Возвращает таблицу всех свойств фрагментов"""
        table_data = []

        for fragment_name in sorted(self.fragment_names):
            blocks = self.get_fragment_blocks(fragment_name)

            for block in blocks:
                for prop in block.properties:
                    row = {
                        'fragment_name': fragment_name,
                        'characteristic': prop['characteristic'],
                        'value': prop['value'],
                        'block_type': block.block_type
                    }
                    table_data.append(row)

            # Если у фрагмента нет свойств, добавляем пустую строку
            if not any(b.properties for b in blocks):
                table_data.append({
                    'fragment_name': fragment_name,
                    'characteristic': None,
                    'value': None,
                    'block_type': blocks[0].block_type if blocks else 'unknown'
                })

        return table_data

    def get_fragments_table(self) -> List[Dict]:
        """Возвращает таблицу фрагментов"""
        table_data = []

        for fragment_name in sorted(self.fragment_names):
            blocks = self.get_fragment_blocks(fragment_name)
            block_types = list(set(b.block_type for b in blocks))

            table_data.append({
                'fragment_name': fragment_name,
                'block_count': len(blocks),
                'block_types': ', '.join(block_types),
                'has_errors': any(b.errors for b in blocks),
                'has_warnings': any(b.warnings for b in blocks)
            })

        return table_data

    def generate_template_strings(self, category_code: str = None) -> Dict:
        """Генерирует строки шаблонов"""
        if category_code is None:
            category_code = self.category

        # Формируем переменные фрагментов ТОЛЬКО для существующих фрагментов
        fragment_vars = {}
        for fragment_name in self.fragment_names:
            var_name = f"{{fragment {fragment_name}}}"
            fragment_vars[fragment_name] = var_name

        # Формируем шаблон по умолчанию из текущего порядка
        if not self.template_order:
            self.template_order = sorted(self.fragment_names)

        default_order = sorted(self.fragment_names)  # ← ДОБАВИТЬ ЭТУ СТРОКУ!

        default_template = " ".join(fragment_vars[name] for name in self.template_order
                                    if name in fragment_vars)

        return {
            'category_code': category_code,
            'fragment_variables': fragment_vars,
            'default_order': default_order,  # ← ДОБАВИТЬ ЭТОТ КЛЮЧ!
            'current_order': self.template_order,
            'default_template': default_template
        }


class Phase6EnhancedProcessor:
    """Улучшенный процессор фазы 6 с подготовкой данных для сайта"""

    def __init__(self, app_state, input_data=None):
        self.app_state = app_state
        self.input_data = input_data or {}
        self.vm = VariableManager()
        self.text_processor = EnhancedTextProcessor(self.vm)

        # Получаем категорию
        self.category = self.input_data.get('category', '')
        if not self.category:
            # Пытаемся извлечь из phase1_data
            phase1_data = self.input_data.get('phase1_data', {})
            self.category = phase1_data.get('category', 'Без_категории')

        # Инициализируем менеджер фрагментов
        self.fragment_manager = FragmentManager(self.category)

        # Инициализация session_state
        if 'phase6_enhanced_data' not in st.session_state:
            st.session_state.phase6_enhanced_data = {
                'fragments_processed': False,
                'fragment_blocks': [],
                'template_order': [],
                'category_code': self.category,
                'merges': {},  # Информация о склеенных фрагментах
                'manual_corrections': {}  # Ручные исправления
            }

    def debug_fragment_manager(self):
        """Метод для отладки fragment_manager"""
        if not hasattr(self, 'fragment_manager') or not self.fragment_manager:
            st.error("❌ fragment_manager не инициализирован")
            return

        st.write("### 🔍 Отладка FragmentManager")

        # 1. Проверяем fragment_names
        fragment_names = list(self.fragment_manager.fragment_names)
        st.write(f"**Количество fragment_names:** {len(fragment_names)}")

        if fragment_names:
            st.write("**Список фрагментов:**")
            for i, name in enumerate(fragment_names[:10]):  # Показываем первые 10
                st.write(f"{i + 1}. {name}")

            # 2. Проверяем fragment_blocks для первого фрагмента
            first_fragment = fragment_names[0]
            blocks = self.fragment_manager.get_fragment_blocks(first_fragment)
            st.write(f"**Блоки для фрагмента '{first_fragment}':** {len(blocks)}")

            if blocks:
                st.write("**Первый блок:**")
                st.json(blocks[0].to_dict())

        # 3. Проверяем fragments
        if hasattr(self.fragment_manager, 'fragments'):
            st.write(f"**Общее количество блоков в fragments:** {len(self.fragment_manager.fragments)}")

            if self.fragment_manager.fragments:
                st.write("**Структура первого блока:**")
                st.write(vars(self.fragment_manager.fragments[0]))

        # 4. Проверяем fragment_properties
        if hasattr(self.fragment_manager, 'fragment_properties'):
            st.write(f"**Количество свойств:** {len(self.fragment_manager.fragment_properties)}")

            if self.fragment_manager.fragment_properties:
                st.write("**Пример свойств:**")
                for frag_name, props in list(self.fragment_manager.fragment_properties.items())[:3]:
                    st.write(f"• {frag_name}: {len(props)} свойств")

    def display_fragment_naming_interface(self):
        """Интерфейс для управления названиями фрагментов"""
        st.header("🏷️ Названия фрагментов")

        # Проверяем наличие менеджера фрагментов
        if not hasattr(self, 'fragment_manager') or not self.fragment_manager:
            st.error("❌ Менеджер фрагментов не инициализирован")
            if st.button("🔄 Восстановить менеджер фрагментов"):
                if 'fragment_manager' in st.session_state.phase6_enhanced_data:
                    self.fragment_manager = st.session_state.phase6_enhanced_data['fragment_manager']
                    st.rerun()
            return

        # Получаем фрагменты
        fragment_names = list(self.fragment_manager.fragment_names)

        if not fragment_names:
            st.info("Нет фрагментов для отображения. Обработайте данные в основном интерфейсе.")
            return

        # Таблица всех фрагментов
        fragments_table = self.fragment_manager.get_fragments_table()

        df_fragments = pd.DataFrame(fragments_table)

        # Отображаем таблицу
        st.write(f"**Всего фрагментов:** {len(fragment_names)}")
        st.dataframe(df_fragments, use_container_width=True)

        # Редактирование названий
        st.subheader("✏️ Редактирование названий")

        col1, col2 = st.columns([2, 1])

        with col1:
            selected_fragment = st.selectbox(
                "Выберите фрагмент для переименования:",
                sorted(fragment_names),
                key="rename_fragment_select"
            )

        with col2:
            new_name = st.text_input(
                "Новое название:",
                value=selected_fragment,
                key="rename_fragment_input"
            )

        if st.button("🔄 Переименовать", key="rename_fragment_btn"):
            if new_name and new_name != selected_fragment:
                if self.fragment_manager.rename_fragment(selected_fragment, new_name):
                    st.success(f"Фрагмент переименован: {selected_fragment} → {new_name}")
                    st.rerun()
                else:
                    st.error("Ошибка при переименовании")

        # Склеивание фрагментов
        st.subheader("🔗 Склеивание фрагментов")

        # Выбор фрагментов для склеивания
        selected_to_merge = st.multiselect(
            "Выберите фрагменты для склеивания (2 и более):",
            sorted(fragment_names),
            key="fragments_to_merge"
        )

        new_merged_name = st.text_input(
            "Название объединенного фрагмента:",
            value=f"{self.category}_объединенный",
            key="merged_fragment_name"
        )

        if st.button("🔗 Склеить выбранные", key="merge_fragments_btn"):
            if len(selected_to_merge) >= 2 and new_merged_name:
                if self.fragment_manager.merge_fragments(selected_to_merge, new_merged_name):
                    # Сохраняем информацию о склейке
                    merges = st.session_state.phase6_enhanced_data.get('merges', {})
                    merges[new_merged_name] = selected_to_merge
                    st.session_state.phase6_enhanced_data['merges'] = merges

                    # Обновляем менеджер в session_state
                    st.session_state.phase6_enhanced_data['fragment_manager'] = self.fragment_manager

                    st.success(f"Склеено {len(selected_to_merge)} фрагментов в '{new_merged_name}'")
                    st.rerun()
                else:
                    st.error("Ошибка при склеивании фрагментов")
            else:
                st.warning("Выберите минимум 2 фрагмента и укажите название")

    def display_fragment_properties_interface(self):
        """Интерфейс для просмотра свойств фрагментов"""
        st.header("📊 Свойства фрагментов")

        # Получаем таблицу свойств
        properties_table = self.fragment_manager.get_all_properties_table()

        if not properties_table:
            st.info("Нет данных о свойствах")
            return

        df_properties = pd.DataFrame(properties_table)

        # Фильтрация
        col1, col2 = st.columns(2)

        with col1:
            filter_type = st.selectbox(
                "Фильтр по типу:",
                ["Все", "regular", "unique", "other"],
                key="properties_filter_type"
            )

        with col2:
            filter_empty = st.checkbox(
                "Показать только фрагменты со свойствами",
                value=True,
                key="filter_with_properties"
            )

        # Применяем фильтры
        filtered_df = df_properties.copy()

        if filter_type != "Все":
            filtered_df = filtered_df[filtered_df['block_type'] == filter_type]

        if filter_empty:
            filtered_df = filtered_df[filtered_df['characteristic'].notna()]

        # Отображаем таблицу
        st.dataframe(filtered_df, use_container_width=True)

        # Экспорт свойств
        st.download_button(
            label="📥 Скачать свойства в CSV",
            data=filtered_df.to_csv(index=False, encoding='utf-8-sig'),
            file_name=f"fragment_properties_{self.category}.csv",
            mime="text/csv"
        )

    def display_fragments_list_interface(self):
        """Интерфейс списка фрагментов"""
        st.header("📋 Фрагменты")

        fragments_list = sorted(self.fragment_manager.fragment_names)

        if not fragments_list:
            st.info("Нет фрагментов")
            return

        # Отображаем список
        st.write(f"Всего фрагментов: **{len(fragments_list)}**")

        # Таблица с деталями
        table_data = []
        for frag_name in fragments_list:
            blocks = self.fragment_manager.get_fragment_blocks(frag_name)
            block_types = list(set(b.block_type for b in blocks))

            # Собираем тексты фрагментов
            sample_texts = []
            for block in blocks[:2]:  # Первые 2 блока
                text_preview = block.processed_text[:100] + "..." if len(
                    block.processed_text) > 100 else block.processed_text
                sample_texts.append(text_preview)

            table_data.append({
                'Фрагмент': frag_name,
                'Кол-во блоков': len(blocks),
                'Типы блоков': ', '.join(block_types),
                'Примеры текстов': ' | '.join(sample_texts),
                'Есть ошибки': '⚠️' if any(b.errors for b in blocks) else '✅',
                'Есть предупреждения': '⚠️' if any(b.warnings for b in blocks) else '✅'
            })

        df_fragments = pd.DataFrame(table_data)
        st.dataframe(df_fragments, use_container_width=True, height=400)

    def display_templates_interface(self):
        """Интерфейс для работы с шаблонами"""
        st.header("🧩 Шаблоны")

        # Ввод кода категории
        category_code = st.text_input(
            "Код категории для шаблонов:",
            value=st.session_state.phase6_enhanced_data.get('category_code', self.category),
            key="category_code_input"
        )

        # Сохраняем код категории
        if category_code:
            st.session_state.phase6_enhanced_data['category_code'] = category_code

        # Генерируем шаблон
        template_data = self.fragment_manager.generate_template_strings(category_code)

        # Отображаем переменные фрагментов
        st.subheader("Переменные фрагментов")

        for frag_name, var in template_data['fragment_variables'].items():
            col1, col2 = st.columns([1, 4])
            with col1:
                st.code(var, language=None)
            with col2:
                blocks = self.fragment_manager.get_fragment_blocks(frag_name)
                st.caption(f"({len(blocks)} блоков)")

        # Редактирование порядка
        st.subheader("🔀 Порядок фрагментов в шаблоне")

        # Используем текущий порядок из фрагмент-менеджера
        current_order = self.fragment_manager.template_order.copy()

        # Если order пустой, используем отсортированный список фрагментов
        if not current_order:
            current_order = sorted(self.fragment_manager.fragment_names)  # ← ИСПРАВЛЕНО!
            self.fragment_manager.template_order = current_order.copy()

        # Фильтруем порядок, оставляя только существующие фрагменты
        existing_fragments = set(self.fragment_manager.fragment_names)
        current_order = [name for name in current_order if name in existing_fragments]

        # Добавляем отсутствующие фрагменты в конец
        missing_fragments = existing_fragments - set(current_order)
        if missing_fragments:
            current_order.extend(sorted(missing_fragments))

        # Сохраняем обновленный порядок
        self.fragment_manager.template_order = current_order.copy()

        # Интерфейс для изменения порядка
        st.write("Перетащите элементы для изменения порядка:")

        for i, frag_name in enumerate(current_order):
            col1, col2, col3 = st.columns([1, 4, 1])

            with col1:
                st.write(f"**{i + 1}.**")

            with col2:
                st.text(frag_name)

            with col3:
                move_up = st.button("↑", key=f"move_up_{i}_{frag_name}", disabled=(i == 0))
                move_down = st.button("↓", key=f"move_down_{i}_{frag_name}",
                                      disabled=(i == len(current_order) - 1))

                if move_up:
                    current_order[i], current_order[i - 1] = current_order[i - 1], current_order[i]
                    self.fragment_manager.template_order = current_order.copy()
                    st.rerun()

                if move_down:
                    current_order[i], current_order[i + 1] = current_order[i + 1], current_order[i]
                    self.fragment_manager.template_order = current_order.copy()
                    st.rerun()

        # Кнопки управления
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💾 Сохранить порядок", key="save_template_order"):
                self.fragment_manager.template_order = current_order.copy()
                st.session_state.phase6_enhanced_data['template_order'] = current_order.copy()
                st.success("Порядок сохранен!")

        with col2:
            if st.button("🔄 Сбросить к алфавитному", key="reset_to_alphabetical"):
                alphabetical_order = sorted(self.fragment_manager.fragment_names)
                current_order = alphabetical_order.copy()
                self.fragment_manager.template_order = current_order.copy()
                st.session_state.phase6_enhanced_data['template_order'] = current_order.copy()
                st.success("Порядок сброшен!")
                st.rerun()

        with col3:
            if st.button("🗑️ Очистить порядок", key="clear_template_order"):
                current_order = []
                self.fragment_manager.template_order = []
                st.session_state.phase6_enhanced_data['template_order'] = []
                st.success("Порядок очищен!")
                st.rerun()

        # Отображение итогового шаблона
        st.subheader("📋 Итоговый шаблон")

        # Формируем строку шаблона с проверкой существования фрагментов
        template_parts = []
        for frag_name in current_order:
            if frag_name in template_data['fragment_variables']:
                template_parts.append(template_data['fragment_variables'][frag_name])
            else:
                st.warning(f"Фрагмент '{frag_name}' не найден в списке фрагментов")

        template_string = " ".join(template_parts)

        st.code(template_string, language=None)

        # Копирование шаблона
        if template_string:
            st.download_button(
                label="📋 Скопировать шаблон",
                data=template_string,
                file_name=f"template_{category_code}.txt",
                mime="text/plain",
                key="download_template"
            )

        # Предпросмотр
        with st.expander("👁️ Предпросмотр шаблона"):
            preview_text = ""
            for frag_name in current_order:
                blocks = self.fragment_manager.get_fragment_blocks(frag_name)
                if blocks:
                    # Берем первый блок для предпросмотра
                    preview_text += blocks[0].processed_text + "\n\n"

            st.text_area("Предпросмотр:", preview_text, height=300, key="template_preview")

    def export_to_excel(self) -> Path:
        """Экспорт всех данных в Excel файл"""
        export_dir = Path("exports/phase6")
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.category}_fragments_{timestamp}.xlsx"
        export_path = export_dir / filename

        # Создаем Excel writer
        with pd.ExcelWriter(export_path, engine='openpyxl') as writer:
            # 1. Лист "Шаблоны"
            template_data = self.fragment_manager.generate_template_strings(
                st.session_state.phase6_enhanced_data.get('category_code', self.category)
            )

            templates_df = pd.DataFrame({
                'Код категории': [template_data['category_code']],
                'Шаблон': [template_data['default_template']],
                'Кол-во фрагментов': [len(template_data['fragment_variables'])]
            })
            templates_df.to_excel(writer, sheet_name='Шаблоны', index=False)

            # 2. Лист "Фрагменты"
            fragments_df = pd.DataFrame({
                'Название фрагмента': sorted(self.fragment_manager.fragment_names)
            })
            fragments_df.to_excel(writer, sheet_name='Фрагменты', index=False)

            # 3. Лист "Свойства фрагментов"
            properties_table = self.fragment_manager.get_all_properties_table()
            properties_df = pd.DataFrame(properties_table)
            if not properties_df.empty:
                properties_df.columns = ['Название фрагмента', 'Характеристика', 'Значение', 'Тип блока']
                properties_df.to_excel(writer, sheet_name='Свойства фрагментов', index=False)
            else:
                pd.DataFrame({'Сообщение': ['Нет данных о свойствах']}).to_excel(
                    writer, sheet_name='Свойства фрагментов', index=False
                )

            # 4. Лист "Элементы фрагментов"
            fragment_elements = []
            for fragment in self.fragment_manager.fragments:
                fragment_elements.append({
                    'Название блока': fragment.fragment_name,
                    'Тип блока': fragment.block_type,
                    'Характеристика': fragment.characteristic_name,
                    'Значение': fragment.characteristic_value,
                    'Оригинальный текст': fragment.original_text,
                    'Обработанный текст': fragment.processed_text,
                    'Ошибки': '; '.join(fragment.errors) if fragment.errors else '',
                    'Предупреждения': '; '.join(fragment.warnings) if fragment.warnings else ''
                })

            elements_df = pd.DataFrame(fragment_elements)
            elements_df.to_excel(writer, sheet_name='Элементы фрагментов', index=False)

            # 5. Лист "Склейки" (если есть)
            merges = st.session_state.phase6_enhanced_data.get('merges', {})
            if merges:
                merges_data = []
                for new_name, old_names in merges.items():
                    merges_data.append({
                        'Объединенный фрагмент': new_name,
                        'Исходные фрагменты': ', '.join(old_names)
                    })
                merges_df = pd.DataFrame(merges_data)
                merges_df.to_excel(writer, sheet_name='Склейки', index=False)

        return export_path

    def main_interface(self):
        """Основной интерфейс улучшенной фазы 6"""
        st.title("🚀 Фаза 6: Подготовка к загрузке на сайт")
        st.markdown("---")

        # ВОССТАНАВЛИВАЕМ fragment_manager из session_state ПЕРЕД проверками
        if (st.session_state.phase6_enhanced_data.get('fragments_processed', False) and
                'fragment_manager' in st.session_state.phase6_enhanced_data):
            self.fragment_manager = st.session_state.phase6_enhanced_data['fragment_manager']

        # БОКОВАЯ ПАНЕЛЬ
        with st.sidebar:
            st.header("🔄 Управление данными")

            # Кнопка обновления из фазы 5
            if st.button("🔄 Обновить из фазы 5", use_container_width=True,
                         help="Загрузить последние данные из фазы 5"):
                if self.load_and_process_data(force_reload=True):
                    st.success("✅ Данные обновлены!")
                    st.rerun()
                else:
                    st.error("❌ Не удалось обновить данные")

            # Кнопка сброса обработки
            if st.button("🗑️ Сбросить обработку", use_container_width=True,
                         help="Очистить все обработанные данные фазы 6"):
                st.session_state.phase6_enhanced_data = {
                    'fragments_processed': False,
                    'fragment_blocks': [],
                    'template_order': [],
                    'category_code': self.category,
                    'merges': {},
                    'manual_corrections': {}
                }
                st.success("✅ Данные сброшены!")
                st.rerun()

            st.divider()

            # Статус данных
            st.header("📊 Статус")

            if (st.session_state.phase6_enhanced_data.get('fragments_processed', False)):
                if 'fragment_manager' in st.session_state.phase6_enhanced_data:
                    self.fragment_manager = st.session_state.phase6_enhanced_data['fragment_manager']
                else:
                    # Пробуем восстановить из fragment_blocks
                    if self.restore_fragments_from_session():
                        st.success("Фрагменты восстановлены из session_state")
                        st.rerun()

            # Информация о данных фазы 5
            if 'app_data' in st.session_state and 'phase5' in st.session_state.app_data:
                phase5_data = st.session_state.app_data['phase5']
                if phase5_data and 'statistics' in phase5_data:
                    stats = phase5_data['statistics']
                    success_count = stats.get('success', 0)
                    st.write(f"**Из фазы 5:** {success_count} текстов")

            st.divider()

            # Навигация
            st.header("🚦 Навигация")
            if st.button("← Вернуться к фазе 5", use_container_width=True):
                st.session_state.current_phase = 5
                st.rerun()

        # Проверяем загрузку данных
        if not st.session_state.phase6_enhanced_data.get('fragments_processed', False):
            # Показываем информацию о загруженных данных
            if 'app_data' in st.session_state and 'phase5' in st.session_state.app_data:
                phase5_data = st.session_state.app_data['phase5']
                stats = phase5_data.get('statistics', {})
                st.info("""
                ## 📥 Подготовка данных для сайта

                Эта фаза подготавливает сгенерированные тексты к загрузке на сайт.

                **Что будет сделано:**
                1. Автоматическое присвоение названий фрагментам
                2. Формирование свойств фрагментов
                3. Создание списка фрагментов
                4. Подготовка шаблонов для сайта
                """)

                # Показываем количество текстов для обработки
                results = phase5_data.get('results', [])
                count = len(results) if isinstance(results, (list, dict)) else 0
                st.write(f"**Найдено {count} текстов для обработки**")

            if st.button("🔄 Начать обработку данных", type="primary",
                         use_container_width=True, key="start_enhanced_processing"):
                with st.spinner("Обработка данных..."):
                    if self.load_and_process_data():
                        st.success("✅ Данные успешно обработаны!")
                        st.rerun()
                    else:
                        st.error("❌ Не удалось обработать данные")

            return

        # Проверяем наличие фрагментов
        if not hasattr(self, 'fragment_manager') or not self.fragment_manager:
            st.error("❌ Менеджер фрагментов не загружен")
            if st.button("🔄 Восстановить менеджер фрагментов", key="restore_fragment_manager"):
                # Пытаемся восстановить из session_state
                if 'fragment_manager' in st.session_state.phase6_enhanced_data:
                    self.fragment_manager = st.session_state.phase6_enhanced_data['fragment_manager']
                    st.rerun()
            return

        fragment_names = list(self.fragment_manager.fragment_names)

        st.write(f"**Обработано фрагментов:** {len(fragment_names)}")

        # Если фрагментов нет, но данные обработаны
        if not fragment_names:
            st.warning("⚠️ Фрагменты не найдены, хотя данные помечены как обработанные")

            # Кнопка для отладки
            if st.button("🔍 Показать отладочную информацию", key="show_debug_info"):
                self.debug_fragment_manager()
                st.stop()

            # Показываем debug информацию
            with st.expander("🔍 Информация для отладки"):
                st.write("Состояние phase6_enhanced_data:")
                st.json(st.session_state.phase6_enhanced_data, expanded=False)

                if 'fragment_blocks' in st.session_state.phase6_enhanced_data:
                    fragment_blocks = st.session_state.phase6_enhanced_data['fragment_blocks']
                    st.write(f"Количество блоков в fragment_blocks: {len(fragment_blocks)}")
                    if fragment_blocks:
                        st.write("Пример первого блока:")
                        st.write(fragment_blocks[0])

            if st.button("🔄 Перезагрузить фрагменты", key="reload_fragments"):
                # Пробуем перезагрузить из исходных данных
                if self.load_and_process_data(force_reload=True):
                    st.success("Фрагменты перезагружены!")
                    st.rerun()
            return

        # Навигация по вкладкам
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏷️ Названия",
            "📊 Свойства",
            "📋 Фрагменты",
            "🧩 Шаблоны",
            "💾 Экспорт"
        ])

        with tab1:
            self.display_fragment_naming_interface()

        with tab2:
            self.display_fragment_properties_interface()

        with tab3:
            self.display_fragments_list_interface()

        with tab4:
            self.display_templates_interface()

        with tab5:
            st.header("📤 Экспорт данных")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("""
                **Подготовленные данные:**
                - Шаблоны для сайта
                - Список фрагментов
                - Свойства фрагментов
                - Тексты элементов
                """)

            with col2:
                if st.button("📊 Экспорт в Excel", type="primary",
                             use_container_width=True, key="export_excel"):
                    with st.spinner("Создание Excel файла..."):
                        try:
                            export_path = self.export_to_excel()

                            # Читаем файл для скачивания
                            with open(export_path, 'rb') as f:
                                excel_data = f.read()

                            st.download_button(
                                label="📥 Скачать Excel файл",
                                data=excel_data,
                                file_name=export_path.name,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_excel"
                            )

                            st.success(f"✅ Файл создан: {export_path.name}")
                        except Exception as e:
                            st.error(f"Ошибка при создании Excel файла: {str(e)}")

    def restore_fragments_from_session(self):
        """Восстанавливает фрагменты из данных session_state"""
        try:
            if 'fragment_blocks' in st.session_state.phase6_enhanced_data:
                fragment_blocks = st.session_state.phase6_enhanced_data['fragment_blocks']

                # Создаем новый менеджер
                self.fragment_manager = FragmentManager(self.category)

                # Добавляем все блоки
                for block_data in fragment_blocks:
                    try:
                        self.fragment_manager.add_block(block_data)
                    except Exception as e:
                        st.warning(f"Ошибка при восстановлении блока: {str(e)}")

                # Восстанавливаем порядок шаблона
                if 'template_order' in st.session_state.phase6_enhanced_data:
                    self.fragment_manager.template_order = st.session_state.phase6_enhanced_data['template_order']

                # Сохраняем обратно в session_state
                st.session_state.phase6_enhanced_data['fragment_manager'] = self.fragment_manager

                return True
        except Exception as e:
            st.error(f"Ошибка при восстановлении фрагментов: {str(e)}")

        return False


def main():
    """Основная функция фазы 6"""

    # Получаем данные напрямую из session_state
    if 'app_data' not in st.session_state:
        st.error("❌ Нет данных приложения")
        st.info("Вернитесь к фазе 1 для создания проекта")

        if st.button("← Вернуться к фазе 1", use_container_width=True):
            st.session_state.current_phase = 1
            st.rerun()
        return

    app_data = st.session_state.app_data

    # Проверяем наличие данных фазы 5
    if 'phase5' not in app_data or not app_data['phase5']:
        st.error("❌ Нет данных из фазы 5")
        st.info("""
        Для работы фазы 6 необходимо:
        1. Завершить фазу 5
        2. Сохранить данные для фазы 6 (кнопка "Сохранить данные для фазы 6" в фазе 5)
        """)

        if st.button("← Вернуться к фазе 5", use_container_width=True):
            st.session_state.current_phase = 5
            st.rerun()
        return

    phase5_data = app_data['phase5']

    # Проверяем, завершена ли фаза 5
    if not phase5_data.get('phase_completed', False):
        st.warning("⚠️ Фаза 5 не завершена полностью")
        st.info("Вернитесь в фазу 5 и завершите генерацию текстов")

        if st.button("← Вернуться к фазе 5", use_container_width=True):
            st.session_state.current_phase = 5
            st.rerun()
        return

    # Показываем информацию о данных
    st.write(f"**Текущая фаза:** 6")

    if 'statistics' in phase5_data:
        stats = phase5_data['statistics']
        success_count = stats.get('success', 0)
        st.success(f"✅ Данные из фазы 5 готовы")
        st.write(f"**Успешно сгенерировано:** {success_count} текстов")

    # Подготавливаем input_data для процессора
    input_data = {
        'phase5_data': phase5_data,
        'phase1_data': app_data.get('phase1', {}),
        'phase2_data': app_data.get('phase2', {}),
        'category': app_data.get('category', ''),
        'project_name': app_data.get('project_name', '')
    }

    # Создаем псевдо-app_state для совместимости
    class AppState:
        def get_phase_data(self, phase_num):
            if phase_num == 5:
                return phase5_data
            elif phase_num == 1:
                return app_data.get('phase1', {})
            elif phase_num == 2:
                return app_data.get('phase2', {})
            return {}

    app_state = AppState()

    # Инициализируем процессор
    processor = Phase6EnhancedProcessor(app_state, input_data)

    # Автоматически загружаем данные при первом входе
    if not st.session_state.phase6_enhanced_data.get('fragments_processed', False):
        st.info("Данные из фазы 5 не обработаны. Нажмите кнопку ниже, чтобы начать.")

        if st.button("🚀 Начать обработку данных", type="primary", use_container_width=True):
            with st.spinner("Обработка данных из фазы 5..."):
                if processor.load_and_process_data():
                    st.success("✅ Данные успешно обработаны!")
                    st.rerun()
                else:
                    st.error("❌ Не удалось обработать данные")
        return

    # Если данные уже обработаны, показываем основной интерфейс
    processor.main_interface()


if __name__ == "__main__":
    main()