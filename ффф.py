import streamlit as st
import re
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import uuid
import time
import difflib
from enum import Enum
import hashlib


# ====================== НОВЫЕ СТРУКТУРЫ ДАННЫХ ======================

class TransformationType(Enum):
    """Типы трансформаций текста"""
    VARIABLE_REPLACE = "variable_replace"
    UNIT_REMOVED = "unit_removed"
    AUTO_INSERT = "auto_insert"
    SPECIAL_SYMBOL = "special_symbol"
    WARNING = "warning"
    ERROR = "error"
    MANUAL_CORRECTION = "manual_correction"
    FRAGMENT_RENAME = "fragment_rename"
    FRAGMENT_MERGE = "fragment_merge"
    TEXT_CLEANING = "text_cleaning"


class SeverityLevel(Enum):
    """Уровни серьезности трансформаций"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class TextTransformation:
    """Структура для хранения информации о каждом изменении текста"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    block_id: str = ""
    fragment_name: str = ""
    transformation_type: TransformationType = TransformationType.TEXT_CLEANING  # ЗДЕСЬ ДОЛЖЕН БЫТЬ TransformationType
    original: str = ""
    result: str = ""
    start: int = -1
    end: int = -1
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    severity: SeverityLevel = SeverityLevel.INFO  # ЗДЕСЬ ДОЛЖЕН БЫТЬ SeverityLevel
    user: str = "system"
    context_hash: str = ""

    def __post_init__(self):
        """Вычисляет хэш контекста для группировки изменений"""
        if not self.context_hash and self.block_id and self.fragment_name:
            context_str = f"{self.block_id}_{self.fragment_name}_{self.transformation_type.value}"
            self.context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict:
        """Конвертирует в словарь для сериализации"""
        data = asdict(self)
        data['transformation_type'] = self.transformation_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'TextTransformation':
        """Создает объект из словаря"""
        data = data.copy()
        data['transformation_type'] = TransformationType(data['transformation_type'])
        data['severity'] = SeverityLevel(data['severity'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class TransformationRegistry:
    """Централизованный реестр всех трансформаций"""

    def __init__(self):
        self.transformations: List[TextTransformation] = []
        self._block_index: Dict[str, List[TextTransformation]] = defaultdict(list)
        self._fragment_index: Dict[str, List[TextTransformation]] = defaultdict(list)
        self._type_index: Dict[TransformationType, List[TextTransformation]] = defaultdict(list)
        self._severity_index: Dict[SeverityLevel, List[TextTransformation]] = defaultdict(list)  # ДОБАВИТЬ ЭТУ СТРОКУ

    def add(self, transformation: TextTransformation):
        """Добавляет трансформацию в реестр и обновляет индексы"""
        self.transformations.append(transformation)
        self._block_index[transformation.block_id].append(transformation)
        self._fragment_index[transformation.fragment_name].append(transformation)
        self._type_index[transformation.transformation_type].append(transformation)
        self._severity_index[transformation.severity].append(transformation)

    def add_batch(self, transformations: List[TextTransformation]):
        """Добавляет несколько трансформаций за раз"""
        for transformation in transformations:
            self.add(transformation)

    def get_by_block_id(self, block_id: str) -> List[TextTransformation]:
        """Возвращает все трансформации для конкретного блока"""
        return self._block_index.get(block_id, [])

    def get_by_fragment(self, fragment_name: str) -> List[TextTransformation]:
        """Возвращает все трансформации для конкретного фрагмента"""
        return self._fragment_index.get(fragment_name, [])

    def get_by_type(self, transformation_type: TransformationType) -> List[TextTransformation]:
        """Возвращает все трансформации определенного типа"""
        return self._type_index.get(transformation_type, [])

    def get_by_severity(self, severity: SeverityLevel) -> List[TextTransformation]:
        """Возвращает все трансформации определенного уровня серьезности"""
        return self._severity_index.get(severity, [])

    def get_errors(self) -> List[TextTransformation]:
        """Возвращает все ошибки"""
        return self._severity_index.get(SeverityLevel.ERROR, [])

    def get_warnings(self) -> List[TextTransformation]:
        """Возвращает все предупреждения"""
        return self._severity_index.get(SeverityLevel.WARNING, [])

    def get_info_transformations(self) -> List[TextTransformation]:
        """Возвращает все информационные трансформации"""
        return self._severity_index.get(SeverityLevel.INFO, [])

    def get_success_transformations(self) -> List[TextTransformation]:
        """Возвращает все успешные трансформации"""
        return self._severity_index.get(SeverityLevel.SUCCESS, [])

    def filter(self,
               block_id: Optional[str] = None,
               fragment_name: Optional[str] = None,
               transformation_type: Optional[TransformationType] = None,
               severity: Optional[SeverityLevel] = None,
               start_date: Optional[datetime] = None,
               end_date: Optional[datetime] = None) -> List[TextTransformation]:
        """Фильтрует трансформации по различным критериям"""
        filtered = self.transformations

        if block_id:
            filtered = [t for t in filtered if t.block_id == block_id]
        if fragment_name:
            filtered = [t for t in filtered if t.fragment_name == fragment_name]
        if transformation_type:
            filtered = [t for t in filtered if t.transformation_type == transformation_type]
        if severity:
            filtered = [t for t in filtered if t.severity == severity]
        if start_date:
            filtered = [t for t in filtered if t.timestamp >= start_date]
        if end_date:
            filtered = [t for t in filtered if t.timestamp <= end_date]

        return filtered

    def to_dataframe(self) -> pd.DataFrame:
        """Конвертирует реестр в DataFrame для отображения"""
        if not self.transformations:
            return pd.DataFrame()

        data = []
        for t in self.transformations:
            row = {
                'id': t.id,
                'block_id': t.block_id,
                'fragment_name': t.fragment_name,
                'transformation_type': t.transformation_type.value,
                'original': t.original[:100] + '...' if len(t.original) > 100 else t.original,
                'result': t.result[:100] + '...' if len(t.result) > 100 else t.result,
                'start': t.start,
                'end': t.end,
                'position': f"{t.start}-{t.end}",
                'severity': t.severity.value,
                'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'user': t.user,
                'meta_summary': self._get_meta_summary(t.meta)
            }
            data.append(row)

        return pd.DataFrame(data)

    def to_detailed_dataframe(self) -> pd.DataFrame:
        """Конвертирует реестр в DataFrame с полными данными"""
        if not self.transformations:
            return pd.DataFrame()

        data = []
        for t in self.transformations:
            row = {
                'id': t.id,
                'block_id': t.block_id,
                'fragment_name': t.fragment_name,
                'transformation_type': t.transformation_type.value,
                'original': t.original,
                'result': t.result,
                'start': t.start,
                'end': t.end,
                'severity': t.severity.value,
                'timestamp': t.timestamp.isoformat(),
                'user': t.user,
                'meta': json.dumps(t.meta, ensure_ascii=False),
                'context_hash': t.context_hash
            }
            data.append(row)

        return pd.DataFrame(data)

    def _get_meta_summary(self, meta: Dict) -> str:
        """Создает краткое описание метаданных"""
        if not meta:
            return ""

        parts = []
        for key, value in meta.items():
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}: {value}")
            elif isinstance(value, list):
                parts.append(f"{key}: {len(value)} items")
            elif isinstance(value, dict):
                parts.append(f"{key}: dict")

        return "; ".join(parts[:3]) + ("..." if len(parts) > 3 else "")

    def clear(self):
        """Очищает реестр"""
        self.transformations.clear()
        self._block_index.clear()
        self._fragment_index.clear()
        self._type_index.clear()
        self._severity_index.clear()

    def save_to_file(self, filepath: str):
        """Сохраняет реестр в файл"""
        data = [t.to_dict() for t in self.transformations]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def load_from_file(self, filepath: str):
        """Загружает реестр из файла"""
        if Path(filepath).exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.transformations = [TextTransformation.from_dict(item) for item in data]
                # Перестраиваем индексы
                for transformation in self.transformations:
                    self._block_index[transformation.block_id].append(transformation)
                    self._fragment_index[transformation.fragment_name].append(transformation)
                    self._type_index[transformation.transformation_type].append(transformation)


# ====================== УТИЛИТЫ ======================

def generate_key_with_timestamp(prefix: str = "key") -> str:
    """Генерирует уникальный ключ с временной меткой"""
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


def get_text_diff(original: str, modified: str) -> str:
    """Возвращает diff между двумя текстами"""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile='Исходный',
        tofile='Измененный',
        lineterm=''
    )
    return ''.join(diff)


def highlight_text_changes(original: str, modified: str, start: int, end: int) -> str:
    """Подсвечивает изменения в тексте"""
    if start == -1 or end == -1:
        return modified

    before = modified[:start]
    after = modified[end:]
    changed = modified[start:end]

    return f"{before}<mark>{changed}</mark>{after}"


def initialize_registry():
    """Инициализирует реестр трансформаций в session_state"""
    if 'transformation_registry' not in st.session_state:
        st.session_state.transformation_registry = TransformationRegistry()
    # Убедимся, что реестр инициализирован с правильными индексами
    elif not hasattr(st.session_state.transformation_registry, '_severity_index'):
        # Если реестр существует, но не имеет нужного атрибута, пересоздаем
        old_registry = st.session_state.transformation_registry
        new_registry = TransformationRegistry()
        # Переносим существующие трансформации
        new_registry.transformations = old_registry.transformations
        # Перестраиваем индексы
        for transformation in new_registry.transformations:
            new_registry._block_index[transformation.block_id].append(transformation)
            new_registry._fragment_index[transformation.fragment_name].append(transformation)
            new_registry._type_index[transformation.transformation_type].append(transformation)
            new_registry._severity_index[transformation.severity].append(transformation)
        st.session_state.transformation_registry = new_registry

    # Инициализация состояния интерфейса
    if 'transformation_ui_state' not in st.session_state:
        st.session_state.transformation_ui_state = {
            'selected_transformation': None,
            'filter_type': 'all',
            'filter_severity': 'all',
            'filter_fragment': 'all',
            'search_text': '',
            'show_only_errors': False,
            'show_only_warnings': False,
            'group_by_block': False,
            'expanded_groups': set()
        }


# ====================== МОДИФИЦИРОВАННЫЕ КЛАССЫ ======================

class EnhancedErrorPreprocessor:
    """Улучшенный препроцессор с трекингом изменений"""

    def __init__(self, registry: TransformationRegistry):
        self.registry = registry
        self.units_to_remove = [
            "мм", "метр", "м", "см", "дм", "км", "миллиметр", "сантиметр", "дециметр", "километр",
            "кг", "г", "мг", "тонна", "т", "грамм", "миллиграмм", "килограмм",
            "л", "мл", "литр", "миллилитр",
            "шт", "штук", "штука", "штуки",
            "кг/м", "г/см³", "г/см3", "кг/м³", "кг/м3",
            "°C", "°F", "град", "градус", "градусов"
        ]
        self._expand_units()

        self.special_symbols_pattern = r'[<>{}|\\^`~!@#$%^&*()_\+=\[\]\'":;?/]'
        self.instruction_keywords = [
            "инструкция:", "промпт:", "введите:", "создайте:", "напишите:",
            "instruction:", "prompt:", "write:", "create:", "generate:",
            "опишите:", "сформулируйте:", "составьте:", "подготовьте:"
        ]

    def _expand_units(self):
        """Расширяет список единиц измерения с учетом падежей и форм"""
        expanded_units = []
        for unit in self.units_to_remove:
            expanded_units.append(unit)
            if unit.endswith('м'):
                expanded_units.append(f"{unit}а")
                expanded_units.append(f"{unit}ов")
                expanded_units.append(f"{unit}у")
            elif unit.endswith('г'):
                expanded_units.append(f"{unit}а")
                expanded_units.append(f"{unit}ов")
            elif unit.endswith('л'):
                expanded_units.append(f"{unit}а")
                expanded_units.append(f"{unit}ов")
        self.units_to_remove = expanded_units

    def preprocess_block(self, block_data: Dict, block_id: str, fragment_name: str) -> Dict:
        """Основной метод предобработки блока с трекингом изменений"""
        text = block_data.get("edited_text", "")
        block_type = block_data.get("type", "")

        result = {
            "original_text": text,
            "processed_text": text,
            "special_symbols": [],
            "has_instructions": False,
            "removed_units": [],
            "auto_corrected": False,
            "added_value": None,
            "cleaned_text": text,
            "transformations": []
        }

        # 1. Проверка на наличие инструкций промпта
        result["has_instructions"] = self._check_instructions(text)
        if result["has_instructions"]:
            transformation = TextTransformation(
                block_id=block_id,
                fragment_name=fragment_name,
                transformation_type=TransformationType.WARNING,
                original=text,
                result=text,
                start=0,
                end=len(text),
                meta={"warning_type": "instruction_detected", "block_type": block_type},
                severity=SeverityLevel.WARNING
            )
            self.registry.add(transformation)
            result["transformations"].append(transformation)

        # 2. Поиск специальных символов
        special_symbols = self._find_special_symbols(text)
        result["special_symbols"] = special_symbols

        for symbol, start, end in special_symbols:
            transformation = TextTransformation(
                block_id=block_id,
                fragment_name=fragment_name,
                transformation_type=TransformationType.SPECIAL_SYMBOL,
                original=symbol,
                result="",
                start=start,
                end=end,
                meta={"symbol": symbol, "position": (start, end)},
                severity=SeverityLevel.WARNING
            )
            self.registry.add(transformation)
            result["transformations"].append(transformation)

        # 3. Удаление единиц измерения
        cleaned_text, removed_units = self._remove_units(text, block_id, fragment_name)
        result["removed_units"] = removed_units
        result["cleaned_text"] = cleaned_text

        # 4. Для regular блоков - проверка формата
        if block_type == "regular":
            result["has_variables"] = self._check_variables_format(text)

        return result

    def _check_instructions(self, text: str) -> bool:
        """Проверяет, содержит ли текст инструкции промпта"""
        text_lower = text.lower()
        for keyword in self.instruction_keywords:
            if keyword in text_lower:
                return True
        return False

    def _find_special_symbols(self, text: str) -> List[Tuple[str, int, int]]:
        """Находит позиции специальных символов в тексте"""
        positions = []
        for match in re.finditer(self.special_symbols_pattern, text):
            symbol = match.group()
            if symbol not in ['[', ']', ',', '.', '-', '_', ' ', '\t', '\n']:
                positions.append((symbol, match.start(), match.end()))
        return positions

    def _remove_units(self, text: str, block_id: str, fragment_name: str) -> Tuple[str, List[str]]:
        """Удаляет единицы измерения из текста с трекингом"""
        removed = []
        cleaned_text = text
        offset = 0

        for unit in self.units_to_remove:
            pattern = r'\b' + re.escape(unit) + r'\b'
            matches = list(re.finditer(pattern, cleaned_text, re.IGNORECASE))

            # Обрабатываем совпадения с конца, чтобы позиции не сдвигались
            for match in reversed(matches):
                start, end = match.span()
                actual_start = start + offset
                actual_end = end + offset

                # Логируем удаление единицы измерения
                transformation = TextTransformation(
                    block_id=block_id,
                    fragment_name=fragment_name,
                    transformation_type=TransformationType.UNIT_REMOVED,
                    original=match.group(),
                    result="",
                    start=actual_start,
                    end=actual_end,
                    meta={"unit": unit, "position_original": (start, end)},
                    severity=SeverityLevel.WARNING
                )
                self.registry.add(transformation)

                # Удаляем единицу из текста
                cleaned_text = cleaned_text[:start] + cleaned_text[end:]
                offset -= (end - start)
                removed.append(unit)

        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        return cleaned_text, removed

    def _check_variables_format(self, text: str) -> bool:
        """Проверяет наличие переменных в формате [переменная]"""
        return bool(re.search(r'\[[^\]]+\]', text))


class EnhancedTextProcessor:
    """Улучшенный обработчик текстов с полным трекингом изменений"""

    def __init__(self, variable_manager, registry: TransformationRegistry):
        self.vm = variable_manager
        self.registry = registry
        self.error_preprocessor = EnhancedErrorPreprocessor(registry)
        self.pattern = re.compile(r'\[([^\]]+)\]')

    def extract_variables(self, text: str) -> List[Tuple[str, int, int]]:
        """Извлекает все переменные из текста в формате [переменная]"""
        matches = []
        for match in self.pattern.finditer(text):
            var_name = match.group(1).strip()
            start, end = match.span()
            matches.append((var_name, start, end))
        return matches

    def process_block(self, block: Dict, characteristics: List[Dict],
                      block_id: str, fragment_name: str) -> Dict:
        """Обрабатывает один текстовый блок с полным трекингом"""
        original_text = block.get("edited_text", "")
        block_type = block.get("type", "")
        char_name = block.get("characteristic_name", "")
        char_value = block.get("characteristic_value", "")

        variables = self.extract_variables(original_text)
        processed_text = original_text
        replacements = []
        errors = []
        warnings = []
        transformations = []
        offset = 0

        for var_name, start, end in variables:
            original_var = original_text[start:end]
            char_found = False
            source_type = "unknown"

            if block_type == "regular":
                if not char_name:
                    errors.append(f"Regular блок без characteristic_name: {original_var}")
                    replacement = f"{{{self.vm.prefixes['prop']} {char_name or 'unknown'}}}"
                    source_type = "prop"
                else:
                    # Ищем характеристику в предоставленных данных
                    for char in characteristics:
                        if char.get("name") == char_name:
                            # Для regular блоков используем prop префикс с именем характеристики
                            replacement = f"{{{self.vm.prefixes['prop']} {char_name}}}"
                            char_found = True
                            source_type = "prop"
                            break

                    if not char_found:
                        # Если не нашли в характеристиках, пробуем найти в переменных
                        if var_name in self.vm.system_vars:
                            replacement = self.vm.get_best_variant(var_name,
                                                                   original_text[max(0, start - 10):end + 10])
                            source_type = "system"
                            char_found = True
                        else:
                            errors.append(f"Не найдена характеристика '{char_name}' для: {original_var}")
                            replacement = f"{{{self.vm.prefixes['prop']} {char_name}}}"
                            source_type = "prop"
            else:
                # Для non-regular блоков используем system переменные
                if var_name in self.vm.system_vars:
                    replacement = self.vm.get_best_variant(var_name,
                                                           original_text[max(0, start - 10):end + 10])
                    source_type = "system"
                    char_found = True
                else:
                    errors.append(f"Неизвестная переменная: [{var_name}]")
                    replacement = f"{{{self.vm.prefixes['system']} {var_name}}}"
                    source_type = "system"

            # Логируем замену переменной
            transformation = TextTransformation(
                block_id=block_id,
                fragment_name=fragment_name,
                transformation_type=TransformationType.VARIABLE_REPLACE,
                original=original_var,
                result=replacement,
                start=start + offset,
                end=end + offset,
                meta={
                    "variable_name": var_name,
                    "source": source_type,
                    "block_type": block_type,
                    "characteristic": char_name,
                    "char_value": char_value,
                    "char_found": char_found
                },
                severity=SeverityLevel.ERROR if not char_found and block_type == "regular" else SeverityLevel.INFO
            )
            self.registry.add(transformation)
            transformations.append(transformation)

            # Применяем замену
            new_start = start + offset
            new_end = end + offset
            processed_text = processed_text[:new_start] + replacement + processed_text[new_end:]
            offset += len(replacement) - (end - start)

            replacements.append({
                "original": original_var,
                "replacement": replacement,
                "position": (start, end),
                "char_found": char_found,
                "source_type": source_type
            })

        # Автодобавление значения для regular блоков без переменных
        if block_type == "regular" and not variables and char_name and char_value:
            found_value = self._find_characteristic_value(char_name, char_value, characteristics)

            if found_value:
                # Автоматически добавляем значение
                new_text = self._insert_value_into_text(original_text, found_value)
                auto_correction_transformation = TextTransformation(
                    block_id=block_id,
                    fragment_name=fragment_name,
                    transformation_type=TransformationType.AUTO_INSERT,
                    original=original_text,
                    result=new_text,
                    start=len(original_text),
                    end=len(new_text),
                    meta={
                        "added_value": found_value,
                        "characteristic_name": char_name,
                        "characteristic_value": char_value,
                        "action": "auto_add_value"
                    },
                    severity=SeverityLevel.SUCCESS
                )
                self.registry.add(auto_correction_transformation)
                transformations.append(auto_correction_transformation)

                # Обновляем текст и перезапускаем обработку
                original_text = new_text
                processed_text = new_text
                variables = self.extract_variables(original_text)

                # Обрабатываем только что добавленную переменную
                if variables:
                    var_name, start, end = variables[-1]
                    replacement = f"{{{self.vm.prefixes['prop']} {char_name}}}"

                    transformation = TextTransformation(
                        block_id=block_id,
                        fragment_name=fragment_name,
                        transformation_type=TransformationType.VARIABLE_REPLACE,
                        original=f"[{found_value}]",
                        result=replacement,
                        start=start,
                        end=end,
                        meta={
                            "variable_name": found_value,
                            "source": "prop",
                            "block_type": block_type,
                            "characteristic": char_name,
                            "auto_added": True
                        },
                        severity=SeverityLevel.SUCCESS
                    )
                    self.registry.add(transformation)
                    transformations.append(transformation)

                    processed_text = processed_text[:start] + replacement + processed_text[end:]

                    replacements.append({
                        "original": f"[{found_value}]",
                        "replacement": replacement,
                        "position": (start, end),
                        "char_found": True,
                        "source_type": "prop",
                        "auto_added": True
                    })

                warnings.append(f"Автоматически добавлено значение: [{found_value}]")
            else:
                # Не смогли найти значение - кидаем ошибку пользователю
                error_msg = f"Не найдено значение для характеристики '{char_name}': {char_value}"
                errors.append(error_msg)

                transformation = TextTransformation(
                    block_id=block_id,
                    fragment_name=fragment_name,
                    transformation_type=TransformationType.ERROR,
                    original=original_text,
                    result=processed_text,
                    start=0,
                    end=len(original_text),
                    meta={
                        "error_type": "missing_characteristic_value",
                        "characteristic_name": char_name,
                        "characteristic_value": char_value,
                        "block_type": block_type
                    },
                    severity=SeverityLevel.ERROR
                )
                self.registry.add(transformation)
                transformations.append(transformation)

        elif block_type == "regular" and not variables and char_name and not char_value:
            # Regular блок без значения характеристики
            error_msg = f"Regular блок '{char_name}' не содержит значения характеристики"
            errors.append(error_msg)

            transformation = TextTransformation(
                block_id=block_id,
                fragment_name=fragment_name,
                transformation_type=TransformationType.ERROR,
                original=original_text,
                result=processed_text,
                start=0,
                end=len(original_text),
                meta={
                    "error_type": "missing_characteristic_value",
                    "characteristic_name": char_name,
                    "block_type": block_type
                },
                severity=SeverityLevel.ERROR
            )
            self.registry.add(transformation)
            transformations.append(transformation)

        if block_type == "regular" and not variables and not char_name:
            error_msg = "Regular блок должен содержать characteristic_name и хотя бы одну переменную"
            errors.append(error_msg)

            transformation = TextTransformation(
                block_id=block_id,
                fragment_name=fragment_name,
                transformation_type=TransformationType.ERROR,
                original=original_text,
                result=processed_text,
                start=0,
                end=len(original_text),
                meta={"error_type": "no_variables", "block_type": block_type},
                severity=SeverityLevel.ERROR
            )
            self.registry.add(transformation)
            transformations.append(transformation)

        if "[название товара]" in original_text.lower():
            warning_msg = "Для [название товара] рекомендуется также добавить переменные категории (РП/ВП/ИП)"
            warnings.append(warning_msg)

            transformation = TextTransformation(
                block_id=block_id,
                fragment_name=fragment_name,
                transformation_type=TransformationType.WARNING,
                original=original_text,
                result=processed_text,
                start=0,
                end=len(original_text),
                meta={"warning_type": "missing_category_vars"},
                severity=SeverityLevel.WARNING
            )
            self.registry.add(transformation)
            transformations.append(transformation)

        return {
            "original_text": original_text,
            "processed_text": processed_text,
            "replacements": replacements,
            "errors": errors,
            "warnings": warnings,
            "has_errors": len(errors) > 0,
            "has_warnings": len(warnings) > 0,
            "variables_count": len(variables),
            "transformations": transformations,
            "auto_corrected": any("auto_added" in r for r in replacements)
        }

    def _find_characteristic_value(self, char_name: str, char_value: str,
                                   characteristics: List[Dict]) -> Optional[str]:
        """Ищет конкретное значение характеристики в данных"""
        if not char_name or not char_value:
            return None

        char_name_lower = char_name.lower()
        char_value_lower = char_value.lower()

        for char in characteristics:
            current_char_name = char.get("name", "")
            if not current_char_name or current_char_name.lower() != char_name_lower:
                continue

            char_data = char.get("data", {})

            if isinstance(char_data, dict):
                for key, value in char_data.items():
                    if value and isinstance(value, str):
                        value_lower = value.lower()
                        if (value_lower == char_value_lower or
                                char_value_lower in value_lower or
                                value_lower in char_value_lower):
                            return value

            elif isinstance(char_data, list):
                for item in char_data:
                    if isinstance(item, dict):
                        item_value = item.get("value")
                    elif isinstance(item, str):
                        item_value = item
                    else:
                        continue

                    if item_value and isinstance(item_value, str):
                        item_value_lower = item_value.lower()
                        if (item_value_lower == char_value_lower or
                                char_value_lower in item_value_lower or
                                item_value_lower in char_value_lower):
                            return item_value

        return None

    def _clean_value_for_search(self, value: str) -> str:
        """Очищает значение для поиска"""
        if not value:
            return ""
        cleaned = value.lower()
        cleaned = re.sub(r'[^\w\sх×*]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _insert_value_into_text(self, text: str, value: str) -> str:
        """Вставляет значение в квадратных скобках в текст"""
        if not text.strip():
            return f"[{value}]"
        if text.strip()[-1] in '.!,;:?':
            return text.strip()[:-1] + f" [{value}]" + text.strip()[-1]
        return text.strip() + f" [{value}]"

    def find_specific_value_for_characteristic(self, char_name: str, char_value: str,
                                               characteristics: List[Dict]) -> Optional[str]:
        """Ищет конкретное значение характеристики в данных из фазы 5"""
        if not char_name or not char_value:
            return None

        char_name_lower = char_name.lower()
        char_value_lower = char_value.lower()

        for char in characteristics:
            current_char_name = char.get("name", "")
            if not current_char_name or current_char_name.lower() != char_name_lower:
                continue

            char_data = char.get("data", {})

            if isinstance(char_data, dict):
                for key, value in char_data.items():
                    if value and isinstance(value, str):
                        value_lower = value.lower()
                        if (value_lower == char_value_lower or
                                char_value_lower in value_lower or
                                value_lower in char_value_lower):
                            return value

            elif isinstance(char_data, list):
                for item in char_data:
                    if isinstance(item, dict):
                        item_value = item.get("value")
                    elif isinstance(item, str):
                        item_value = item
                    else:
                        continue

                    if item_value and isinstance(item_value, str):
                        item_value_lower = item_value.lower()
                        if (item_value_lower == char_value_lower or
                                char_value_lower in item_value_lower or
                                item_value_lower in char_value_lower):
                            return item_value

            # Поиск по очищенным значениям
            if isinstance(char_data, dict):
                for key, value in char_data.items():
                    if value and isinstance(value, str):
                        clean_value = self._clean_value_for_search(value)
                        clean_char_value = self._clean_value_for_search(char_value)

                        if clean_value and clean_char_value:
                            if (clean_value == clean_char_value or
                                    clean_char_value in clean_value or
                                    clean_value in clean_char_value):
                                return value

        return None

    def smart_process_block(self, block: Dict, characteristics: List[Dict],
                            block_id: str, fragment_name: str) -> Dict:
        """Умная обработка блока с двухэтапной проверкой и трекингом"""
        original_text = block.get("edited_text", "")
        block_type = block.get("type", "")
        char_name = block.get("characteristic_name", "")
        char_value = block.get("characteristic_value", "")

        # ЭТАП 1: Предобработка ошибок
        error_result = self.error_preprocessor.preprocess_block(block, block_id, fragment_name)

        variables = self.extract_variables(original_text)
        auto_corrected = False
        added_value = None
        auto_correction_transformation = None

        # Автокоррекция для regular блоков без переменных
        if block_type == 'regular' and not variables and char_name and char_value:
            found_value = self.find_specific_value_for_characteristic(
                char_name, char_value, characteristics
            )

            if not found_value:
                clean_value = self._clean_value_for_search(char_value)
                found_value = self.find_specific_value_for_characteristic(
                    char_name, clean_value, characteristics
                )

            if found_value:
                if (found_value not in original_text and
                        f"[{found_value}]" not in original_text and
                        found_value.lower() not in original_text.lower()):
                    new_text = self._insert_value_into_text(original_text, found_value)

                    # Логируем автоисправление
                    auto_correction_transformation = TextTransformation(
                        block_id=block_id,
                        fragment_name=fragment_name,
                        transformation_type=TransformationType.AUTO_INSERT,
                        original=original_text,
                        result=new_text,
                        start=len(original_text),
                        end=len(new_text),
                        meta={
                            "added_value": found_value,
                            "characteristic_name": char_name,
                            "characteristic_value": char_value,
                            "found_value": found_value
                        },
                        severity=SeverityLevel.SUCCESS
                    )
                    self.registry.add(auto_correction_transformation)

                    original_text = new_text
                    auto_corrected = True
                    added_value = found_value
                    error_result['auto_corrected'] = True
                    error_result['added_value'] = found_value

        # Обновляем текст для обработки переменных
        block_for_variables = block.copy()
        block_for_variables['edited_text'] = error_result['cleaned_text']
        if auto_corrected:
            block_for_variables['edited_text'] = original_text

        # ЭТАП 2: Обработка переменных
        variable_result = self.process_block(block_for_variables, characteristics, block_id, fragment_name)

        # Объединяем результаты
        all_transformations = error_result.get('transformations', [])
        if auto_correction_transformation:
            all_transformations.append(auto_correction_transformation)
        all_transformations.extend(variable_result.get('transformations', []))

        combined_result = {
            "original_text": block.get("edited_text", ""),
            "processed_text": variable_result.get("processed_text", ""),
            "replacements": variable_result.get("replacements", []),
            "errors": [],
            "warnings": [],
            "has_errors": bool(error_result.get("special_symbols")) or variable_result.get("has_errors", False),
            "has_warnings": variable_result.get("has_warnings", False) or bool(error_result.get("removed_units")),
            "variables_count": variable_result.get("variables_count", 0),
            "error_details": error_result,
            "auto_corrected": auto_corrected,
            "added_value": added_value,
            "transformations": all_transformations
        }

        # Добавляем специальные символы в ошибки
        special_symbols = error_result.get('special_symbols', [])
        if special_symbols:
            for symbol, start, end in special_symbols:
                combined_result["errors"].append(f"Спецсимвол '{symbol}' на позиции {start}-{end}")

        # Добавляем ошибки из переменных
        if variable_result.get("errors"):
            combined_result["errors"].extend(variable_result["errors"])

        # Добавляем предупреждения
        if error_result.get("has_instructions"):
            combined_result["warnings"].append("Текст может содержать инструкции промпта")

        if error_result.get("removed_units"):
            units_str = ", ".join(error_result["removed_units"])
            combined_result["warnings"].append(f"Удалены единицы измерения: {units_str}")

        if auto_corrected:
            combined_result["warnings"].append(f"Автоматически добавлено значение: [{added_value}]")

        return combined_result


@dataclass
class FragmentBlock:
    """Блок фрагмента с расширенной информацией о трансформациях"""
    id: str
    fragment_name: str
    original_text: str
    processed_text: str
    block_type: str
    characteristic_name: Optional[str] = None
    characteristic_value: Optional[str] = None
    category: Optional[str] = None
    properties: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: str = "pending"
    manual_correction: Optional[str] = None
    manual_review_required: bool = False
    review_notes: Optional[str] = None
    auto_corrected: bool = False
    added_value: Optional[str] = None
    error_details: Optional[Dict] = None
    transformation_ids: List[str] = field(default_factory=list)
    last_processed: datetime = field(default_factory=datetime.now)

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
            'warnings': self.warnings,
            'status': self.status,
            'manual_correction': self.manual_correction,
            'manual_review_required': self.manual_review_required,
            'review_notes': self.review_notes,
            'auto_corrected': self.auto_corrected,
            'added_value': self.added_value,
            'error_details': self.error_details,
            'transformation_ids': self.transformation_ids,
            'last_processed': self.last_processed.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FragmentBlock':
        """Создает объект из словаря"""
        data = data.copy()
        data['last_processed'] = datetime.fromisoformat(data['last_processed'])
        return cls(**data)


class EnhancedFragmentManager:
    """Управление фрагментами с поддержкой трекинга изменений"""

    def __init__(self, category: str, registry: TransformationRegistry):
        self.category = category
        self.registry = registry
        self.fragments: List[FragmentBlock] = []  # ДОБАВИТЬ ЭТУ СТРОКУ
        self.fragment_names: set = set()
        self.fragment_properties: Dict[str, List[Dict]] = defaultdict(list)
        self.template_order: List[str] = []

    def _clean_value_for_name(self, value: str) -> str:
        """Очищает значение для использования в названии фрагмента"""
        if not value:
            return ""
        cleaned = re.sub(r'[^\w\s-]', '', value.lower())
        cleaned = re.sub(r'[\s-]+', '_', cleaned)
        cleaned = cleaned.strip('_')
        if len(cleaned) > 50:
            cleaned = cleaned[:50]
        return cleaned

    def add_block(self, block_data: Dict, transformations: List[TextTransformation] = None) -> FragmentBlock:
        """Добавляет блок и формирует его название по правилам"""
        if block_data.get('type') == 'regular':
            char_name = block_data.get('characteristic_name', '')
            fragment_name = f"{self.category}_{char_name}" if char_name else f"{self.category}_unknown"

        elif block_data.get('type') == 'unique':
            char_name = block_data.get('characteristic_name', '')
            char_value = block_data.get('characteristic_value', '')
            clean_value = self._clean_value_for_name(char_value)

            if char_name and clean_value:
                fragment_name = f"{self.category}_{char_name}_{clean_value}"
            elif char_name:
                fragment_name = f"{self.category}_{char_name}"
            else:
                fragment_name = f"{self.category}_unique_unknown"

        else:
            block_name = block_data.get('block_name', '')
            if block_name:
                clean_name = self._clean_value_for_name(block_name)
                fragment_name = f"{self.category}_{clean_name}"
            else:
                fragment_name = f"{self.category}_other"

        # Создаем объект блока
        fragment_block = FragmentBlock(
            id=block_data.get('id', f"block_{len(self.fragments)}_{uuid.uuid4().hex[:8]}"),
            fragment_name=fragment_name,
            original_text=block_data.get('original_text', ''),
            processed_text=block_data.get('processed_text', ''),
            block_type=block_data.get('type', 'unknown'),
            characteristic_name=block_data.get('characteristic_name'),
            characteristic_value=block_data.get('characteristic_value'),
            category=self.category,
            errors=block_data.get('errors', []),
            warnings=block_data.get('warnings', []),
            status=block_data.get('status', 'processed'),
            manual_correction=block_data.get('manual_correction'),
            auto_corrected=block_data.get('auto_corrected', False),
            added_value=block_data.get('added_value'),
            error_details=block_data.get('error_details')
        )

        # Сохраняем ID трансформаций
        if transformations:
            fragment_block.transformation_ids = [t.id for t in transformations]

        # Формируем свойства фрагмента
        self._extract_properties(fragment_block)

        # Добавляем блок
        self.fragments.append(fragment_block)
        self.fragment_names.add(fragment_name)

        return fragment_block

    def _extract_properties(self, fragment: FragmentBlock):
        """Извлекает свойства из фрагмента"""
        properties = []

        if fragment.block_type == 'regular':
            if fragment.characteristic_name:
                properties.append({
                    'characteristic': fragment.characteristic_name,
                    'value': None,
                    'is_unique': False
                })

        elif fragment.block_type == 'unique':
            if fragment.characteristic_name and fragment.characteristic_value:
                properties.append({
                    'characteristic': fragment.characteristic_name,
                    'value': fragment.characteristic_value,
                    'is_unique': True
                })

        fragment.properties = properties
        for prop in properties:
            self.fragment_properties[fragment.fragment_name].append(prop)

    def rename_fragment(self, old_name: str, new_name: str, user: str = "system") -> bool:
        """Переименовывает фрагмент с трекингом"""
        if old_name not in self.fragment_names:
            return False

        # Логируем переименование
        transformation = TextTransformation(
            block_id="fragment_manager",
            fragment_name=old_name,
            transformation_type=TransformationType.FRAGMENT_RENAME,
            original=old_name,
            result=new_name,
            start=0,
            end=len(old_name),
            meta={"old_name": old_name, "new_name": new_name, "user": user},
            severity=SeverityLevel.INFO,
            user=user
        )
        self.registry.add(transformation)

        # Обновляем фрагменты
        for fragment in self.fragments:
            if fragment.fragment_name == old_name:
                fragment.fragment_name = new_name

        self.fragment_names.remove(old_name)
        self.fragment_names.add(new_name)

        if old_name in self.fragment_properties:
            self.fragment_properties[new_name] = self.fragment_properties.pop(old_name)

        if old_name in self.template_order:
            index = self.template_order.index(old_name)
            self.template_order[index] = new_name

        return True

    def merge_fragments(self, fragment_names: List[str], new_name: str, user: str = "system") -> bool:
        """Склеивает несколько фрагментов в один с трекингом"""
        if not fragment_names or len(fragment_names) < 2:
            return False

        for frag_name in fragment_names:
            if frag_name not in self.fragment_names:
                return False

        # Логируем склеивание
        transformation = TextTransformation(
            block_id="fragment_manager",
            fragment_name=new_name,
            transformation_type=TransformationType.FRAGMENT_MERGE,
            original=", ".join(fragment_names),
            result=new_name,
            start=0,
            end=len(", ".join(fragment_names)),
            meta={"source_fragments": fragment_names, "new_name": new_name, "user": user},
            severity=SeverityLevel.INFO,
            user=user
        )
        self.registry.add(transformation)

        # Обновляем фрагменты
        for fragment in self.fragments:
            if fragment.fragment_name in fragment_names:
                fragment.fragment_name = new_name

        self.fragment_names.difference_update(fragment_names)
        self.fragment_names.add(new_name)

        merged_properties = []
        for frag_name in fragment_names:
            if frag_name in self.fragment_properties:
                merged_properties.extend(self.fragment_properties[frag_name])
                del self.fragment_properties[frag_name]

        if merged_properties:
            self.fragment_properties[new_name] = merged_properties

        positions = [i for i, name in enumerate(self.template_order) if name in fragment_names]
        if positions:
            first_position = min(positions)
            self.template_order = [name for name in self.template_order if name not in fragment_names]
            self.template_order.insert(first_position, new_name)
        else:
            self.template_order.append(new_name)

        return True

    def get_fragment_blocks(self, fragment_name: str) -> List[FragmentBlock]:
        """Возвращает все блоки с указанным названием фрагмента"""
        return [f for f in self.fragments if f.fragment_name == fragment_name]

    def get_all_properties_table(self) -> List[Dict]:
        """Возвращает таблицу всех свойств фрагментов"""
        table_data = []
        seen_properties = set()

        for fragment_name in sorted(self.fragment_names):
            blocks = self.get_fragment_blocks(fragment_name)
            fragment_props = {}

            for block in blocks:
                for prop in block.properties:
                    if prop['characteristic']:
                        key = (prop['characteristic'], prop['value'])
                        if key not in fragment_props:
                            fragment_props[key] = {
                                'fragment_name': fragment_name,
                                'characteristic': prop['characteristic'],
                                'value': prop['value'],
                                'block_type': block.block_type
                            }

            for prop in fragment_props.values():
                table_data.append(prop)

            if not fragment_props:
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
                'has_warnings': any(b.warnings for b in blocks),
                'transformation_count': sum(len(b.transformation_ids) for b in blocks)
            })

        return table_data

    def generate_template_strings(self, category_code: str = None) -> Dict:
        """Генерирует строки шаблонов"""
        if category_code is None:
            category_code = self.category

        fragment_vars = {}
        for fragment_name in self.fragment_names:
            var_name = f"{{fragment {fragment_name}}}"
            fragment_vars[fragment_name] = var_name

        if not self.template_order:
            self.template_order = sorted(self.fragment_names)

        default_order = sorted(self.fragment_names)
        default_template = " ".join(fragment_vars[name] for name in self.template_order
                                    if name in fragment_vars)

        return {
            'category_code': category_code,
            'fragment_variables': fragment_vars,
            'default_order': default_order,
            'current_order': self.template_order,
            'default_template': default_template
        }

    def get_block_by_id(self, block_id: str) -> Optional[FragmentBlock]:
        """Возвращает блок по ID"""
        for block in self.fragments:
            if block.id == block_id:
                return block
        return None

    def get_blocks_with_errors(self) -> List[FragmentBlock]:
        """Возвращает блоки с ошибками"""
        return [block for block in self.fragments if block.errors]

    def get_blocks_with_warnings(self) -> List[FragmentBlock]:
        """Возвращает блоки с предупреждениями"""
        return [block for block in self.fragments if block.warnings]

    def update_block(self, block_id: str, updates: Dict, user: str = "system") -> bool:
        """Обновляет блок по ID с трекингом изменений"""
        for i, block in enumerate(self.fragments):
            if block.id == block_id:
                # Логируем изменения
                for key, value in updates.items():
                    if hasattr(block, key) and getattr(block, key) != value:
                        transformation = TextTransformation(
                            block_id=block_id,
                            fragment_name=block.fragment_name,
                            transformation_type=TransformationType.MANUAL_CORRECTION,
                            original=str(getattr(block, key)),
                            result=str(value),
                            start=0,
                            end=len(str(getattr(block, key))),
                            meta={
                                "field": key,
                                "old_value": getattr(block, key),
                                "new_value": value,
                                "user": user
                            },
                            severity=SeverityLevel.INFO,
                            user=user
                        )
                        self.registry.add(transformation)

                        setattr(block, key, value)

                block.last_processed = datetime.now()
                return True
        return False


class TransformationAuditInterface:
    """Интерфейс для аудита всех трансформаций текста"""

    def __init__(self, registry: TransformationRegistry, fragment_manager: EnhancedFragmentManager = None):
        self.registry = registry
        self.fm = fragment_manager
        initialize_registry()

    def display_main_interface(self):
        """Основной интерфейс аудита трансформаций"""
        st.header("📊 Журнал изменений текста")

        # Статистика
        self._display_stats_cards()

        # Основные вкладки
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Все изменения",
            "⚠️ Ошибки и предупреждения",
            "🔍 Поиск и фильтры",
            "📈 Статистика"
        ])

        with tab1:
            self._display_all_transformations()
        with tab2:
            self._display_issues_tab()
        with tab3:
            self._display_search_interface()
        with tab4:
            self._display_statistics()

    def _display_stats_cards(self):
        """Отображает карточки со статистикой"""
        total = len(self.registry.transformations)
        errors = len(self.registry.get_errors())
        warnings = len(self.registry.get_warnings())
        variable_replaces = len(self.registry.get_by_type(TransformationType.VARIABLE_REPLACE))
        unit_removed = len(self.registry.get_by_type(TransformationType.UNIT_REMOVED))

        cols = st.columns(5)
        with cols[0]:
            st.metric("Всего изменений", total)
        with cols[1]:
            st.metric("Ошибки", errors, delta_color="inverse" if errors > 0 else "off")
        with cols[2]:
            st.metric("Предупреждения", warnings)
        with cols[3]:
            st.metric("Замен переменных", variable_replaces)
        with cols[4]:
            st.metric("Удалено единиц", unit_removed)

    def _display_all_transformations(self):
        """Отображает все трансформации в таблице"""
        st.subheader("Все изменения")

        # Фильтры
        col1, col2, col3 = st.columns(3)

        with col1:
            filter_type = st.selectbox(
                "Тип изменения:",
                ["Все"] + [t.value for t in TransformationType],
                key="all_transformations_type_filter"
            )

        with col2:
            filter_severity = st.selectbox(
                "Критичность:",
                ["Все", "info", "warning", "error", "success"],
                key="all_transformations_severity_filter"
            )

        with col3:
            if self.fm:
                fragment_names = ["Все"] + sorted(list(self.fm.fragment_names))
                selected_fragment = st.selectbox(
                    "Фрагмент:",
                    fragment_names,
                    key="all_transformations_fragment_filter"
                )
            else:
                selected_fragment = "Все"

        # Применяем фильтры
        filtered = self.registry.transformations

        if filter_type != "Все":
            filtered = [t for t in filtered if t.transformation_type.value == filter_type]

        if filter_severity != "Все":
            filtered = [t for t in filtered if t.severity.value == filter_severity]

        if selected_fragment != "Все" and self.fm:
            filtered = [t for t in filtered if t.fragment_name == selected_fragment]

        # Показываем таблицу
        if filtered:
            df = self._transformations_to_dataframe(filtered)

            # Настройки отображения
            col1, col2 = st.columns(2)
            with col1:
                page_size = st.selectbox(
                    "Строк на странице:",
                    [10, 25, 50, 100],
                    key="transformations_page_size"
                )

            with col2:
                group_by_block = st.checkbox(
                    "Группировать по блокам",
                    value=st.session_state.transformation_ui_state.get('group_by_block', False),
                    key="group_by_block_check"
                )
                st.session_state.transformation_ui_state['group_by_block'] = group_by_block

            if group_by_block:
                self._display_grouped_transformations(filtered)
            else:
                # Отображаем таблицу
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=min(len(df) * 35 + 100, 600),
                    column_config={
                        "original": st.column_config.TextColumn("Исходный", width="medium"),
                        "result": st.column_config.TextColumn("Результат", width="medium"),
                        "position": st.column_config.TextColumn("Позиция", width="small"),
                        "severity": st.column_config.TextColumn("Критичность", width="small"),
                        "timestamp": st.column_config.TextColumn("Время", width="medium")
                    }
                )

            # Детали выбранной трансформации
            if st.session_state.get("selected_rows"):
                selected_idx = st.session_state.selected_rows[0]
                if selected_idx < len(filtered):
                    self._display_transformation_details(filtered[selected_idx])
        else:
            st.info("Нет изменений с выбранными фильтрами")

    def _display_issues_tab(self):
        """Вкладка с ошибками и предупреждениями"""
        st.subheader("Проблемные изменения")

        # Разделяем ошибки и предупреждения
        errors = self.registry.get_errors()
        warnings = self.registry.get_warnings()

        tab1, tab2 = st.tabs(["❌ Ошибки", "⚠️ Предупреждения"])

        with tab1:
            if errors:
                st.warning(f"Найдено {len(errors)} ошибок")
                self._display_issues_table(errors, "errors")
            else:
                st.success("🎉 Ошибок не найдено!")

        with tab2:
            if warnings:
                st.info(f"Найдено {len(warnings)} предупреждений")
                self._display_issues_table(warnings, "warnings")
            else:
                st.success("🎉 Предупреждений не найдено!")

    def _display_search_interface(self):
        """Интерфейс расширенного поиска"""
        st.subheader("🔍 Расширенный поиск изменений")

        with st.form("advanced_search_form"):
            col1, col2 = st.columns(2)

            with col1:
                search_text = st.text_input("Текст для поиска:")
                search_in = st.multiselect(
                    "Искать в:",
                    ["original", "result", "meta"],
                    default=["original", "result"]
                )

            with col2:
                date_from = st.date_input("Дата от:")
                date_to = st.date_input("Дата до:", value=datetime.now())
                user_filter = st.text_input("Пользователь:")

            col3, col4 = st.columns(2)
            with col3:
                selected_types = st.multiselect(
                    "Типы изменений:",
                    [t.value for t in TransformationType],
                    default=[TransformationType.VARIABLE_REPLACE.value,
                             TransformationType.UNIT_REMOVED.value]
                )

            with col4:
                selected_severities = st.multiselect(
                    "Критичность:",
                    [s.value for s in SeverityLevel],
                    default=[SeverityLevel.WARNING.value, SeverityLevel.ERROR.value]
                )

            if st.form_submit_button("🔍 Найти", use_container_width=True):
                # Выполняем поиск
                results = self._advanced_search(
                    search_text, search_in, date_from, date_to,
                    user_filter, selected_types, selected_severities
                )

                if results:
                    st.success(f"Найдено {len(results)} изменений")
                    df = self._transformations_to_dataframe(results)
                    st.dataframe(df, use_container_width=True, height=400)

                    # Экспорт результатов
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Экспорт в CSV",
                        data=csv,
                        file_name=f"transformation_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("По вашему запросу ничего не найдено")

    def _display_statistics(self):
        """Отображает статистику по трансформациям"""
        st.subheader("📈 Статистика изменений")

        if not self.registry.transformations:
            st.info("Нет данных для статистики")
            return

        # Общая статистика
        total = len(self.registry.transformations)
        by_type = {}
        by_severity = {}
        by_fragment = {}
        by_hour = defaultdict(int)

        for t in self.registry.transformations:
            # По типам
            type_key = t.transformation_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            # По критичности
            severity_key = t.severity.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1

            # По фрагментам
            fragment_key = t.fragment_name
            by_fragment[fragment_key] = by_fragment.get(fragment_key, 0) + 1

            # По часам
            hour_key = t.timestamp.hour
            by_hour[hour_key] = by_hour.get(hour_key, 0) + 1

        # Визуализация
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Распределение по типам:**")
            type_df = pd.DataFrame({
                'Тип': list(by_type.keys()),
                'Количество': list(by_type.values())
            }).sort_values('Количество', ascending=False)
            st.dataframe(type_df, use_container_width=True, hide_index=True)

        with col2:
            st.write("**Распределение по критичности:**")
            severity_df = pd.DataFrame({
                'Критичность': list(by_severity.keys()),
                'Количество': list(by_severity.values())
            })
            st.dataframe(severity_df, use_container_width=True, hide_index=True)

        # Топ фрагментов
        st.write("**Топ фрагментов по изменениям:**")
        fragment_df = pd.DataFrame({
            'Фрагмент': list(by_fragment.keys()),
            'Изменений': list(by_fragment.values())
        }).sort_values('Изменений', ascending=False).head(10)
        st.dataframe(fragment_df, use_container_width=True, hide_index=True)

        # Активность по часам
        st.write("**Активность по часам:**")
        hours = sorted(by_hour.keys())
        hour_data = {'Час': hours, 'Изменений': [by_hour[h] for h in hours]}
        hour_df = pd.DataFrame(hour_data)
        st.bar_chart(hour_df.set_index('Час'))

    def _transformations_to_dataframe(self, transformations: List[TextTransformation]) -> pd.DataFrame:
        """Конвертирует список трансформаций в DataFrame"""
        data = []
        for t in transformations:
            data.append({
                'ID': t.id[:8],
                'Блок': t.block_id[:8] if t.block_id else '',
                'Фрагмент': t.fragment_name,
                'Тип': t.transformation_type.value,
                'Исходный': t.original[:50] + ('...' if len(t.original) > 50 else ''),
                'Результат': t.result[:50] + ('...' if len(t.result) > 50 else ''),
                'Позиция': f"{t.start}-{t.end}" if t.start != -1 else '',
                'Критичность': t.severity.value,
                'Время': t.timestamp.strftime('%H:%M:%S'),
                'Пользователь': t.user
            })
        return pd.DataFrame(data)

    def _display_grouped_transformations(self, transformations: List[TextTransformation]):
        """Отображает трансформации с группировкой по блокам"""
        # Группируем по block_id
        grouped = defaultdict(list)
        for t in transformations:
            grouped[t.block_id].append(t)

        # Сортируем блоки по количеству изменений
        sorted_blocks = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)

        for block_id, block_transformations in sorted_blocks:
            with st.expander(f"Блок {block_id[:8]} ({len(block_transformations)} изменений)", expanded=False):
                # Сортируем по времени
                block_transformations.sort(key=lambda x: x.timestamp)

                for t in block_transformations:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        severity_color = {
                            "error": "🔴",
                            "warning": "🟡",
                            "info": "🔵",
                            "success": "🟢"
                        }.get(t.severity.value, "⚪")
                        st.write(f"{severity_color} {t.transformation_type.value}")
                    with col2:
                        st.write(f"`{t.original[:30]}` → `{t.result[:30]}`")
                    with col3:
                        st.write(t.timestamp.strftime('%H:%M:%S'))

    def _display_transformation_details(self, transformation: TextTransformation):
        """Отображает детали выбранной трансформации"""
        st.markdown("---")
        st.subheader("🔍 Детали изменения")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** `{transformation.id}`")
            st.write(f"**Тип:** `{transformation.transformation_type.value}`")
            st.write(f"**Блок:** `{transformation.block_id}`")
            st.write(f"**Фрагмент:** `{transformation.fragment_name}`")
            st.write(f"**Пользователь:** `{transformation.user}`")

        with col2:
            severity_badge = {
                "error": "🔴 Критическая",
                "warning": "🟡 Предупреждение",
                "info": "🔵 Информация",
                "success": "🟢 Успех"
            }.get(transformation.severity.value, "⚪ Неизвестно")
            st.write(f"**Критичность:** {severity_badge}")
            st.write(f"**Позиция:** {transformation.start}-{transformation.end}")
            st.write(f"**Время:** {transformation.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**Хэш контекста:** `{transformation.context_hash}`")

        st.markdown("---")
        st.subheader("📝 Изменение текста")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Исходный текст:**")
            if transformation.original:
                st.code(transformation.original, language=None)
            else:
                st.warning("(пусто)")

        with col2:
            st.write("**Результат:**")
            if transformation.result:
                st.code(transformation.result, language=None)
            else:
                st.warning("(удалено)")

        # Diff изменений
        if transformation.original and transformation.result:
            st.markdown("---")
            st.subheader("🔄 Сравнение")

            diff = get_text_diff(transformation.original, transformation.result)
            if diff:
                with st.expander("Показать diff", expanded=False):
                    st.code(diff, language="diff")

        # Метаданные
        if transformation.meta:
            st.markdown("---")
            st.subheader("📋 Метаданные")

            for key, value in transformation.meta.items():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**{key}:**")
                with col2:
                    if isinstance(value, (dict, list)):
                        st.json(value, expanded=False)
                    else:
                        st.write(str(value))

    def _display_issues_table(self, issues: List[TextTransformation], issue_type: str):
        """Отображает таблицу с проблемами"""
        df = self._transformations_to_dataframe(issues)

        # Группируем по фрагментам
        if self.fm:
            fragment_stats = {}
            for issue in issues:
                fragment = issue.fragment_name
                fragment_stats[fragment] = fragment_stats.get(fragment, 0) + 1

            st.write("**Проблемы по фрагментам:**")
            for fragment, count in sorted(fragment_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                st.write(f"- `{fragment}`: {count} проблем")

        # Таблица
        st.dataframe(
            df,
            use_container_width=True,
            height=400,
            column_config={
                "original": st.column_config.TextColumn("Исходный", width="medium"),
                "result": st.column_config.TextColumn("Результат", width="medium")
            }
        )

        # Массовые действия
        if issue_type == "errors" and issues:
            st.markdown("---")
            st.subheader("🚀 Быстрые действия")

            if st.button(f"📋 Экспорт всех {len(issues)} ошибок в CSV", use_container_width=True):
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Скачать CSV",
                    data=csv,
                    file_name=f"errors_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_errors_csv"
                )

    def _advanced_search(self, search_text: str, search_in: List[str], date_from,
                         date_to, user_filter: str, selected_types: List[str],
                         selected_severities: List[str]) -> List[TextTransformation]:
        """Выполняет расширенный поиск"""
        results = []

        for t in self.registry.transformations:
            # Фильтр по дате
            if date_from and t.timestamp.date() < date_from:
                continue
            if date_to and t.timestamp.date() > date_to:
                continue

            # Фильтр по пользователю
            if user_filter and user_filter not in t.user:
                continue

            # Фильтр по типам
            if selected_types and t.transformation_type.value not in selected_types:
                continue

            # Фильтр по критичности
            if selected_severities and t.severity.value not in selected_severities:
                continue

            # Поиск по тексту
            if search_text:
                text_found = False
                if "original" in search_in and search_text.lower() in t.original.lower():
                    text_found = True
                elif "result" in search_in and search_text.lower() in t.result.lower():
                    text_found = True
                elif "meta" in search_in and search_text.lower() in json.dumps(t.meta).lower():
                    text_found = True

                if not text_found:
                    continue

            results.append(t)

        return results


class EnhancedVariableManager:
    """Управление системными переменными с трекингом изменений"""

    def __init__(self, registry: TransformationRegistry):
        self.registry = registry
        self.variables_dir = Path("config/variables")
        self.variables_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.variables_dir / "settings.json"
        self.prefixes = {
            "prop": "prop",
            "system": "system",
            "fragment": "fragment"
        }
        self.load_settings()

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

    def load_settings(self):
        """Загружает настройки префиксов"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.prefixes = settings.get('prefixes', self.prefixes)
            except:
                self.save_settings()

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

    def save_settings(self):
        """Сохраняет настройки префиксов"""
        settings = {'prefixes': self.prefixes}
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    def save_variables(self):
        """Сохраняет переменные в файл"""
        var_file = self.variables_dir / "system_variables.json"
        with open(var_file, 'w', encoding='utf-8') as f:
            json.dump(self.system_vars, f, ensure_ascii=False, indent=2)

    def update_prefix(self, prefix_type: str, value: str, user: str = "system"):
        """Обновляет префикс с трекингом"""
        if prefix_type in self.prefixes:
            old_value = self.prefixes[prefix_type]

            # Логируем изменение
            transformation = TextTransformation(
                block_id="variable_manager",
                fragment_name="system",
                transformation_type=TransformationType.TEXT_CLEANING,
                original=f"{{{old_value} var}}",
                result=f"{{{value} var}}",
                start=0,
                end=len(f"{{{old_value} var}}"),
                meta={
                    "prefix_type": prefix_type,
                    "old_value": old_value,
                    "new_value": value,
                    "user": user
                },
                severity=SeverityLevel.INFO,
                user=user
            )
            self.registry.add(transformation)

            self.prefixes[prefix_type] = value
            self.save_settings()

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

    def add_variable(self, name: str, variants: List[Dict], description: str = "", user: str = "system"):
        """Добавляет новую переменную с трекингом"""
        # Логируем добавление
        transformation = TextTransformation(
            block_id="variable_manager",
            fragment_name="system",
            transformation_type=TransformationType.TEXT_CLEANING,
            original="",
            result=f"[{name}]",
            start=0,
            end=0,
            meta={
                "action": "add_variable",
                "name": name,
                "variants_count": len(variants),
                "description": description,
                "user": user
            },
            severity=SeverityLevel.SUCCESS,
            user=user
        )
        self.registry.add(transformation)

        self.system_vars[name] = {
            "variants": variants,
            "description": description
        }
        self.save_variables()

    def edit_variable(self, old_name: str, new_name: str, variants: List[Dict],
                      description: str = "", user: str = "system"):
        """Редактирует переменную с трекингом"""
        if old_name in self.system_vars:
            # Логируем изменение
            transformation = TextTransformation(
                block_id="variable_manager",
                fragment_name="system",
                transformation_type=TransformationType.TEXT_CLEANING,
                original=old_name,
                result=new_name,
                start=0,
                end=len(old_name),
                meta={
                    "action": "edit_variable",
                    "old_name": old_name,
                    "new_name": new_name,
                    "variants_count": len(variants),
                    "description": description,
                    "user": user
                },
                severity=SeverityLevel.INFO,
                user=user
            )
            self.registry.add(transformation)

            self.system_vars[new_name] = {
                "variants": variants,
                "description": description
            }
            if old_name != new_name:
                del self.system_vars[old_name]
            self.save_variables()

    def delete_variable(self, name: str, user: str = "system"):
        """Удаляет переменную с трекингом"""
        if name in self.system_vars:
            # Логируем удаление
            transformation = TextTransformation(
                block_id="variable_manager",
                fragment_name="system",
                transformation_type=TransformationType.TEXT_CLEANING,
                original=f"[{name}]",
                result="",
                start=0,
                end=len(f"[{name}]"),
                meta={
                    "action": "delete_variable",
                    "name": name,
                    "user": user
                },
                severity=SeverityLevel.WARNING,
                user=user
            )
            self.registry.add(transformation)

            del self.system_vars[name]
            self.save_variables()

    def get_all_variables(self) -> List[Dict]:
        """Возвращает список всех переменных"""
        variables = []
        for name, info in self.system_vars.items():
            variables.append({
                "name": name,
                "description": info.get("description", ""),
                "variants": info.get("variants", []),
                "variants_count": len(info.get("variants", []))
            })
        return variables


class Phase6EnhancedProcessorWithAudit:
    """Улучшенный процессор фазы 6 с полной системой аудита"""

    def __init__(self, app_state, input_data=None):
        self.app_state = app_state
        self.input_data = input_data or {}

        # Инициализация реестра
        initialize_registry()
        self.registry = st.session_state.transformation_registry

        # Инициализация менеджеров
        self.vm = EnhancedVariableManager(self.registry)
        self.text_processor = EnhancedTextProcessor(self.vm, self.registry)

        self.category = self.input_data.get('category', '')
        if not self.category:
            phase1_data = self.input_data.get('phase1_data', {})
            self.category = phase1_data.get('category', 'Без_категории')

        self.fragment_manager = EnhancedFragmentManager(self.category, self.registry)
        self.characteristics = []

        # Интерфейсы
        self.audit_interface = TransformationAuditInterface(self.registry, self.fragment_manager)

        # Инициализация состояния
        if 'phase6_audit_data' not in st.session_state:
            st.session_state.phase6_audit_data = {
                'fragments_processed': False,
                'processing_time': None,
                'total_blocks': 0,
                'stats': {
                    'transformations': 0,
                    'errors': 0,
                    'warnings': 0,
                    'auto_corrections': 0,
                    'variable_replacements': 0,
                    'units_removed': 0
                }
            }

    def load_and_process_data(self, force_reload: bool = False) -> bool:
        """Загружает и обрабатывает данные из фазы 5 с полным трекингом"""
        try:
            # Очищаем предыдущие данные
            if force_reload:
                self.registry.clear()
                self.fragment_manager = EnhancedFragmentManager(self.category, self.registry)
                st.session_state.phase6_audit_data['fragments_processed'] = False

            if 'app_data' in st.session_state and 'phase5' in st.session_state.app_data:
                phase5_data = st.session_state.app_data['phase5']
            else:
                st.error("❌ Нет данных из фазы 5")
                return False

            if not phase5_data.get('phase_completed', False):
                st.warning("⚠️ Фаза 5 не завершена")
                return False

            # Извлекаем характеристики
            phase1_data = self.input_data.get('phase1_data', {})
            if phase1_data and 'characteristics' in phase1_data:
                self.characteristics = phase1_data['characteristics']
            else:
                self.characteristics = self._extract_characteristics_from_phase5(phase5_data)

            results = phase5_data.get('results', [])
            if not results:
                st.warning("Нет результатов для обработки")
                return False

            # Обработка блоков
            total_blocks = 0
            stats = {
                'transformations': 0,
                'errors': 0,
                'warnings': 0,
                'auto_corrections': 0,
                'variable_replacements': 0,
                'units_removed': 0
            }

            for result in results:
                if result.get('status') != 'success':
                    continue

                total_blocks += 1

                # Используем len(self.fragment_manager.fragments) для генерации ID
                block_data = {
                    'id': result.get('prompt_id', f"block_{total_blocks}_{uuid.uuid4().hex[:8]}"),
                    'original_text': result.get('edited_text', ''),
                    'edited_text': result.get('edited_text', ''),
                    'type': result.get('type', 'other'),
                    'characteristic_name': result.get('characteristic_name'),
                    'characteristic_value': result.get('characteristic_value'),
                    'block_name': result.get('block_name', ''),
                    'errors': [],
                    'warnings': [],
                    'status': 'pending'
                }

                # Обрабатываем блок
                processed_result = self.text_processor.process_block(
                    block_data,
                    self.characteristics,
                    block_data['id'],
                    f"fragment_{total_blocks}"  # Временное имя фрагмента
                )

                # Обновляем статистику
                transformations = processed_result.get('transformations', [])
                stats['transformations'] += len(transformations)

                for t in transformations:
                    if t.severity == SeverityLevel.ERROR:
                        stats['errors'] += 1
                    elif t.severity == SeverityLevel.WARNING:
                        stats['warnings'] += 1
                    elif t.transformation_type == TransformationType.AUTO_INSERT:
                        stats['auto_corrections'] += 1
                    elif t.transformation_type == TransformationType.VARIABLE_REPLACE:
                        stats['variable_replacements'] += 1
                    elif t.transformation_type == TransformationType.UNIT_REMOVED:
                        stats['units_removed'] += 1

                # Обновляем данные блока
                block_data.update({
                    'processed_text': processed_result.get('processed_text', ''),
                    'errors': processed_result.get('errors', []),
                    'warnings': processed_result.get('warnings', []),
                    'status': 'error' if processed_result.get('has_errors', False) else 'processed',
                    'auto_corrected': processed_result.get('auto_corrected', False),
                    'added_value': processed_result.get('added_value', None),
                    'error_details': processed_result.get('error_details', {})
                })

                # Добавляем блок в менеджер
                try:
                    fragment_block = self.fragment_manager.add_block(block_data, transformations)
                except Exception as e:
                    st.error(f"Ошибка при добавлении блока: {str(e)}")
                    continue

            # Сохраняем результаты
            st.session_state.phase6_audit_data.update({
                'fragments_processed': True,
                'fragment_manager': self.fragment_manager,
                'text_processor': self.text_processor,
                'characteristics': self.characteristics,
                'processing_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_blocks': total_blocks,
                'stats': stats
            })

            if total_blocks > 0:
                st.success(f"✅ Обработано {total_blocks} блоков")

                # Показываем статистику трансформаций
                with st.expander("📊 Статистика обработки", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Всего изменений", stats['transformations'])
                        st.metric("Замен переменных", stats['variable_replacements'])
                        st.metric("Автоисправлений", stats['auto_corrections'])
                    with col2:
                        st.metric("Ошибок", stats['errors'])
                        st.metric("Предупреждений", stats['warnings'])
                        st.metric("Удалено единиц", stats['units_removed'])

            return True

        except Exception as e:
            st.error(f"Ошибка при обработке данных: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return False

    def _extract_characteristics_from_phase5(self, phase5_data: Dict) -> List[Dict]:
        """Извлекает характеристики из данных фазы 5"""
        characteristics = {}

        results = phase5_data.get('results', [])
        for result in results:
            char_name = result.get('characteristic_name')
            char_value = result.get('characteristic_value')

            if not char_name or not char_value:
                continue

            char_name = char_name.strip()
            char_value = str(char_value).strip()

            if char_name not in characteristics:
                characteristics[char_name] = {
                    'name': char_name,
                    'data': {}
                }

            char_data = characteristics[char_name]['data']
            if char_value and char_value not in char_data.values():
                key = f"value_{len(char_data) + 1}"
                char_data[key] = char_value

        return list(characteristics.values())

    def display_main_interface(self):
        """Основной интерфейс фазы 6 с системой аудита"""
        st.title("🚀 Фаза 6: Подготовка к загрузке на сайт")
        st.markdown("---")

        # Проверяем, обработаны ли данные
        if not st.session_state.phase6_audit_data.get('fragments_processed', False):
            self._display_initial_interface()
            return

        # Загружаем менеджер фрагментов
        if 'fragment_manager' in st.session_state.phase6_audit_data:
            self.fragment_manager = st.session_state.phase6_audit_data['fragment_manager']

        # Основные вкладки
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Обзор",
            "🏷️ Фрагменты",
            "⚠️ Проблемы",
            "📋 Аудит изменений",
            "🧩 Шаблоны",
            "⚙️ Настройки"
        ])

        with tab1:
            self._display_overview_interface()
        with tab2:
            self._display_fragments_interface()
        with tab3:
            self._display_problems_interface()
        with tab4:
            self.audit_interface.display_main_interface()
        with tab5:
            self._display_templates_interface()
        with tab6:
            self._display_settings_interface()

    def _display_initial_interface(self):
        """Интерфейс начальной загрузки данных"""
        st.info("""
        ## 📥 Подготовка данных для сайта

        **Что будет сделано:**
        1. Вставка переменных с трекингом изменений
        2. Выявление ошибок и ручная правка
        3. Форматирование результатов
        4. Подготовка шаблонов для сайта
        5. Полный аудит всех изменений
        """)

        if 'app_data' in st.session_state and 'phase5' in st.session_state.app_data:
            phase5_data = st.session_state.app_data['phase5']
            stats = phase5_data.get('statistics', {})
            success_count = stats.get('success', 0)

            st.write(f"**Найдено {success_count} текстов для обработки**")

        if st.button("🚀 Начать обработку данных с трекингом", type="primary",
                     use_container_width=True, key="start_audit_processing"):
            with st.spinner("Обработка данных с полным трекингом изменений..."):
                if self.load_and_process_data():
                    st.success("✅ Данные успешно обработаны с полным аудитом!")
                    st.rerun()
                else:
                    st.error("❌ Не удалось обработать данные")

    def _display_overview_interface(self):
        """Интерфейс обзора"""
        st.header("📊 Обзор проекта")

        # Статистика проекта
        if hasattr(self, 'fragment_manager') and self.fragment_manager:
            total_fragments = len(self.fragment_manager.fragment_names)
            total_blocks = len(self.fragment_manager.fragments)
            error_blocks = len(self.fragment_manager.get_blocks_with_errors())
            warning_blocks = len(self.fragment_manager.get_blocks_with_warnings())
        else:
            total_fragments = 0
            total_blocks = 0
            error_blocks = 0
            warning_blocks = 0

        # Статистика трансформаций
        stats = st.session_state.phase6_audit_data.get('stats', {})

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Фрагментов", total_fragments)
        with col2:
            st.metric("Блоков", total_blocks)
        with col3:
            st.metric("Блоков с ошибками", error_blocks, delta_color="inverse")
        with col4:
            st.metric("Блоков с предупреждениями", warning_blocks)

        st.divider()

        # Статистика изменений
        st.subheader("📈 Статистика изменений")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Всего изменений", stats.get('transformations', 0))
        with col2:
            st.metric("Замен переменных", stats.get('variable_replacements', 0))
        with col3:
            st.metric("Удалено единиц", stats.get('units_removed', 0))
        with col4:
            st.metric("Автоисправлений", stats.get('auto_corrections', 0))

        st.divider()

        # Быстрые действия
        st.subheader("🚀 Быстрые действия")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Обновить из фазы 5", use_container_width=True,
                         help="Перезагрузить данные из фазы 5"):
                if self.load_and_process_data(force_reload=True):
                    st.success("✅ Данные обновлены!")
                    st.rerun()

        with col2:
            if st.button("📊 Экспорт отчета", use_container_width=True,
                         help="Экспортировать полный отчет"):
                self._export_complete_report()

        with col3:
            if st.button("🗑️ Очистить аудит", use_container_width=True,
                         help="Очистить журнал изменений"):
                self.registry.clear()
                st.success("✅ Журнал изменений очищен!")
                st.rerun()

    def _display_fragments_interface(self):
        """Интерфейс управления фрагментами"""
        st.header("🏷️ Управление фрагментами")

        tab1, tab2, tab3 = st.tabs(["Список", "Переименование", "Свойства"])

        with tab1:
            self._display_fragments_list()

        with tab2:
            self._display_fragment_rename_interface()

        with tab3:
            self._display_fragment_properties()

    def _display_fragments_list(self):
        """Отображает список фрагментов"""
        fragment_names = list(self.fragment_manager.fragment_names)

        if not fragment_names:
            st.info("Нет фрагментов")
            return

        st.write(f"Всего фрагментов: **{len(fragment_names)}**")

        table_data = []
        for frag_name in fragment_names:
            blocks = self.fragment_manager.get_fragment_blocks(frag_name)
            block_types = list(set(b.block_type for b in blocks))

            # Собираем статистику по блоку
            error_count = sum(len(b.errors) for b in blocks)
            warning_count = sum(len(b.warnings) for b in blocks)
            transformation_count = sum(len(b.transformation_ids) for b in blocks)

            table_data.append({
                'Фрагмент': frag_name,
                'Блоков': len(blocks),
                'Типы': ', '.join(block_types),
                'Ошибки': error_count,
                'Предупреждения': warning_count,
                'Изменений': transformation_count,
                'Статус': '⚠️' if error_count > 0 else '✅'
            })

        df_fragments = pd.DataFrame(table_data)
        st.dataframe(df_fragments, use_container_width=True, height=400)

    def _display_fragment_rename_interface(self):
        """Интерфейс переименования фрагментов"""
        st.subheader("✏️ Переименование фрагментов")

        fragment_names = list(self.fragment_manager.fragment_names)

        if not fragment_names:
            st.info("Нет фрагментов для переименования")
            return

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
                if self.fragment_manager.rename_fragment(selected_fragment, new_name, user="user"):
                    st.success(f"Фрагмент переименован: {selected_fragment} → {new_name}")
                    st.rerun()
                else:
                    st.error("Ошибка при переименовании")

    def _display_fragment_properties(self):
        """Отображает свойства фрагментов"""
        st.subheader("📊 Свойства фрагментов")

        properties_table = self.fragment_manager.get_all_properties_table()

        if not properties_table:
            st.info("Нет данных о свойствах")
            return

        df_properties = pd.DataFrame(properties_table)
        st.dataframe(df_properties, use_container_width=True)

    def _display_problems_interface(self):
        """Интерфейс проблем с рабочими массовыми действиями"""
        st.header("⚠️ Проблемы и ошибки")

        # Получаем блоки с проблемами
        error_blocks = self.fragment_manager.get_blocks_with_errors()
        warning_blocks = self.fragment_manager.get_blocks_with_warnings()

        tab1, tab2, tab3 = st.tabs(["❌ Ошибки", "⚠️ Предупреждения", "🔧 Ручное исправление"])

        with tab1:
            if error_blocks:
                st.error(f"Найдено {len(error_blocks)} блоков с ошибками")
                self._display_problems_table(error_blocks, "errors", show_correction=True)
            else:
                st.success("🎉 Блоков с ошибками не найдено!")

        with tab2:
            if warning_blocks:
                st.warning(f"Найдено {len(warning_blocks)} блоков с предупреждениями")
                self._display_problems_table(warning_blocks, "warnings", show_correction=False)
            else:
                st.success("🎉 Блоков с предупреждениями не найдено!")

        with tab3:
            self._display_manual_correction_interface()

    def _display_problems_table(self, blocks: List[FragmentBlock], problem_type: str, show_correction: bool = True):
        """Отображает таблицу с проблемами и массовыми действиями"""
        if not blocks:
            return

        # Группируем ошибки по типам для анализа
        error_types = defaultdict(list)
        for block in blocks:
            for error in block.errors:
                error_types[error].append(block.id)

        # Показываем статистику по типам ошибок
        if error_types:
            with st.expander("📊 Анализ ошибок", expanded=True):
                for error_msg, block_ids in error_types.items():
                    st.write(f"**{error_msg}** - {len(block_ids)} блоков")

        # Таблица блоков
        table_data = []
        for block in blocks:
            table_data.append({
                "ID": block.id,
                "Фрагмент": block.fragment_name,
                "Тип": block.block_type,
                "Характеристика": block.characteristic_name or "-",
                "Значение": block.characteristic_value or "-",
                "Ошибки": len(block.errors),
                "Предупреждения": len(block.warnings),
                "Статус": block.status,
                "Автоисправлен": "✅" if block.auto_corrected else "❌",
                "Текст": block.original_text[:80] + "..." if len(block.original_text) > 80 else block.original_text
            })

        df = pd.DataFrame(table_data)

        # Используем уникальный ключ для каждой таблицы
        table_key = f"problems_table_{problem_type}_{int(time.time())}"
        st.dataframe(df, use_container_width=True, height=400, key=table_key)

        # Массовые действия
        st.subheader("⚡ Массовые действия")

        col1, col2 = st.columns(2)
        with col1:
            action_type = st.selectbox(
                "Действие:",
                ["Принять блоки", "Автоисправление", "Пометить как проверенные", "Удалить блоки"],
                key=f"mass_action_{problem_type}"
            )

        with col2:
            if st.button("🔍 Выбрать все с этой ошибкой",
                         key=f"select_all_{problem_type}_{int(time.time())}"):
                # Логика выбора всех блоков с наиболее частой ошибкой
                if error_types:
                    most_common_error = max(error_types.items(), key=lambda x: len(x[1]))[0]
                    st.session_state[f"selected_blocks_{problem_type}"] = error_types[most_common_error]
                    st.rerun()

        # Выбор блоков для массовых действий
        selected_ids = st.multiselect(
            "Выберите блоки для обработки:",
            [block.id for block in blocks],
            default=st.session_state.get(f"selected_blocks_{problem_type}", []),
            key=f"mass_action_select_{problem_type}_{int(time.time())}"
        )

        if selected_ids and st.button(f"Применить '{action_type}' к выбранным",
                                      key=f"apply_mass_action_{problem_type}_{int(time.time())}",
                                      type="primary"):

            if action_type == "Принять блоки":
                self._mass_accept_blocks(selected_ids)
            elif action_type == "Автоисправление":
                self._mass_auto_correct(selected_ids)
            elif action_type == "Пометить как проверенные":
                self._mass_mark_as_reviewed(selected_ids)
            elif action_type == "Удалить блоки":
                self._mass_delete_blocks(selected_ids)

            st.success(f"Обработано {len(selected_ids)} блоков")
            st.rerun()

        # Показываем детали выбранного блока
        if selected_ids and len(selected_ids) == 1:
            block = self.fragment_manager.get_block_by_id(selected_ids[0])
            if block:
                self._display_block_details(block, show_correction)

    def _display_manual_correction_interface(self):
        """Интерфейс ручного исправления блоков"""
        st.subheader("🔧 Ручное исправление")

        # Фильтр для поиска блоков
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_status = st.selectbox(
                "Статус:",
                ["Все", "pending", "error", "fixed", "accepted"],
                key="correction_filter_status"
            )

        with col2:
            filter_type = st.selectbox(
                "Тип блока:",
                ["Все", "regular", "unique", "other"],
                key="correction_filter_type"
            )

        with col3:
            search_text = st.text_input("Поиск по тексту:", key="correction_search")

        # Фильтруем блоки
        filtered_blocks = []
        for block in self.fragment_manager.fragments:
            if filter_status != "Все" and block.status != filter_status:
                continue
            if filter_type != "Все" and block.block_type != filter_type:
                continue
            if search_text and search_text.lower() not in block.original_text.lower():
                continue
            filtered_blocks.append(block)

        if not filtered_blocks:
            st.info("Блоки не найдены по заданным фильтрам")
            return

        # Выбор блока для редактирования
        selected_block_id = st.selectbox(
            "Выберите блок для редактирования:",
            [f"{b.id} - {b.fragment_name} ({len(b.errors)} ошибок)" for b in filtered_blocks],
            key="select_block_for_correction"
        )

        if selected_block_id:
            block_id = selected_block_id.split(" - ")[0]
            block = self.fragment_manager.get_block_by_id(block_id)

            if block:
                self._display_block_editor(block)

    def _display_block_details(self, block: FragmentBlock, show_correction: bool = True):
        """Отображает детали блока с возможностью исправления"""
        st.markdown("---")
        st.subheader(f"📝 Детали блока: {block.id}")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Фрагмент:** {block.fragment_name}")
            st.write(f"**Тип:** {block.block_type}")
            if block.characteristic_name:
                st.write(f"**Характеристика:** {block.characteristic_name}")
            if block.characteristic_value:
                st.write(f"**Значение:** {block.characteristic_value}")

        with col2:
            status_badges = {
                'pending': '🟡 Ожидает',
                'error': '🔴 Ошибка',
                'fixed': '🟢 Исправлен',
                'accepted': '✅ Принят'
            }
            st.write(f"**Статус:** {status_badges.get(block.status, block.status)}")
            st.write(f"**Автоисправлен:** {'✅ Да' if block.auto_corrected else '❌ Нет'}")

        # Ошибки и предупреждения
        if block.errors:
            st.markdown("---")
            st.subheader("❌ Ошибки")
            for error in block.errors:
                st.error(f"• {error}")

        if block.warnings:
            st.markdown("---")
            st.subheader("⚠️ Предупреждения")
            for warning in block.warnings:
                st.warning(f"• {warning}")

        # Тексты
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Исходный текст")
            st.text_area("", value=block.original_text, height=150, disabled=True,
                         key=f"original_{block.id}")

        with col2:
            st.subheader("Обработанный текст")
            if block.processed_text:
                st.code(block.processed_text)
            else:
                st.info("Текст не обработан")

        # Действия по исправлению
        if show_correction:
            st.markdown("---")
            st.subheader("⚡ Действия")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("✏️ Редактировать",
                             key=f"edit_{block.id}_{int(time.time())}",
                             use_container_width=True):
                    st.session_state[f"editing_block_{block.id}"] = True
                    st.rerun()

            with col2:
                if st.button("✅ Принять",
                             key=f"accept_{block.id}_{int(time.time())}",
                             use_container_width=True):
                    self.fragment_manager.update_block(
                        block.id,
                        {"status": "accepted", "manual_correction": "Принято вручную"},
                        user="user"
                    )
                    st.success("Блок принят!")
                    st.rerun()

            with col3:
                if st.button("🔄 Автоисправление",
                             key=f"auto_{block.id}_{int(time.time())}",
                             use_container_width=True):
                    self._auto_correct_single_block(block)
                    st.rerun()

            with col4:
                if st.button("🗑️ Удалить",
                             key=f"delete_{block.id}_{int(time.time())}",
                             use_container_width=True,
                             type="secondary"):
                    if st.checkbox(f"Подтвердить удаление блока {block.id}"):
                        self._delete_single_block(block.id)
                        st.rerun()

            # Редактор блока
            if st.session_state.get(f"editing_block_{block.id}", False):
                self._display_block_editor(block)

    def _display_block_editor(self, block: FragmentBlock):
        """Отображает редактор для блока"""
        st.markdown("---")
        st.subheader("✏️ Редактирование блока")

        # Редактор текста
        edited_text = st.text_area(
            "Текст блока:",
            value=block.original_text,
            height=200,
            key=f"editor_{block.id}"
        )

        # Предпросмотр обработки
        if st.button("🔄 Предпросмотр обработки",
                     key=f"preview_{block.id}_{int(time.time())}"):
            block_data = {
                "edited_text": edited_text,
                "type": block.block_type,
                "characteristic_name": block.characteristic_name,
                "characteristic_value": block.characteristic_value
            }

            result = self.text_processor.process_block(
                block_data,
                self.characteristics,
                block.id,
                block.fragment_name
            )

            st.subheader("Предпросмотр:")
            st.code(result.get("processed_text", ""))

            if result.get("errors"):
                st.error("Ошибки:")
                for error in result["errors"]:
                    st.error(f"• {error}")

            if result.get("warnings"):
                st.warning("Предупреждения:")
                for warning in result["warnings"]:
                    st.warning(f"• {warning}")

        # Кнопки сохранения
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Сохранить изменения",
                         key=f"save_{block.id}_{int(time.time())}",
                         type="primary",
                         use_container_width=True):
                block_data = {
                    "edited_text": edited_text,
                    "type": block.block_type,
                    "characteristic_name": block.characteristic_name,
                    "characteristic_value": block.characteristic_value
                }

                result = self.text_processor.process_block(
                    block_data,
                    self.characteristics,
                    block.id,
                    block.fragment_name
                )

                # Обновляем блок
                updates = {
                    "original_text": edited_text,
                    "processed_text": result.get("processed_text", ""),
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                    "status": "fixed" if not result.get("has_errors", False) else "error",
                    "manual_correction": edited_text
                }

                self.fragment_manager.update_block(block.id, updates, user="user")
                st.session_state[f"editing_block_{block.id}"] = False
                st.success("Блок сохранен!")
                st.rerun()

        with col2:
            if st.button("🚫 Отмена",
                         key=f"cancel_{block.id}_{int(time.time())}",
                         use_container_width=True):
                st.session_state[f"editing_block_{block.id}"] = False
                st.rerun()

    # 3. Добавляем методы массовых действий

    def _mass_accept_blocks(self, block_ids: List[str]):
        """Массовое принятие блоков"""
        for block_id in block_ids:
            block = self.fragment_manager.get_block_by_id(block_id)
            if block:
                self.fragment_manager.update_block(
                    block_id,
                    {"status": "accepted", "manual_correction": "Принято массово"},
                    user="user"
                )

    def _mass_auto_correct(self, block_ids: List[str]):
        """Массовое автоисправление блоков"""
        for block_id in block_ids:
            block = self.fragment_manager.get_block_by_id(block_id)
            if block and self.text_processor:
                block_data = {
                    "edited_text": block.original_text,
                    "type": block.block_type,
                    "characteristic_name": block.characteristic_name,
                    "characteristic_value": block.characteristic_value
                }

                result = self.text_processor.process_block(
                    block_data,
                    self.characteristics,
                    block.id,
                    block.fragment_name
                )

                updates = {
                    "original_text": block.original_text,
                    "processed_text": result.get("processed_text", ""),
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                    "status": "fixed" if not result.get("has_errors", False) else "error",
                    "auto_corrected": True
                }

                self.fragment_manager.update_block(block.id, updates, user="system")

    def _mass_mark_as_reviewed(self, block_ids: List[str]):
        """Массовая пометка блоков как проверенных"""
        for block_id in block_ids:
            self.fragment_manager.update_block(
                block_id,
                {"status": "fixed", "manual_review_required": False},
                user="user"
            )

    def _mass_delete_blocks(self, block_ids: List[str]):
        """Массовое удаление блоков"""
        for block_id in block_ids:
            self._delete_single_block(block_id)

    def _delete_single_block(self, block_id: str):
        """Удаление одного блока"""
        for i, block in enumerate(self.fragment_manager.fragments):
            if block.id == block_id:
                self.fragment_manager.fragments.pop(i)
                break
        # Также нужно удалить из fragment_names если это был последний блок с таким именем
        self._cleanup_fragment_names()

    def _cleanup_fragment_names(self):
        """Очищает fragment_names от пустых фрагментов"""
        if not hasattr(self.fragment_manager, 'fragments'):
            return

        # Собираем актуальные имена фрагментов
        active_fragments = set()
        for block in self.fragment_manager.fragments:
            active_fragments.add(block.fragment_name)

        # Удаляем неактивные имена
        self.fragment_manager.fragment_names = active_fragments
    def _auto_correct_single_block(self, block: FragmentBlock):
        """Автоисправление одного блока"""
        if not self.text_processor:
            return

        block_data = {
            "edited_text": block.original_text,
            "type": block.block_type,
            "characteristic_name": block.characteristic_name,
            "characteristic_value": block.characteristic_value
        }

        result = self.text_processor.process_block(
            block_data,
            self.characteristics,
            block.id,
            block.fragment_name
        )

        updates = {
            "original_text": block.original_text,
            "processed_text": result.get("processed_text", ""),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "status": "fixed" if not result.get("has_errors", False) else "error",
            "auto_corrected": True
        }

        self.fragment_manager.update_block(block.id, updates, user="system")
    def _display_templates_interface(self):
        """Упрощенный интерфейс шаблонов"""
        st.header("🧩 Шаблоны")

        fragments = sorted(self.fragment_manager.fragment_names)

        if not fragments:
            st.info("Нет фрагментов для создания шаблона")
            return

        selected = st.multiselect(
            "Выберите фрагменты для шаблона:",
            fragments,
            default=self.fragment_manager.template_order or fragments[:min(5, len(fragments))]
        )

        if selected:
            st.write("**Порядок фрагментов:**")

            for i in range(len(selected)):
                col1, col2, col3, col4 = st.columns([1, 4, 1, 1])

                with col1:
                    st.write(f"{i + 1}.")

                with col2:
                    st.write(selected[i])

                with col3:
                    if st.button("↑", key=f"up_{i}", disabled=(i == 0)):
                        selected[i], selected[i - 1] = selected[i - 1], selected[i]
                        st.rerun()

                with col4:
                    if st.button("↓", key=f"down_{i}", disabled=(i == len(selected) - 1)):
                        selected[i], selected[i + 1] = selected[i + 1], selected[i]
                        st.rerun()

        if st.button("💾 Сохранить порядок", use_container_width=True):
            self.fragment_manager.template_order = selected
            st.session_state.phase6_audit_data['template_order'] = selected
            st.success("Порядок сохранен!")

        if selected:
            category_code = self.category
            template_data = self.fragment_manager.generate_template_strings(category_code)

            template_parts = [template_data['fragment_variables'][f] for f in selected if
                              f in template_data['fragment_variables']]
            template_string = " ".join(template_parts)

            st.subheader("📋 Итоговый шаблон")
            st.code(template_string, language=None)

            st.download_button(
                label="📋 Скопировать шаблон",
                data=template_string,
                file_name=f"template_{category_code}.txt",
                mime="text/plain"
            )

    def _display_settings_interface(self):
        """Интерфейс настроек"""
        st.header("⚙️ Настройки")

        tab1, tab2, tab3 = st.tabs(["Переменные", "Префиксы", "Экспорт данных"])

        with tab1:
            self._display_variable_management()

        with tab2:
            self._display_prefix_settings()

        with tab3:
            self._display_export_interface()

    def _display_variable_management(self):
        """Управление переменными"""
        st.subheader("⚙️ Управление системными переменными")

        variables = self.vm.get_all_variables()

        if not variables:
            st.info("Нет системных переменных")
            return

        # Таблица переменных
        var_data = []
        for var in variables:
            var_data.append({
                "Название": var["name"],
                "Описание": var["description"],
                "Вариантов": var["variants_count"],
                "Пример": var["variants"][0]["value"] if var["variants"] else "Нет вариантов"
            })

        df_vars = pd.DataFrame(var_data)
        st.dataframe(df_vars, use_container_width=True, hide_index=True)

        # Детальный просмотр
        selected_var = st.selectbox(
            "Выберите переменную для детального просмотра:",
            [var["name"] for var in variables],
            key="var_detail_select"
        )

        if selected_var:
            var_info = self.vm.system_vars.get(selected_var)
            if var_info:
                st.write(f"**Описание:** {var_info.get('description', 'Нет описания')}")
                st.write("**Варианты:**")
                for i, variant in enumerate(var_info.get("variants", []), 1):
                    with st.expander(f"Вариант {i}"):
                        st.write(f"**Значение:** `{variant.get('value', '')}`")
                        st.write(f"**Контекст:** `{variant.get('context', 'Любой контекст')}`")

    def _display_prefix_settings(self):
        """Настройка префиксов"""
        st.subheader("🏷️ Настройка префиксов")

        col1, col2, col3 = st.columns(3)

        with col1:
            prop_prefix = st.text_input(
                "Префикс для свойств:",
                value=self.vm.prefixes.get('prop', 'prop'),
                key="settings_prop_prefix"
            )

        with col2:
            system_prefix = st.text_input(
                "Префикс для системных переменных:",
                value=self.vm.prefixes.get('system', 'system'),
                key="settings_system_prefix"
            )

        with col3:
            fragment_prefix = st.text_input(
                "Префикс для фрагментов:",
                value=self.vm.prefixes.get('fragment', 'fragment'),
                key="settings_fragment_prefix"
            )

        if st.button("💾 Сохранить настройки префиксов",
                     use_container_width=True,
                     key="save_prefix_settings"):
            self.vm.update_prefix('prop', prop_prefix, user="user")
            self.vm.update_prefix('system', system_prefix, user="user")
            self.vm.update_prefix('fragment', fragment_prefix, user="user")
            st.success("Настройки префиксов сохранены!")

    def _display_export_interface(self):
        """Интерфейс экспорта данных"""
        st.subheader("📤 Экспорт данных")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Экспорт трансформаций в CSV", use_container_width=True):
                self._export_transformations_csv()

        with col2:
            if st.button("📋 Экспорт фрагментов в Excel", use_container_width=True):
                self._export_fragments_excel()

        st.divider()

        # Экспорт полного отчета
        if st.button("📁 Экспорт полного отчета", type="primary", use_container_width=True):
            self._export_complete_report()

    def _export_transformations_csv(self):
        """Экспортирует трансформации в CSV"""
        if not self.registry.transformations:
            st.warning("Нет данных для экспорта")
            return

        df = self.registry.to_detailed_dataframe()
        csv = df.to_csv(index=False, encoding='utf-8-sig')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"transformations_{self.category}_{timestamp}.csv"

        st.download_button(
            label="📥 Скачать CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )

    def _export_fragments_excel(self):
        """Экспортирует фрагменты в Excel"""
        try:
            # Создаем директорию для экспорта
            export_dir = Path("exports/phase6")
            export_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.category}_fragments_{timestamp}.xlsx"
            export_path = export_dir / filename

            with pd.ExcelWriter(export_path, engine='openpyxl') as writer:
                # Лист с фрагментами
                fragments_table = self.fragment_manager.get_fragments_table()
                if fragments_table:
                    fragments_df = pd.DataFrame(fragments_table)
                    fragments_df.to_excel(writer, sheet_name='Фрагменты', index=False)

                # Лист с блоками
                blocks_data = []
                for block in self.fragment_manager.fragments:
                    blocks_data.append({
                        'ID': block.id,
                        'Фрагмент': block.fragment_name,
                        'Тип': block.block_type,
                        'Характеристика': block.characteristic_name,
                        'Значение': block.characteristic_value,
                        'Исходный текст': block.original_text,
                        'Обработанный текст': block.processed_text,
                        'Ошибки': '; '.join(block.errors) if block.errors else '',
                        'Предупреждения': '; '.join(block.warnings) if block.warnings else '',
                        'Статус': block.status,
                        'Автоисправлен': 'Да' if block.auto_corrected else 'Нет',
                        'Добавленное значение': block.added_value or ''
                    })

                if blocks_data:
                    blocks_df = pd.DataFrame(blocks_data)
                    blocks_df.to_excel(writer, sheet_name='Блоки', index=False)

                # Лист с трансформациями
                if self.registry.transformations:
                    transformations_df = self.registry.to_dataframe()
                    transformations_df.to_excel(writer, sheet_name='Изменения', index=False)

            with open(export_path, 'rb') as f:
                excel_data = f.read()

            st.download_button(
                label="📥 Скачать Excel файл",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.success(f"✅ Файл создан: {filename}")

        except Exception as e:
            st.error(f"Ошибка при создании Excel файла: {str(e)}")

    def _export_complete_report(self):
        """Экспортирует полный отчет"""
        try:
            report_data = {
                "project_info": {
                    "category": self.category,
                    "processing_time": st.session_state.phase6_audit_data.get('processing_time'),
                    "total_blocks": st.session_state.phase6_audit_data.get('total_blocks', 0)
                },
                "statistics": st.session_state.phase6_audit_data.get('stats', {}),
                "fragments_count": len(self.fragment_manager.fragment_names),
                "transformations_count": len(self.registry.transformations)
            }

            report_json = json.dumps(report_data, ensure_ascii=False, indent=2, default=str)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"phase6_complete_report_{self.category}_{timestamp}.json"

            st.download_button(
                label="📥 Скачать полный отчет (JSON)",
                data=report_json,
                file_name=filename,
                mime="application/json"
            )

        except Exception as e:
            st.error(f"Ошибка при создании отчета: {str(e)}")

    def _export_problems_report(self, blocks: List[FragmentBlock]):
        """Экспортирует отчет о проблемах"""
        report_data = []

        for block in blocks:
            report_data.append({
                'ID': block.id,
                'Фрагмент': block.fragment_name,
                'Тип': block.block_type,
                'Характеристика': block.characteristic_name,
                'Значение': block.characteristic_value,
                'Ошибки': '; '.join(block.errors) if block.errors else '',
                'Предупреждения': '; '.join(block.warnings) if block.warnings else '',
                'Статус': block.status,
                'Текст': block.original_text[:200] + "..." if len(block.original_text) > 200 else block.original_text
            })

        df = pd.DataFrame(report_data)
        csv = df.to_csv(index=False, encoding='utf-8-sig')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"problems_report_{self.category}_{timestamp}.csv"

        st.download_button(
            label="📥 Скачать отчет в CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )


# ====================== ГЛАВНАЯ ФУНКЦИЯ ======================

def main():
    """Основная функция фазы 6 с полной системой аудита"""

    if 'app_data' not in st.session_state:
        st.error("❌ Нет данных приложения")
        st.info("Вернитесь к фазе 1 для создания проекта")

        if st.button("← Вернуться к фазе 1", use_container_width=True):
            st.session_state.current_phase = 1
            st.rerun()
        return

    app_data = st.session_state.app_data

    if 'phase5' not in app_data or not app_data['phase5']:
        st.error("❌ Нет данных из фазы 5")
        st.info("""
        Для работы фазы 6 необходимо:
        1. Завершить фазу 5
        2. Сохранить данные для фазы 6
        """)

        if st.button("← Вернуться к фазе 5", use_container_width=True):
            st.session_state.current_phase = 5
            st.rerun()
        return

    phase5_data = app_data['phase5']

    if not phase5_data.get('phase_completed', False):
        st.warning("⚠️ Фаза 5 не завершена полностью")
        st.info("Вернитесь в фазу 5 и завершите генерацию текстов")

        if st.button("← Вернуться к фазе 5", use_container_width=True):
            st.session_state.current_phase = 5
            st.rerun()
        return

    st.write(f"**Текущая фаза:** 6 - Подготовка к загрузке на сайт с полным аудитом")

    if 'statistics' in phase5_data:
        stats = phase5_data['statistics']
        success_count = stats.get('success', 0)
        st.success(f"✅ Данные из фазы 5 готовы")
        st.write(f"**Успешно сгенерировано:** {success_count} текстов")

    input_data = {
        'phase5_data': phase5_data,
        'phase1_data': app_data.get('phase1', {}),
        'phase2_data': app_data.get('phase2', {}),
        'category': app_data.get('category', ''),
        'project_name': app_data.get('project_name', '')
    }

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

    # Инициализация процессора с аудитом
    processor = Phase6EnhancedProcessorWithAudit(app_state, input_data)

    # Отображение основного интерфейса
    processor.display_main_interface()


if __name__ == "__main__":
    main()