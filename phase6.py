import streamlit as st
import re
import json
from datetime import datetime
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import uuid
import time
from enum import Enum
from io import BytesIO

# ====================== ОСНОВНЫЕ СТРУКТУРЫ ДАННЫХ ======================

class TransformationType(Enum):
    VARIABLE_REPLACE = "variable_replace"
    UNIT_REMOVED = "unit_removed"
    SPECIAL_SYMBOL_REMOVED = "special_symbol_removed"
    AUTO_INSERT = "auto_insert"
    WARNING = "warning"
    ERROR = "error"
    MANUAL_CORRECTION = "manual_correction"
    HTML_GENERATION = "html_generation"


class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class TextTransformation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    block_id: str = ""
    fragment_name: str = ""
    transformation_type: TransformationType = TransformationType.MANUAL_CORRECTION
    original: str = ""
    result: str = ""
    start: int = -1
    end: int = -1
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    severity: SeverityLevel = SeverityLevel.INFO
    user: str = "system"

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'block_id': self.block_id,
            'fragment_name': self.fragment_name,
            'transformation_type': self.transformation_type.value,
            'original': self.original,
            'result': self.result,
            'start': self.start,
            'end': self.end,
            'meta': self.meta,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'user': self.user
        }


class TransformationRegistry:
    def __init__(self):
        self.transformations: List[TextTransformation] = []
        self._block_index: Dict[str, List[TextTransformation]] = defaultdict(list)
        self._fragment_index: Dict[str, List[TextTransformation]] = defaultdict(list)

    def add(self, transformation: TextTransformation):
        self.transformations.append(transformation)
        self._block_index[transformation.block_id].append(transformation)
        self._fragment_index[transformation.fragment_name].append(transformation)

    def get_by_block_id(self, block_id: str) -> List[TextTransformation]:
        return self._block_index.get(block_id, [])

    def get_by_fragment(self, fragment_name: str) -> List[TextTransformation]:
        return self._fragment_index.get(fragment_name, [])

    def get_errors(self) -> List[TextTransformation]:
        return [t for t in self.transformations if t.severity == SeverityLevel.ERROR]

    def get_warnings(self) -> List[TextTransformation]:
        return [t for t in self.transformations if t.severity == SeverityLevel.WARNING]

    def clear(self):
        self.transformations.clear()
        self._block_index.clear()
        self._fragment_index.clear()


class VariableManager:
    def __init__(self):
        self.prefixes = {"prop": "prop", "system": "system", "fragment": "fragment"}

        self.system_vars = {
            "город": {
                "variants": ["{system город}", "{system городе}", "{system по_городу}"],
                "description": "Название города с вариантами падежей"
            },
            "название товара": {
                "variants": ["{system название_товара}"],
                "description": "Название товара"
            },
            "цена": {
                "variants": ["{system цена_товара}, руб."],
                "description": "Цена товара"
            },
            "единица измерения": {
                "variants": ["{system количество}"],
                "description": "Единица измерения"
            },
            "телефон": {
                "variants": ["8 495 969-51-08"],
                "description": "Телефон компании"
            },
            "email": {
                "variants": ["msk@steelborg.ru"],
                "description": "Email компании"
            },
            "компания": {
                "variants": ["Steelborg"],
                "description": "Название компании"
            },
            "категория РП": {
                "variants": ["{system название_категории_РП}"],
                "description": "Категория в родительном падеже"
            },
            "категория ВП": {
                "variants": ["{system название_категории_ВП}"],
                "description": "Категория в винительном падеже"
            },
            "категория ИП": {
                "variants": ["{system название_категории}"],
                "description": "Категория в именительном падеже"
            },
            "сайт": {
                "variants": ["steelborg.ru"],
                "description": "Сайт компании"
            },
            "адрес": {
                "variants": ["г. Москва, ул. Примерная, д. 1"],
                "description": "Адрес компании"
            },
            "рабочие часы": {
                "variants": ["пн-пт с 9:00 до 18:00"],
                "description": "Рабочие часы"
            }
        }

    def get_variable_suggestions(self) -> List[Dict]:
        suggestions = []
        for name, data in self.system_vars.items():
            for variant in data.get("variants", []):
                suggestions.append({
                    "type": "system",
                    "name": name,
                    "value": variant,
                    "description": data.get("description", f"Системная переменная: {name}")
                })
        suggestions.extend([
            {"type": "prop", "name": "prop", "value": "{prop }", "description": "Свойство характеристики"},
            {"type": "fragment", "name": "fragment", "value": "{fragment }", "description": "Фрагмент текста"}
        ])
        return suggestions

    def format_variable(self, var_type: str, var_name: str) -> str:
        if var_type == "system":
            return f"{{{self.prefixes['system']} {var_name}}}"
        elif var_type == "prop":
            return f"{{{self.prefixes['prop']} {var_name}}}"
        elif var_type == "fragment":
            return f"{{{self.prefixes['fragment']} {var_name}}}"
        return var_name


@dataclass
class FragmentBlock:
    id: str
    fragment_name: str
    original_text: str
    processed_text: str
    block_type: str
    html_text: str = ""
    characteristic_name: Optional[str] = None
    characteristic_value: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: str = "pending"
    manual_correction: Optional[str] = None
    auto_corrected: bool = False
    added_value: Optional[str] = None
    special_symbols: List[Tuple[str, int, int]] = field(default_factory=list)
    last_modified: datetime = field(default_factory=datetime.now)
    units_removed: List[str] = field(default_factory=list)
    symbols_removed: List[str] = field(default_factory=list)
    html_generated: bool = False

    def to_dict(self):
        return {
            'id': self.id,
            'fragment_name': self.fragment_name,
            'original_text': self.original_text,
            'processed_text': self.processed_text,
            'html_text': self.html_text,
            'block_type': self.block_type,
            'characteristic_name': self.characteristic_name,
            'characteristic_value': self.characteristic_value,
            'errors': self.errors,
            'warnings': self.warnings,
            'status': self.status,
            'manual_correction': self.manual_correction,
            'auto_corrected': self.auto_corrected,
            'added_value': self.added_value,
            'special_symbols': self.special_symbols,
            'last_modified': self.last_modified.isoformat()
        }


class FragmentManager:
    def __init__(self, category: str):
        self.category = category
        self.fragments: List[FragmentBlock] = []
        self.fragment_names: set = set()
        self.template_order: List[str] = []
        self.fragment_properties: Dict[str, List[Dict]] = defaultdict(list)

    def add_block(self, block_data: Dict) -> FragmentBlock:
        fragment_block = FragmentBlock(
            id=block_data.get('id', str(uuid.uuid4())),
            fragment_name=block_data['fragment_name'],
            original_text=block_data.get('original_text', ''),
            processed_text=block_data.get('processed_text', ''),
            block_type=block_data.get('block_type', 'unknown'),
            html_text=block_data.get('html_text', ''),
            characteristic_name=block_data.get('characteristic_name'),
            characteristic_value=block_data.get('characteristic_value'),
            errors=block_data.get('errors', []),
            warnings=block_data.get('warnings', []),
            status=block_data.get('status', 'pending'),
            auto_corrected=block_data.get('auto_corrected', False),
            added_value=block_data.get('added_value'),
            special_symbols=block_data.get('special_symbols', [])
        )
        self.fragments.append(fragment_block)
        self.fragment_names.add(fragment_block.fragment_name)
        self._extract_properties(fragment_block)
        return fragment_block

    def _extract_properties(self, fragment: FragmentBlock):
        if fragment.block_type == 'regular' and fragment.characteristic_name:
            self.fragment_properties[fragment.fragment_name].append({
                'characteristic': fragment.characteristic_name,
                'value': None,
                'is_unique': False
            })
        elif fragment.block_type == 'unique' and fragment.characteristic_name and fragment.characteristic_value:
            self.fragment_properties[fragment.fragment_name].append({
                'characteristic': fragment.characteristic_name,
                'value': fragment.characteristic_value,
                'is_unique': True
            })

    def rename_fragment(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.fragment_names:
            return False
        for fragment in self.fragments:
            if fragment.fragment_name == old_name:
                fragment.fragment_name = new_name
        self.fragment_names.remove(old_name)
        self.fragment_names.add(new_name)
        if old_name in self.fragment_properties:
            self.fragment_properties[new_name] = self.fragment_properties.pop(old_name)
        if old_name in self.template_order:
            self.template_order[self.template_order.index(old_name)] = new_name
        return True

    def get_fragment_blocks(self, fragment_name: str) -> List[FragmentBlock]:
        return [f for f in self.fragments if f.fragment_name == fragment_name]

    def get_all_properties(self) -> List[Dict]:
        props = []
        for frag_name in sorted(self.fragment_names):
            for prop in self.fragment_properties.get(frag_name, []):
                props.append({
                    'fragment_name': frag_name,
                    'characteristic': prop['characteristic'],
                    'value': prop['value'],
                    'is_unique': prop['is_unique']
                })
        return props

    def generate_template(self, category_code: str = None) -> Dict:
        if category_code is None:
            category_code = self.category
        if not self.template_order:
            self.template_order = sorted(self.fragment_names)
        fragment_vars = {name: f"{{fragment {name}}}" for name in self.fragment_names}
        template_parts = [fragment_vars[name] for name in self.template_order if name in fragment_vars]
        return {
            'category_code': category_code,
            'template': " ".join(template_parts),
            'fragment_variables': fragment_vars,
            'order': self.template_order
        }

    def update_block(self, block_id: str, updates: Dict) -> bool:
        for fragment in self.fragments:
            if fragment.id == block_id:
                for key, value in updates.items():
                    if hasattr(fragment, key):
                        setattr(fragment, key, value)
                fragment.last_modified = datetime.now()
                return True
        return False

    def delete_block(self, block_id: str) -> bool:
        for i, fragment in enumerate(self.fragments):
            if fragment.id == block_id:
                del self.fragments[i]
                if not any(f.fragment_name == fragment.fragment_name for f in self.fragments):
                    self.fragment_names.discard(fragment.fragment_name)
                return True
        return False


class EnhancedTextProcessor:
    def __init__(self, variable_manager: VariableManager):
        self.vm = variable_manager
        self.pattern = re.compile(r'\[([^\]]+)\]')
        self.special_symbols_pattern = re.compile(r'[<>{}|\\^`~!@#$%^&*()_\+=\[\]\'":;?/]')
        self.units_to_remove = [
            "мм", "метр", "м", "см", "дм", "км", "миллиметр", "сантиметр", "дециметр", "километр",
            "кг", "г", "мг", "тонна", "т", "грамм", "миллиграмм", "килограмм",
            "л", "мл", "литр", "миллилитр", "шт", "штук", "штука", "штуки",
            "кг/м", "г/см³", "г/см3", "кг/м³", "кг/м3", "°C", "°F", "град", "градус", "градусов"
        ]
        self.instruction_keywords = [
            "инструкция:", "промпт:", "введите:", "создайте:", "напишите:",
            "instruction:", "prompt:", "write:", "create:", "generate:",
            "опишите:", "сформулируйте:", "составьте:", "подготовьте:"
        ]

    def check_regular_brackets(self, text: str, expected_value: str) -> List[str]:
        """
        Проверяет, что в тексте есть подстроки вида [expected_value].
        Возвращает список ошибок.
        """
        if not expected_value:
            return []  # нет ожидаемого значения – не проверяем
        pattern = r'\[' + re.escape(expected_value) + r'\]'
        if re.search(pattern, text):
            return []
        # Если не нашли точное совпадение, проверяем наличие любых скобок
        if self.pattern.search(text):
            return [f"В regular-блоке ожидается значение [{expected_value}], но найдены другие скобки"]
        else:
            return [f"В regular-блоке отсутствует значение [{expected_value}]"]
    # --------------------------------------------------------------
    #  ЗАМЕНА ПЕРЕМЕННЫХ (ТОЛЬКО ЗАМЕНА, БЕЗ АВТОДОБАВЛЕНИЯ)
    # --------------------------------------------------------------
    def replace_variables(self, text: str, block_type: str,
                         char_name: Optional[str] = None,
                         char_value: Optional[str] = None) -> Dict:
        """
        Заменяет выражения [variable] на соответствующие переменные.
        НЕ добавляет автоматически новые скобки.
        Для non-regular блоков, если переменная не найдена, заменяет на {system var_name} и добавляет ошибку.
        """
        errors = []
        warnings = []
        special_symbols = self._find_special_symbols(text)

        matches = list(self.pattern.finditer(text))
        processed_text = text
        offset = 0
        replacements = []

        for match in matches:
            var_name = match.group(1).strip()
            start, end = match.span()

            if block_type == 'regular':
                # Для regular блока заменяем на {prop ...}
                replacement = f"{{prop {char_name if char_name else var_name}}}"
            else:
                # Для non-regular пытаемся найти системную переменную
                var_lower = var_name.lower()
                found = False
                replacement = None
                for sys_var, data in self.vm.system_vars.items():
                    if sys_var.lower() == var_lower:
                        replacement = data['variants'][0]
                        found = True
                        break
                if not found:
                    replacement = match.group()  # оставляем как есть, например "[var_name]"
                    errors.append(f"Неизвестная переменная '{var_name}' в non-regular блоке")

            new_start = start + offset
            new_end = end + offset
            processed_text = processed_text[:new_start] + replacement + processed_text[new_end:]
            offset += len(replacement) - (end - start)

            replacements.append({
                'original': match.group(),
                'replacement': replacement,
                'position': (start, end)
            })

        return {
            'processed_text': processed_text,
            'replacements': replacements,
            'errors': errors,
            'warnings': warnings,
            'special_symbols': special_symbols
        }

    # --------------------------------------------------------------
    #  АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ СКОБОК (ТОЛЬКО ДЛЯ REGULAR)
    # --------------------------------------------------------------
    # --------------------------------------------------------------
    #  АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ СКОБОК (ТОЛЬКО ДЛЯ REGULAR)
    # --------------------------------------------------------------
    def auto_insert_bracket(self, text: str, char_value: str) -> Tuple[str, bool, Optional[str]]:
        """
        Умное добавление скобок для regular-блоков:
        1. Ищет в тексте вхождение characteristic_value (без учёта регистра) и оборачивает первое найденное в квадратные скобки.
        2. Если значение не найдено, добавляет [char_value] в конец текста.
        Возвращает (новый_текст, был_ли_добавлен/изменён, найденное_значение_или_None).
        """
        if not char_value:
            return text, False, None

        # Если уже есть скобки — ничего не делаем
        if self.pattern.search(text):
            return text, False, None

        # Экранируем спецсимволы в значении для регулярного выражения
        escaped_value = re.escape(char_value)
        # Ищем полное совпадение слова/фразы (границы слов)
        pattern = r'\b' + escaped_value + r'\b'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            # Нашли значение, оборачиваем его в скобки
            start, end = match.span()
            # Важно: не заменять, если уже внутри скобок? Но мы уже проверили, что скобок нет.
            new_text = text[:start] + '[' + text[start:end] + ']' + text[end:]
            return new_text, True, text[start:end]
        else:
            # Не нашли — добавляем в конец
            if text and not text.endswith(' '):
                text += ' '
            added_text = f"[{char_value}]"
            new_text = text + added_text
            return new_text, True, char_value

    # --------------------------------------------------------------
    #  ПРОВЕРКА ОТСУТСТВИЯ СКОБОК (ДЛЯ REGULAR)
    # --------------------------------------------------------------


    # --------------------------------------------------------------
    #  УДАЛЕНИЕ ЕДИНИЦ
    # --------------------------------------------------------------
    def remove_units(self, text: str, units_list: List[str]) -> Tuple[str, List[str]]:
        removed = []
        cleaned = text
        for unit in units_list:
            pattern = r'\b' + re.escape(unit) + r'\b'
            for m in reversed(list(re.finditer(pattern, cleaned, re.IGNORECASE))):
                cleaned = cleaned[:m.start()] + cleaned[m.end():]
                removed.append(unit)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned, removed

    # --------------------------------------------------------------
    #  УДАЛЕНИЕ СПЕЦСИМВОЛОВ
    # --------------------------------------------------------------
    def remove_special_symbols(self, text: str, symbols_to_remove: List[str]) -> Tuple[str, List[str], List[Tuple[str, int, int]]]:
        removed = []
        cleaned = text
        for symbol in symbols_to_remove:
            escaped = re.escape(symbol)
            pattern = escaped
            for m in reversed(list(re.finditer(pattern, cleaned))):
                cleaned = cleaned[:m.start()] + cleaned[m.end():]
                removed.append(symbol)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        new_special_symbols = self._find_special_symbols(cleaned)
        return cleaned, removed, new_special_symbols

    # --------------------------------------------------------------
    #  ПОИСК СПЕЦСИМВОЛОВ
    # --------------------------------------------------------------
    def _find_special_symbols(self, text: str) -> List[Tuple[str, int, int]]:
        specials = []
        for match in self.special_symbols_pattern.finditer(text):
            symbol = match.group()
            if symbol not in ['[', ']', ',', '.', '-', '_', ' ', '\t', '\n']:
                specials.append((symbol, match.start(), match.end()))
        return specials

    # --------------------------------------------------------------
    #  ГЕНЕРАЦИЯ HTML
    # --------------------------------------------------------------
    def convert_to_html(self, text: str) -> str:
        if not text:
            return ""
        lines = text.split('\n')
        html_lines = []
        in_list = False
        for line in lines:
            line = line.rstrip()
            if not line:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                continue
            if line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('- ') or line.startswith('* ') or re.match(r'^\d+\.', line):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                content = re.sub(r'^[-*\d.]+\s*', '', line)
                html_lines.append(f'<li>{content}</li>')
            else:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
                html_lines.append(f'<p>{line}</p>')
        if in_list:
            html_lines.append('</ul>')
        return '\n'.join(html_lines)

    # --------------------------------------------------------------
    #  УПРАВЛЕНИЕ СПИСКОМ ЕДИНИЦ
    # --------------------------------------------------------------
    def add_unit_to_remove(self, unit: str):
        if unit and unit not in self.units_to_remove:
            self.units_to_remove.append(unit)

    def remove_unit_from_list(self, unit: str):
        if unit in self.units_to_remove:
            self.units_to_remove.remove(unit)

    def find_units_in_text(self, text: str) -> List[str]:
        found = set()
        text_lower = text.lower()
        # Окончания для существительных (мужской род, множественное число и т.п.)
        endings = ['', 'а', 'у', 'ом', 'е', 'ы', 'ов', 'ам', 'ами', 'ах']
        for unit in self.units_to_remove:
            # Если единица короткая (<=2 символов) или содержит не только буквы, ищем точно
            if len(unit) <= 2 or not re.match(r'^[а-яё]+$', unit, re.IGNORECASE):
                pattern = r'\b' + re.escape(unit.lower()) + r'\b'
            else:
                # Строим регулярку: основа + возможные окончания
                base = re.escape(unit.lower())
                endings_pattern = '(?:' + '|'.join(re.escape(e) for e in endings) + ')'
                pattern = r'\b' + base + endings_pattern + r'\b'
            if re.search(pattern, text_lower):
                found.add(unit)
        return sorted(found)


class ExportManager:
    @staticmethod
    def export_to_excel(fragment_manager: FragmentManager, template_data: Dict = None,
                        use_html: bool = False) -> BytesIO:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if template_data:
                pd.DataFrame({
                    'Код категории': [template_data['category_code']],
                    'Шаблон': [template_data['template']]
                }).to_excel(writer, sheet_name='Шаблоны', index=False)

            pd.DataFrame({
                'Название фрагмента': sorted(fragment_manager.fragment_names)
            }).to_excel(writer, sheet_name='Фрагменты', index=False)

            props = fragment_manager.get_all_properties()
            if props:
                pd.DataFrame(props).to_excel(writer, sheet_name='Свойства фрагментов', index=False)
            else:
                pd.DataFrame({'Сообщение': ['Нет данных']}).to_excel(writer, sheet_name='Свойства фрагментов',
                                                                     index=False)

            elements = []
            for f in fragment_manager.fragments:
                elements.append({
                    'Название блока': f.fragment_name,
                    'Текстовый фрагмент': f.html_text if use_html else f.processed_text,
                    'HTML версия': f.html_text,
                    'Обычный текст': f.processed_text,
                    'Тип': f.block_type,
                    'Характеристика': f.characteristic_name or '',
                    'Значение': f.characteristic_value or '',
                    'Статус': f.status,
                    'Ошибки': '; '.join(f.errors),
                    'Предупреждения': '; '.join(f.warnings)
                })
            pd.DataFrame(elements).to_excel(writer, sheet_name='Элементы фрагментов', index=False)
        output.seek(0)
        return output

    @staticmethod
    def export_verification_json(fragment_manager: FragmentManager, phase5_data: Dict) -> str:
        fm = fragment_manager
        prompts = phase5_data.get('prompts', {})
        results = phase5_data.get('results', [])
        original_by_id = {r.get('prompt_id'): r.get('edited_text', '') for r in results}

        blocks_info = []
        for block in fm.fragments:
            info = {
                'block_id': block.id,
                'fragment_name': block.fragment_name,
                'block_type': block.block_type,
                'original_text': original_by_id.get(block.id, block.original_text),
                'processed_text': block.processed_text,
                'html_text': block.html_text,
                'characteristic_name': block.characteristic_name,
                'characteristic_value': block.characteristic_value,
                'errors': block.errors,
                'warnings': block.warnings,
                'special_symbols': block.special_symbols,
                'status': block.status,
                'auto_corrected': block.auto_corrected,
                'added_value': block.added_value,
                'prompt_id': block.id,
            }
            prompt_text = prompts.get(block.id)
            if prompt_text:
                info['prompt_text'] = prompt_text
            blocks_info.append(info)

        export_data = {
            'timestamp': datetime.now().isoformat(),
            'category': fm.category,
            'blocks': blocks_info,
            'phase5_meta': {
                'total_results': len(results),
                'prompts_count': len(prompts)
            }
        }
        return json.dumps(export_data, ensure_ascii=False, indent=2, default=str)

    @staticmethod
    def export_verification_excel(fragment_manager: FragmentManager, phase5_data: Dict) -> BytesIO:
        fm = fragment_manager
        prompts = phase5_data.get('prompts', {})
        results = phase5_data.get('results', [])
        original_by_id = {r.get('prompt_id'): r.get('edited_text', '') for r in results}

        data = []
        for block in fm.fragments:
            data.append({
                'ID блока': block.id,
                'Фрагмент': block.fragment_name,
                'Тип': block.block_type,
                'Исходный текст (фаза 5)': original_by_id.get(block.id, block.original_text),
                'Обработанный текст': block.processed_text,
                'HTML': block.html_text,
                'Характеристика': block.characteristic_name,
                'Значение': block.characteristic_value,
                'Ошибки': '; '.join(block.errors),
                'Предупреждения': '; '.join(block.warnings),
                'Статус': block.status,
                'Автоисправлено': block.auto_corrected,
                'Добавленное значение': block.added_value,
                'Текст промпта': prompts.get(block.id, ''),
            })

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(data).to_excel(writer, sheet_name='Блоки', index=False)
            # Добавим лист с промптами, если есть
            if prompts:
                prompts_df = pd.DataFrame([
                    {'prompt_id': pid, 'prompt_text': ptext}
                    for pid, ptext in prompts.items()
                ])
                prompts_df.to_excel(writer, sheet_name='Промпты', index=False)
        output.seek(0)
        return output


class Phase6Interface:
    def __init__(self):
        self.vm = VariableManager()
        self.text_processor = EnhancedTextProcessor(self.vm)
        self._init_session_state()
        self._init_ui_state()

    def _init_session_state(self):
        if 'fragment_manager' not in st.session_state:
            st.session_state.fragment_manager = FragmentManager("Без_категории")
        if 'transformation_registry' not in st.session_state:
            st.session_state.transformation_registry = TransformationRegistry()
        if 'units_manager' not in st.session_state:
            st.session_state.units_manager = {
                'units': self.text_processor.units_to_remove.copy(),
                'custom_units': []
            }
        if 'found_units' not in st.session_state:
            st.session_state.found_units = []
        if 'found_special_symbols' not in st.session_state:
            st.session_state.found_special_symbols = []

    def _init_ui_state(self):
        default_ui_state = {
            'selected_block_id': None,
            # 'editing_mode': False,            # удалить
            'active_tab': 'fragments',
            'show_html': False,
            # 'selected_issues': set(),         # можно удалить
            'fragments_page': 1,
            'fragments_per_page': 20,
            'fragment_search': '',
            'fragment_group_by': 'none',
            'insert_position_mode': 'end',
            'insert_position_word_index': 0,
            'selected_units_global': [],
            'selected_symbols_global': [],
            'compact_view': True,  # оставляем
            'filtered_block_ids': [],  # новый список id после фильтрации
            'current_block_index': 0, # индекс в этом списке
            'editing_block_id': None
        }
        if 'ui_state' not in st.session_state:
            st.session_state.ui_state = default_ui_state.copy()
        else:
            for key, value in default_ui_state.items():
                if key not in st.session_state.ui_state:
                    st.session_state.ui_state[key] = value

    def _migrate_fragments(self):
        fm = st.session_state.fragment_manager
        for frag in fm.fragments:
            if not hasattr(frag, 'special_symbols'):
                frag.special_symbols = []
            if not hasattr(frag, 'html_text'):
                frag.html_text = ""
            if not hasattr(frag, 'auto_corrected'):
                frag.auto_corrected = False
            if not hasattr(frag, 'added_value'):
                frag.added_value = None
            if not hasattr(frag, 'last_modified'):
                frag.last_modified = datetime.now()
            if not hasattr(frag, 'html_generated'):
                frag.html_generated = False
            if not hasattr(frag, 'units_removed'):
                frag.units_removed = []
            if not hasattr(frag, 'symbols_removed'):
                frag.symbols_removed = []
            if isinstance(frag.last_modified, str):
                try:
                    frag.last_modified = datetime.fromisoformat(frag.last_modified)
                except:
                    frag.last_modified = datetime.now()

    # ------------------------------------------------------------------
    #                     ЗАГРУЗКА ДАННЫХ (БЕЗ ОБРАБОТКИ)
    # ------------------------------------------------------------------
    def _load_data(self) -> bool:
        try:
            app_data = st.session_state.app_data
            if 'phase5' not in app_data:
                st.error("❌ Нет данных из фазы 5")
                return False

            phase5_data = app_data['phase5']
            results = phase5_data.get('results', [])
            if not results:
                st.warning("⚠️ Нет результатов для обработки")
                return False

            if st.session_state.fragment_manager.fragments:
                return True

            fm = st.session_state.fragment_manager

            for result in results:
                if result.get('status') != 'success':
                    continue

                frag_name = self._generate_fragment_name(result)
                original = result.get('edited_text', '')

                block_data = {
                    'id': result.get('prompt_id', str(uuid.uuid4())),
                    'fragment_name': frag_name,
                    'original_text': original,
                    'processed_text': original,
                    'html_text': '',
                    'block_type': result.get('type', 'unknown'),
                    'characteristic_name': result.get('characteristic_name'),
                    'characteristic_value': result.get('characteristic_value'),
                    'errors': [],
                    'warnings': [],
                    'special_symbols': [],
                    'status': 'pending',
                    'auto_corrected': False,
                    'added_value': None
                }
                fm.add_block(block_data)

            return True
        except Exception as e:
            st.error(f"Ошибка загрузки: {str(e)}")
            return False

    def _generate_fragment_name(self, result: Dict) -> str:
        bt = result.get('type', '')
        cn = result.get('characteristic_name', '')
        cv = result.get('characteristic_value', '')
        cat = st.session_state.app_data.get('category', 'Без_категории')

        if bt == 'regular' and cn:
            return f"{cat}_{cn}"
        elif bt == 'unique' and cn and cv:
            clean = re.sub(r'[^\w\s-]', '', cv.lower())
            clean = re.sub(r'[\s-]+', '_', clean)[:30].strip('_')
            return f"{cat}_{cn}_{clean}"
        else:
            bn = result.get('block_name', '')
            if bn:
                clean = re.sub(r'[^\w\s-]', '', bn.lower())
                clean = re.sub(r'[\s-]+', '_', clean)[:30].strip('_')
                return f"{cat}_{clean}"
            return f"{cat}_блок_{uuid.uuid4().hex[:8]}"

    # ------------------------------------------------------------------
    #                     УПРАВЛЕНИЕ ЕДИНИЦАМИ
    # ------------------------------------------------------------------
    def _scan_units_in_texts(self) -> List[str]:
        fm = st.session_state.fragment_manager
        all_units = set()
        for frag in fm.fragments:
            units_in_text = self.text_processor.find_units_in_text(frag.original_text)
            all_units.update(units_in_text)
        return sorted(all_units)



    # ------------------------------------------------------------------
    #                     УПРАВЛЕНИЕ СПЕЦСИМВОЛАМИ
    # ------------------------------------------------------------------
    def _scan_special_symbols_in_texts(self) -> List[str]:
        fm = st.session_state.fragment_manager
        all_symbols = set()
        for frag in fm.fragments:
            sym_list = self.text_processor._find_special_symbols(frag.original_text)
            for sym, _, _ in sym_list:
                all_symbols.add(sym)
        return sorted(all_symbols)

    def _manage_units_and_symbols(self):
        with st.sidebar.expander("⚙️ Единицы и спецсимволы", expanded=False):
            st.write("### 📏 Единицы измерения, найденные в текстах")
            found_units = st.session_state.get('found_units', [])
            if found_units:
                selected_units = st.multiselect(
                    "Выберите единицы для удаления:",
                    found_units,
                    default=st.session_state.ui_state.get('selected_units_global', []),
                    key="selected_units_global_widget"
                )
                st.session_state.ui_state['selected_units_global'] = selected_units
            else:
                st.info("В текстах не найдено стандартных единиц измерения.")
                st.session_state.ui_state['selected_units_global'] = []

            st.divider()
            new_unit = st.text_input("Добавить свою единицу:")
            if st.button("➕ Добавить единицу", use_container_width=True):
                if new_unit and new_unit not in st.session_state.units_manager['units']:
                    st.session_state.units_manager['units'].append(new_unit)
                    self.text_processor.add_unit_to_remove(new_unit)
                    st.session_state.found_units = self._scan_units_in_texts()
                    st.rerun()

            st.divider()
            st.write("### ⚡ Специальные символы, найденные в текстах")
            found_symbols = st.session_state.get('found_special_symbols', [])
            if found_symbols:
                selected_symbols = st.multiselect(
                    "Выберите символы для удаления:",
                    found_symbols,
                    default=st.session_state.ui_state.get('selected_symbols_global', []),
                    key="selected_symbols_global_widget"
                )
                st.session_state.ui_state['selected_symbols_global'] = selected_symbols
            else:
                st.info("Специальные символы не найдены.")
                st.session_state.ui_state['selected_symbols_global'] = []

            st.divider()
            if st.button("🗑️ Удалить выбранные единицы и символы из ВСЕХ блоков", use_container_width=True):
                units = st.session_state.ui_state.get('selected_units_global', [])
                symbols = st.session_state.ui_state.get('selected_symbols_global', [])
                if units:
                    self._apply_unit_removal(units_to_remove=units)
                if symbols:
                    self._apply_special_symbol_removal(symbols_to_remove=symbols)
                st.rerun()

    # ------------------------------------------------------------------
    #                     ОПЕРАЦИИ НАД БЛОКАМИ (ИНДИВИДУАЛЬНЫЕ И ОБЩИЕ)
    # ------------------------------------------------------------------
    def _apply_variable_replacement(self, block_id: str = None):
        """Замена переменных (только замена существующих скобок)."""
        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        blocks = [next((b for b in fm.fragments if b.id == block_id), None)] if block_id else fm.fragments
        blocks = [b for b in blocks if b is not None]

        all_replacements = []
        errors_occurred = False

        for block in blocks:
            result = self.text_processor.replace_variables(
                text=block.processed_text,
                block_type=block.block_type,
                char_name=block.characteristic_name,
                char_value=block.characteristic_value
            )

            old_text = block.processed_text
            block.processed_text = result['processed_text']
            block.special_symbols = result['special_symbols']
            # Добавляем новые ошибки
            for err in result['errors']:
                if err not in block.errors:
                    block.errors.append(err)
                    block.status = 'error'
                    trans = TextTransformation(
                        block_id=block.id,
                        fragment_name=block.fragment_name,
                        transformation_type=TransformationType.ERROR,
                        original="",
                        result="",
                        meta={'message': err},
                        severity=SeverityLevel.ERROR,
                        user="system"
                    )
                    registry.add(trans)
                    errors_occurred = True

            block.last_modified = datetime.now()

            for repl in result['replacements']:
                trans = TextTransformation(
                    block_id=block.id,
                    fragment_name=block.fragment_name,
                    transformation_type=TransformationType.VARIABLE_REPLACE,
                    original=repl['original'],
                    result=repl['replacement'],
                    start=repl['position'][0],
                    end=repl['position'][1],
                    severity=SeverityLevel.INFO,
                    user="user"
                )
                registry.add(trans)
                all_replacements.append({
                    'block': block.fragment_name,
                    'original': repl['original'],
                    'replacement': repl['replacement']
                })

        if all_replacements:
            st.success("✅ Переменные заменены")
            df = pd.DataFrame(all_replacements)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Нет замен для выполнения")

        if errors_occurred:
            st.error("❌ При замене возникли ошибки. Проверьте вкладку 'Проблемы'.")

    def _auto_insert_regular_blocks(self, block_id: str = None):
        """Автоматически оборачивает найденное значение в [] в regular-блоках без скобок."""
        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        blocks = [next((b for b in fm.fragments if b.id == block_id), None)] if block_id else fm.fragments
        blocks = [b for b in blocks if b is not None and b.block_type == 'regular']

        inserted = 0
        for block in blocks:
            if not block.characteristic_value:
                continue
            new_text, added, found_value = self.text_processor.auto_insert_bracket(
                block.processed_text, block.characteristic_value
            )
            if added:
                block.processed_text = new_text
                block.last_modified = datetime.now()
                block.auto_corrected = True
                block.added_value = found_value
                trans = TextTransformation(
                    block_id=block.id,
                    fragment_name=block.fragment_name,
                    transformation_type=TransformationType.AUTO_INSERT,
                    original="",
                    result=f"[{found_value}]",
                    meta={'value': found_value, 'method': 'wrap' if found_value != block.characteristic_value else 'append'},
                    severity=SeverityLevel.WARNING,
                    user="system"
                )
                registry.add(trans)
                inserted += 1

        if inserted:
            st.success(f"✅ Добавлены/обёрнуты значения в {inserted} regular-блоков")
        else:
            st.info("Нет regular-блоков, требующих добавления значения")

    def _apply_unit_removal(self, block_id: str = None, units_to_remove: List[str] = None):
        if not units_to_remove:
            st.warning("Не выбрано ни одной единицы для удаления.")
            return

        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        blocks = [next((b for b in fm.fragments if b.id == block_id), None)] if block_id else fm.fragments
        blocks = [b for b in blocks if b is not None]

        all_removed = []

        for block in blocks:
            cleaned, removed = self.text_processor.remove_units(block.processed_text, units_to_remove)
            if removed:
                block.processed_text = cleaned
                block.last_modified = datetime.now()
                trans = TextTransformation(
                    block_id=block.id,
                    fragment_name=block.fragment_name,
                    transformation_type=TransformationType.UNIT_REMOVED,
                    original="",
                    result="",
                    meta={'removed_units': list(set(removed))},
                    severity=SeverityLevel.INFO,
                    user="user"
                )
                registry.add(trans)
                all_removed.extend([(block.fragment_name, unit) for unit in set(removed)])
            if removed:
                block.units_removed = list(set(removed))
        if all_removed:
            st.success(f"✅ Удалены единицы из {len(set(b for b,_ in all_removed))} блоков")
            df = pd.DataFrame(all_removed, columns=["Фрагмент", "Единица"]).drop_duplicates()
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Единицы для удаления не найдены в текстах.")

    def _apply_special_symbol_removal(self, block_id: str = None, symbols_to_remove: List[str] = None):
        if not symbols_to_remove:
            st.warning("Не выбрано ни одного символа для удаления.")
            return

        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        blocks = [next((b for b in fm.fragments if b.id == block_id), None)] if block_id else fm.fragments
        blocks = [b for b in blocks if b is not None]

        all_removed = []

        for block in blocks:
            cleaned, removed, new_specials = self.text_processor.remove_special_symbols(
                block.processed_text, symbols_to_remove
            )
            if removed:
                block.processed_text = cleaned
                block.special_symbols = new_specials
                block.last_modified = datetime.now()
                trans = TextTransformation(
                    block_id=block.id,
                    fragment_name=block.fragment_name,
                    transformation_type=TransformationType.SPECIAL_SYMBOL_REMOVED,
                    original="",
                    result="",
                    meta={'removed_symbols': list(set(removed))},
                    severity=SeverityLevel.INFO,
                    user="user"
                )
                registry.add(trans)
                all_removed.extend([(block.fragment_name, sym) for sym in set(removed)])
            if removed:
                block.symbols_removed = list(set(removed))
        if all_removed:
            st.success(f"✅ Удалены спецсимволы из {len(set(b for b,_ in all_removed))} блоков")
            df = pd.DataFrame(all_removed, columns=["Фрагмент", "Символ"]).drop_duplicates()
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Выбранные символы не найдены в текстах.")

    def _apply_generate_html(self, block_id: str = None):
        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        blocks = [next((b for b in fm.fragments if b.id == block_id), None)] if block_id else fm.fragments
        blocks = [b for b in blocks if b is not None]

        generated = 0
        for block in blocks:
            html = self.text_processor.convert_to_html(block.processed_text)
            block.html_text = html
            block.last_modified = datetime.now()
            trans = TextTransformation(
                block_id=block.id,
                fragment_name=block.fragment_name,
                transformation_type=TransformationType.HTML_GENERATION,
                original="",
                result=html[:100] + "..." if len(html) > 100 else html,
                severity=SeverityLevel.INFO,
                user="user"
            )
            registry.add(trans)
            generated += 1
            block.html_generated = True

        st.success(f"🌐 HTML сгенерирован для {generated} блоков")

        if generated == 1 and block_id:
            st.markdown(blocks[0].html_text, unsafe_allow_html=True)

    def _check_all_errors(self):
        """Полная проверка ошибок во всех блоках (без автоматического исправления)."""
        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        errors_found = 0

        for block in fm.fragments:
            # 1. Проверка regular-блоков на отсутствие скобок
            if block.block_type == 'regular':
                missing = self.text_processor.check_regular_brackets(block.processed_text, block.block_type)
                if missing:
                    # Удаляем старые такие ошибки, добавляем новые
                    block.errors = [e for e in block.errors if "отсутствует значение в квадратных скобках" not in e]
                    block.errors.extend(missing)
                    block.status = 'error'
                    for err in missing:
                        trans = TextTransformation(
                            block_id=block.id,
                            fragment_name=block.fragment_name,
                            transformation_type=TransformationType.ERROR,
                            original="",
                            result="",
                            meta={'message': err},
                            severity=SeverityLevel.ERROR,
                            user="system"
                        )
                        registry.add(trans)
                    errors_found += len(missing)

            # 2. Проверка non-regular блоков: все скобки должны соответствовать системным переменным
            elif block.block_type != 'regular':
                matches = self.text_processor.pattern.finditer(block.processed_text)
                for match in matches:
                    var_name = match.group(1).strip()
                    var_lower = var_name.lower()
                    # Проверяем, есть ли системная переменная
                    found = any(sys_var.lower() == var_lower for sys_var in self.vm.system_vars.keys())
                    if not found:
                        err_msg = f"Неизвестная переменная '{var_name}' в non-regular блоке"
                        if err_msg not in block.errors:
                            block.errors.append(err_msg)
                            block.status = 'error'
                            trans = TextTransformation(
                                block_id=block.id,
                                fragment_name=block.fragment_name,
                                transformation_type=TransformationType.ERROR,
                                original="",
                                result="",
                                meta={'message': err_msg},
                                severity=SeverityLevel.ERROR,
                                user="system"
                            )
                            registry.add(trans)
                        errors_found += 1

            # Обновляем специальные символы (для информации)
            block.special_symbols = self.text_processor._find_special_symbols(block.processed_text)

        if errors_found:
            st.error(f"❌ Найдено {errors_found} ошибок. Проверьте вкладку 'Проблемы'.")
        else:
            st.success("✅ Ошибок не найдено")

    # ------------------------------------------------------------------
    #                     СБРОС СОСТОЯНИЯ
    # ------------------------------------------------------------------
    def _reset_state(self):
        """Полный сброс состояния фазы 6 (очистка session_state)."""
        keys_to_clear = [
            'fragment_manager',
            'transformation_registry',
            'units_manager',
            'found_units',
            'found_special_symbols',
            'ui_state'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.success("✅ Состояние фазы 6 сброшено. Страница будет перезагружена.")
        time.sleep(1)
        st.rerun()

    def _add_reset_button(self):
        with st.sidebar:
            st.divider()
            st.write("### 🛑 Управление состоянием")
            confirm_key = "confirm_reset"
            # Создаем чекбокс и получаем его значение
            confirm = st.checkbox("Подтвердите сброс", key=confirm_key, value=False)
            if st.button("🔄 Сбросить состояние фазы 6", use_container_width=True, type="secondary"):
                if confirm:
                    self._reset_state()
                else:
                    st.warning("Поставьте галочку для подтверждения")

    # ------------------------------------------------------------------
    #                     ОСНОВНОЙ ИНТЕРФЕЙС
    # ------------------------------------------------------------------
    def display_main_interface(self):
        st.title("🚀 Фаза 6: Подготовка к загрузке на сайт (ручной режим)")
        st.markdown("---")

        if 'app_data' not in st.session_state:
            st.error("❌ Нет данных приложения. Завершите фазы 1-5.")
            return

        if not self._load_data():
            return

        self._migrate_fragments()

        # Сканируем единицы и спецсимволы в текстах
        st.session_state.found_units = self._scan_units_in_texts()
        st.session_state.found_special_symbols = self._scan_special_symbols_in_texts()

        self._display_top_panel()
          # Кнопка сброса состояния

        # Общие кнопки для массовых операций
        with st.container():
            st.subheader("🛠️ Массовые операции")
            final_confirm = st.checkbox(
                "⚠️ Подтверждаю, что это финальная замена переменных (рекомендуется после всех исправлений)",
                key="final_confirm"
            )
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("🔄 Заменить переменные во всех блоках", disabled=not final_confirm,
                             use_container_width=True):
                    st.warning(
                        "Вы выполняете финальную замену переменных. Убедитесь, что все остальные правки завершены.")
                    self._apply_variable_replacement()
            with col2:
                if st.button("⚖️ Удалить выбранные единицы из всех блоков", use_container_width=True):
                    units = st.session_state.ui_state.get('selected_units_global', [])
                    self._apply_unit_removal(units_to_remove=units)
            with col3:
                if st.button("🌐 Сгенерировать HTML для всех блоков", use_container_width=True):
                    self._apply_generate_html()
            with col4:
                if st.button("🔍 Проверить ошибки во всех блоках", use_container_width=True):
                    self._check_all_errors()
            with col5:
                if st.button("🔧 Автоисправить regular-блоки", use_container_width=True):
                    self._auto_insert_regular_blocks()

        st.markdown("---")



        tab_options = ["🏷️ Фрагменты", "📋 История замен", "🧩 Шаблоны и HTML", "📤 Экспорт отчета"]
        default_tab = st.session_state.ui_state.get('active_tab', tab_options[0])
        if default_tab not in tab_options:
            default_tab = tab_options[0]
        active_tab = st.radio(
            "Выберите вкладку",
            tab_options,
            horizontal=True,
            label_visibility="collapsed",
            index=tab_options.index(default_tab),
            key="main_tabs"
        )
        st.session_state.ui_state['active_tab'] = active_tab

        if active_tab == tab_options[0]:
            self._display_templates_interface()

        elif active_tab == tab_options[1]:
            self._display_fragments_interface()
        elif active_tab == tab_options[2]:
            self._display_transformations_interface()
        elif active_tab == tab_options[3]:
            self._display_export_interface()

    def _display_top_panel(self):
        with st.expander("⚙️ Настройки обработки (единицы, спецсимволы, сброс)", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write("### 📏 Единицы измерения")
                found_units = st.session_state.get('found_units', [])
                if found_units:
                    selected_units = st.multiselect(
                        "Выберите единицы для удаления:",
                        found_units,
                        default=st.session_state.ui_state.get('selected_units_global', []),
                        key="selected_units_global_widget"
                    )
                    st.session_state.ui_state['selected_units_global'] = selected_units
                else:
                    st.info("В текстах не найдено стандартных единиц.")
                    st.session_state.ui_state['selected_units_global'] = []

                new_unit = st.text_input("Добавить свою единицу:", key="new_unit_input")
                if st.button("➕ Добавить единицу", use_container_width=True):
                    if new_unit and new_unit not in st.session_state.units_manager['units']:
                        st.session_state.units_manager['units'].append(new_unit)
                        self.text_processor.add_unit_to_remove(new_unit)
                        st.session_state.found_units = self._scan_units_in_texts()
                        st.rerun()

            with col2:
                st.write("### ⚡ Специальные символы")
                found_symbols = st.session_state.get('found_special_symbols', [])
                if found_symbols:
                    selected_symbols = st.multiselect(
                        "Выберите символы для удаления:",
                        found_symbols,
                        default=st.session_state.ui_state.get('selected_symbols_global', []),
                        key="selected_symbols_global_widget"
                    )
                    st.session_state.ui_state['selected_symbols_global'] = selected_symbols
                else:
                    st.info("Специальные символы не найдены.")
                    st.session_state.ui_state['selected_symbols_global'] = []

            st.divider()
            col_apply, col_reset = st.columns(2)
            with col_apply:
                if st.button("🗑️ Удалить выбранные единицы и символы из ВСЕХ блоков", use_container_width=True):
                    units = st.session_state.ui_state.get('selected_units_global', [])
                    symbols = st.session_state.ui_state.get('selected_symbols_global', [])
                    if units:
                        self._apply_unit_removal(units_to_remove=units)
                    if symbols:
                        self._apply_special_symbol_removal(symbols_to_remove=symbols)
                    st.rerun()
            with col_reset:
                confirm = st.checkbox("Подтвердите сброс", key="top_reset_confirm")
                if st.button("🔄 Сбросить состояние фазы 6", use_container_width=True, disabled=not confirm):
                    self._reset_state()
    # ------------------------------------------------------------------
    #                     ЭКСПОРТ
    # ------------------------------------------------------------------
    def _display_export_interface(self):
        st.header("📤 Экспорт отчета")
        fm = st.session_state.fragment_manager
        if not fm.fragments:
            st.info("Нет данных для экспорта")
            return
        st.divider()
        st.subheader("🔍 Экспорт для проверки (входные данные фазы 5 + текущее состояние)")

        phase5_data = st.session_state.app_data.get('phase5', {})
        if not phase5_data:
            st.warning("Данные фазы 5 отсутствуют, экспорт будет неполным.")

        col_json, col_xlsx = st.columns(2)
        with col_json:
            if st.button("📥 JSON (проверка)", use_container_width=True):
                json_data = ExportManager.export_verification_json(fm, phase5_data)
                st.download_button(
                    "⬇️ Сохранить JSON",
                    data=json_data,
                    file_name=f"проверка_{fm.category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
        with col_xlsx:
            if st.button("📥 Excel (проверка)", use_container_width=True):
                excel_data = ExportManager.export_verification_excel(fm, phase5_data)
                st.download_button(
                    "⬇️ Сохранить Excel",
                    data=excel_data,
                    file_name=f"проверка_{fm.category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        fmt = st.radio("Формат:", ["XLSX (Excel)", "JSON"], horizontal=True)
        use_html = st.checkbox("Использовать HTML версию", value=st.session_state.ui_state.get('show_html', False))
        st.session_state.ui_state['show_html'] = use_html
        tmpl = fm.generate_template()

        if fmt == "XLSX (Excel)":
            col1, col2, col3 = st.columns(3)
            col1.metric("Фрагментов", len(fm.fragment_names))
            col2.metric("Блоков", len(fm.fragments))
            err_cnt = sum(len(f.errors) for f in fm.fragments)
            col3.metric("Ошибок", err_cnt, delta_color="inverse")

            if st.button("📥 Экспорт в Excel", type="primary", use_container_width=True):
                with st.spinner("Создание Excel..."):
                    excel = ExportManager.export_to_excel(fm, tmpl, use_html)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button("⬇️ Скачать", data=excel,
                                       file_name=f"отчет_{tmpl['category_code']}_{ts}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       use_container_width=True)
        else:
            st.subheader("Экспорт в JSON")
            fragments_data = [f.to_dict() for f in fm.fragments]
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'category': tmpl['category_code'],
                'template': tmpl['template'],
                'fragments': fragments_data,
                'statistics': {
                    'total_fragments': len(fm.fragment_names),
                    'total_blocks': len(fm.fragments),
                    'error_blocks': sum(1 for f in fm.fragments if f.errors),
                    'warning_blocks': sum(1 for f in fm.fragments if f.warnings),
                    'template_order': tmpl['order']
                }
            }
            json_data = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)
            st.download_button("📥 Скачать JSON", data=json_data,
                               file_name=f"отчет_{tmpl['category_code']}_{datetime.now().strftime('%Y%m%d')}.json",
                               mime="application/json", use_container_width=True)

    # ------------------------------------------------------------------
    #                     ФРАГМЕНТЫ (СПИСОК И РЕДАКТОР)
    # ------------------------------------------------------------------
    def _display_fragments_interface(self):
        st.header("🏷️ Фрагменты и блоки")
        fm = st.session_state.fragment_manager

        if not fm.fragments:
            st.info("Нет фрагментов для отображения")
            return

        # --- Фильтры (без изменений) ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_type = st.selectbox("Тип блока", ["Все", "regular", "unique", "other"], key="frag_filter_type")
        with col2:
            status_options = ["Все", "pending", "error", "warning", "processed", "fixed"]
            filter_status = st.selectbox("Статус", status_options, key="frag_filter_status")
        with col3:
            search_text = st.text_input("🔍 Поиск по тексту", value=st.session_state.ui_state.get('fragment_search', ''))
            st.session_state.ui_state['fragment_search'] = search_text
        with col4:
            fragment_names = ["Все фрагменты"] + sorted(fm.fragment_names)
            selected_fragment = st.selectbox("Фрагмент", fragment_names, key="frag_filter_fragment")

        # Применяем фильтры (как раньше)...
        filtered_blocks = fm.fragments.copy()
        if filter_type != "Все":
            filtered_blocks = [b for b in filtered_blocks if b.block_type == filter_type]
        if filter_status != "Все":
            filtered_blocks = [b for b in filtered_blocks if b.status == filter_status]
        if search_text:
            search_lower = search_text.lower()
            filtered_blocks = [
                b for b in filtered_blocks
                if search_lower in b.original_text.lower() or search_lower in b.processed_text.lower()
            ]
        if selected_fragment != "Все фрагменты":
            filtered_blocks = [b for b in filtered_blocks if b.fragment_name == selected_fragment]

        if not filtered_blocks:
            st.info("Нет блоков, соответствующих фильтрам")
            return

        # Пагинация (как раньше)
        per_page = st.selectbox("Блоков на странице", [10, 20, 50, 100], index=1, key="frag_per_page")
        total_blocks = len(filtered_blocks)
        total_pages = max(1, (total_blocks + per_page - 1) // per_page)
        current_page = st.session_state.ui_state.get('fragments_page', 1)
        if current_page > total_pages:
            current_page = total_pages
            st.session_state.ui_state['fragments_page'] = current_page

        # Навигация по страницам (как раньше)
        col_prev, col_page, col_next, col_info = st.columns([1, 2, 1, 3])
        with col_prev:
            if st.button("◀ Предыдущая", disabled=current_page <= 1, key="prev_page"):
                st.session_state.ui_state['fragments_page'] = current_page - 1
                st.rerun()
        with col_page:
            page = st.number_input("Страница", min_value=1, max_value=total_pages,
                                   value=current_page, key="frag_page_input")
            if page != current_page:
                st.session_state.ui_state['fragments_page'] = page
                st.rerun()
        with col_next:
            if st.button("Следующая ▶", disabled=current_page >= total_pages, key="next_page"):
                st.session_state.ui_state['fragments_page'] = current_page + 1
                st.rerun()
        with col_info:
            st.write(f"Всего блоков: {total_blocks}, страниц: {total_pages}")

        start_idx = (current_page - 1) * per_page
        end_idx = start_idx + per_page
        page_blocks = filtered_blocks[start_idx:end_idx]

        # Группируем по фрагментам
        page_blocks_by_fragment = defaultdict(list)
        for block in page_blocks:
            page_blocks_by_fragment[block.fragment_name].append(block)

        # Отображаем
        for frag_name, blocks in page_blocks_by_fragment.items():
            with st.expander(f"📁 **{frag_name}** ({len(blocks)} блоков)", expanded=True):
                for block in blocks:
                    self._render_editable_block(block)

    def _render_editable_block(self, block: FragmentBlock):
        # Определяем цвет рамки по статусу
        border_color = "#ff4d4d" if block.errors else "#f0f2f6"
        with st.container(border=True):
            st.markdown(f"<div style='border-left: 5px solid {border_color}; padding: 10px;'>", unsafe_allow_html=True)

            # Заголовок и краткая информация
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            col1.markdown(f"**{block.fragment_name}** · `{block.block_type}`")
            col2.markdown(f"Статус: `{block.status}`")
            col3.markdown(f"Ошибок: {len(block.errors)}")

            # Иконки операций
            icons = []
            if block.auto_corrected:
                icons.append("🔧")
            if block.html_generated:
                icons.append("🌐")
            if block.units_removed:
                icons.append("⚖️")
            if block.symbols_removed:
                icons.append("⚡")
            col4.markdown(" ".join(icons))

            # Характеристика и значение
            if block.characteristic_name or block.characteristic_value:
                st.caption(f"📌 {block.characteristic_name or '—'}: {block.characteristic_value or '—'}")

            # Превью текста
            text_sample = block.processed_text[:200] + ("..." if len(block.processed_text) > 200 else "")
            st.code(text_sample, language="text")

            # Кнопка редактирования
            editing_id = st.session_state.ui_state.get('editing_block_id', None)
            if st.button("✏️ Редактировать", key=f"edit_btn_{block.id}", use_container_width=True):
                # Закрываем предыдущий редактор, открываем новый
                st.session_state.ui_state['editing_block_id'] = block.id
                st.rerun()

            # Если этот блок сейчас редактируется, показываем редактор
            if editing_id == block.id:
                self._display_inline_block_editor(block)

            st.markdown("</div>", unsafe_allow_html=True)
    def _render_editable_block(self, block: FragmentBlock):
        # Определяем цвет рамки в зависимости от наличия ошибок
        border_color = "#ff4d4d" if block.errors else "#f0f2f6"
        with st.container(border=True):
            st.markdown(f"<div style='border-left: 5px solid {border_color}; padding-left: 10px;'>",
                        unsafe_allow_html=True)

            # Заголовок блока с краткой информацией
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            col1.markdown(f"**{block.fragment_name}** · `{block.block_type}`")
            col2.markdown(f"Статус: `{block.status}`")
            col3.markdown(f"Ошибок: {len(block.errors)}")
            if col4.button("🔧 Операции", key=f"ops_{block.id}"):
                # Показываем всплывающее меню с операциями (как было в карточке)
                pass  # но лучше вынести кнопки ниже
            icons = []
            if block.auto_corrected:
                icons.append("🔧")
            if block.html_generated:
                icons.append("🌐")
            if block.units_removed:
                icons.append("⚖️")
            if block.symbols_removed:
                icons.append("⚡")
            if icons:
                st.markdown(" ".join(icons))
            # Характеристика и значение
            if block.characteristic_name or block.characteristic_value:
                st.caption(f"📌 {block.characteristic_name or '—'}: {block.characteristic_value or '—'}")

            # Текущий текст (сокращённый)
            text_sample = block.processed_text[:200] + ("..." if len(block.processed_text) > 200 else "")
            st.code(text_sample, language="text")

            # Кнопка для раскрытия редактора
            expand_key = f"expand_{block.id}"
            if st.button("✏️ Редактировать", key=expand_key, use_container_width=True):
                st.session_state[f"editing_block_{block.id}"] = True

            # Если включён режим редактирования – показываем полный редактор
            if st.session_state.get(f"editing_block_{block.id}", False):
                self._display_inline_block_editor(block)

            st.markdown("</div>", unsafe_allow_html=True)
    def _display_compact_list(self, filtered_blocks):
        fm = st.session_state.fragment_manager
        per_page = st.selectbox("Записей на странице", [10, 20, 50, 100],
                                index=1, key="frag_per_page")
        st.session_state.ui_state['fragments_per_page'] = per_page

        total_blocks = len(filtered_blocks)
        total_pages = max(1, (total_blocks + per_page - 1) // per_page)
        current_page = st.session_state.ui_state.get('fragments_page', 1)
        if current_page > total_pages:
            current_page = total_pages
            st.session_state.ui_state['fragments_page'] = current_page

        # Навигация по страницам
        col_prev, col_page, col_next, col_info = st.columns([1, 2, 1, 3])
        with col_prev:
            if st.button("◀ Предыдущая", disabled=current_page <= 1, key="prev_page"):
                st.session_state.ui_state['fragments_page'] = current_page - 1
                st.rerun()
        with col_page:
            page = st.number_input("Страница", min_value=1, max_value=total_pages,
                                   value=current_page, key="frag_page_input")
            if page != current_page:
                st.session_state.ui_state['fragments_page'] = page
                st.rerun()
        with col_next:
            if st.button("Следующая ▶", disabled=current_page >= total_pages, key="next_page"):
                st.session_state.ui_state['fragments_page'] = current_page + 1
                st.rerun()
        with col_info:
            st.write(f"Всего блоков: {total_blocks}, страниц: {total_pages}")

        start_idx = (current_page - 1) * per_page
        end_idx = start_idx + per_page
        page_blocks = filtered_blocks[start_idx:end_idx]

        for block in page_blocks:
            self._render_block_card(block)

    def _display_block_navigator(self):
        fm = st.session_state.fragment_manager
        filtered_ids = st.session_state.ui_state.get('filtered_block_ids', [])
        if not filtered_ids:
            st.warning("Нет блоков для отображения")
            if st.button("← Назад к списку"):
                st.session_state.ui_state['compact_view'] = True
                st.session_state.ui_state['selected_block_id'] = None
                st.rerun()
            return

        current_index = st.session_state.ui_state.get('current_block_index', 0)
        if current_index < 0 or current_index >= len(filtered_ids):
            current_index = 0
            st.session_state.ui_state['current_block_index'] = current_index

        block_id = filtered_ids[current_index]
        block = next((b for b in fm.fragments if b.id == block_id), None)
        if not block:
            st.error("Блок не найден")
            return

        st.subheader(f"✏️ Редактирование: {block.fragment_name}")

        # Навигационные кнопки
        col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 2, 1])
        with col_nav1:
            if st.button("◀ Предыдущий", disabled=current_index == 0, use_container_width=True):
                new_index = current_index - 1
                st.session_state.ui_state['current_block_index'] = new_index
                st.session_state.ui_state['selected_block_id'] = filtered_ids[new_index]
                st.rerun()
        with col_nav2:
            if st.button("Следующий ▶", disabled=current_index == len(filtered_ids) - 1, use_container_width=True):
                new_index = current_index + 1
                st.session_state.ui_state['current_block_index'] = new_index
                st.session_state.ui_state['selected_block_id'] = filtered_ids[new_index]
                st.rerun()
        with col_nav3:
            st.write(f"Блок {current_index + 1} из {len(filtered_ids)}")
        with col_nav4:
            if st.button("← К списку", use_container_width=True):
                st.session_state.ui_state['compact_view'] = True
                st.session_state.ui_state['selected_block_id'] = None
                st.rerun()

        # --- Информация о блоке ---
        col1, col2, col3, col4 = st.columns(4)
        col1.write(f"**Тип:** {block.block_type}")
        col2.write(f"**Хар-ка:** {block.characteristic_name or '-'}")
        col3.write(f"**Значение:** {block.characteristic_value or '-'}")
        col4.write(f"**Статус:** {block.status}")

        with st.expander("📊 Сравнение: исходный → обработанный", expanded=False):
            col_before, col_after = st.columns(2)
            with col_before:
                st.markdown("**До обработки:**")
                st.code(block.original_text if block.original_text else "(пусто)")
            with col_after:
                st.markdown("**После обработки (текущий результат):**")
                st.code(block.processed_text if block.processed_text else "(пусто)")
                if block.html_text:
                    st.markdown("**HTML версия:**")
                    st.code(block.html_text[:300] + ("..." if len(block.html_text) > 300 else ""))

        if block.errors:
            with st.expander(f"❌ Ошибки ({len(block.errors)})", expanded=False):
                for e in block.errors:
                    st.write(f"- {e}")
        if block.special_symbols:
            with st.expander(f"⚡ Спецсимволы ({len(block.special_symbols)})", expanded=False):
                for sym, st_pos, end_pos in block.special_symbols[:20]:
                    st.write(f"- '{sym}' на {st_pos}-{end_pos}")
                if len(block.special_symbols) > 20:
                    st.write(f"... и ещё {len(block.special_symbols) - 20}")

        st.divider()

        # --- Кнопки операций ---
        st.subheader("🛠️ Операции над текстом")
        with st.popover("⚙️", use_container_width=True):
            if st.button("🔄 Заменить переменные", key=f"pop_replace_{block.id}", use_container_width=True):
                self._apply_variable_replacement(block.id)
                st.rerun()
            if st.button("🔧 Добавить значение", key=f"pop_autofix_{block.id}", use_container_width=True):
                self._auto_insert_regular_blocks(block.id)
                st.rerun()
            if st.button("⚖️ Удалить единицы", key=f"pop_remove_{block.id}", use_container_width=True):
                units = st.session_state.ui_state.get('selected_units_global', [])
                self._apply_unit_removal(block.id, units)
                st.rerun()
            if st.button("🌐 HTML", key=f"pop_html_{block.id}", use_container_width=True):
                self._apply_generate_html(block.id)
                st.rerun()
            if st.button("⚡ Удалить спецсимволы", key=f"pop_spec_{block.id}", use_container_width=True):
                symbols = st.session_state.ui_state.get('selected_symbols_global', [])
                self._apply_special_symbol_removal(block.id, symbols)
                st.rerun()

        st.divider()

        # --- Вставка переменных (как в редакторе) ---
        st.subheader("🔄 Вставка переменных")
        textarea_key = f"nav_editor_text_{block.id}"
        if textarea_key not in st.session_state:
            st.session_state[textarea_key] = block.processed_text

        col_pos1, col_pos2 = st.columns([2, 2])
        with col_pos1:
            insert_mode = st.radio(
                "Позиция вставки:",
                ["в конец", "в начало", "после слова"],
                horizontal=True,
                key=f"nav_ins_mode_{block.id}"
            )
        with col_pos2:
            word_index = 0
            if insert_mode == "после слова":
                words = st.session_state[textarea_key].split()
                if words:
                    word_index = st.selectbox(
                        "После какого слова:",
                        options=list(range(len(words))),
                        format_func=lambda i: f"{i + 1}. {words[i][:20]}",
                        key=f"nav_ins_word_{block.id}"
                    )
                else:
                    st.info("Текст пуст, вставка в конец")
                    insert_mode = "в конец"

        suggestions = self.vm.get_variable_suggestions()
        city_vars = [v for v in suggestions if 'город' in v['name'].lower()]
        product_vars = [v for v in suggestions if 'товар' in v['name'].lower()]
        category_vars = [v for v in suggestions if 'категория' in v['name'].lower()]
        prop_var = next((v for v in suggestions if v['type'] == 'prop'), None)
        frag_var = next((v for v in suggestions if v['type'] == 'fragment'), None)
        other_vars = [v for v in suggestions if v not in city_vars + product_vars + category_vars
                      and v != prop_var and v != frag_var]

        def insert_variable(text, var_value, mode, word_idx):
            if mode == "в начало":
                return var_value + " " + text if text else var_value
            elif mode == "после слова" and word_idx < len(text.split()):
                parts = text.split()
                parts.insert(word_idx + 1, var_value)
                return " ".join(parts)
            else:
                if text and not text.endswith(' '):
                    text += ' '
                return text + var_value

        col_city, col_prod, col_cat, col_propfrag, col_other = st.columns(5)

        with col_city:
            with st.popover("🌆 Город", use_container_width=True):
                for idx, var in enumerate(city_vars):
                    if st.button(var['value'], key=f"nav_city_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()
        with col_prod:
            with st.popover("🏷️ Товар", use_container_width=True):
                for idx, var in enumerate(product_vars):
                    if st.button(var['value'], key=f"nav_prod_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()
        with col_cat:
            with st.popover("📂 Категория", use_container_width=True):
                for idx, var in enumerate(category_vars):
                    if st.button(var['value'], key=f"nav_cat_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()
        with col_propfrag:
            col_p, col_f = st.columns(2)
            with col_p:
                if prop_var and st.button("prop", key=f"nav_prop_{block.id}", use_container_width=True):
                    st.session_state[textarea_key] = insert_variable(
                        st.session_state[textarea_key],
                        prop_var['value'],
                        insert_mode,
                        word_index if insert_mode == "после слова" else 0
                    )
                    st.rerun()
            with col_f:
                if frag_var and st.button("fragment", key=f"nav_frag_{block.id}", use_container_width=True):
                    st.session_state[textarea_key] = insert_variable(
                        st.session_state[textarea_key],
                        frag_var['value'],
                        insert_mode,
                        word_index if insert_mode == "после слова" else 0
                    )
                    st.rerun()
        with col_other:
            with st.popover("📝 Прочие", use_container_width=True):
                for idx, var in enumerate(other_vars):
                    if st.button(var['name'], key=f"nav_other_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()

        st.divider()

        # --- Редактор текста ---
        edited_text = st.text_area(
            "Текст блока:",
            value=st.session_state[textarea_key],
            height=200,
            key=textarea_key,
            label_visibility="collapsed"
        )
        if st.session_state[textarea_key] != edited_text:
            st.session_state[textarea_key] = edited_text

        # --- Кнопка сохранения (и удаления, если нужно) ---
        col_save, col_delete = st.columns(2)
        with col_save:
            if st.button("💾 Сохранить изменения", type="primary", key=f"nav_save_{block.id}", use_container_width=True):
                old_text = block.processed_text
                block.processed_text = edited_text
                block.last_modified = datetime.now()
                # Обновляем ошибки
                missing = self.text_processor.check_regular_brackets(block.processed_text, block.block_type)
                block.errors = [e for e in block.errors if "отсутствует значение в квадратных скобках" not in e]
                if missing:
                    block.errors.extend(missing)
                    block.status = 'error'
                else:
                    block.status = 'fixed' if not block.errors else block.status
                block.special_symbols = self.text_processor._find_special_symbols(block.processed_text)
                trans = TextTransformation(
                    block_id=block.id,
                    fragment_name=block.fragment_name,
                    transformation_type=TransformationType.MANUAL_CORRECTION,
                    original=old_text,
                    result=edited_text,
                    severity=SeverityLevel.INFO,
                    user="user"
                )
                st.session_state.transformation_registry.add(trans)
                st.success("✅ Текст сохранён")
                st.rerun()
        with col_delete:
            if st.button("🗑️ Удалить блок", key=f"nav_delete_{block.id}", use_container_width=True):
                if fm.delete_block(block.id):
                    st.success("Блок удалён")
                    # После удаления обновляем список фильтров
                    st.session_state.ui_state['filtered_block_ids'] = [b.id for b in fm.fragments]
                    st.session_state.ui_state['current_block_index'] = 0
                    st.session_state.ui_state['selected_block_id'] = None
                    if st.session_state.ui_state['filtered_block_ids']:
                        st.session_state.ui_state['selected_block_id'] = \
                        st.session_state.ui_state['filtered_block_ids'][0]
                    st.rerun()
                else:
                    st.error("Не удалось удалить блок")
    def _render_block_card(self, block: FragmentBlock):
        with st.container(border=True):
            cols = st.columns([2, 1, 1, 1, 1])
            cols[0].write(f"**{block.fragment_name}** ({block.block_type})")
            cols[1].write(f"Статус: {block.status}")
            cols[2].write(f"Ошибок: {len(block.errors)}")
            if cols[3].button("✏️", key=f"edit_card_{block.id}", use_container_width=True):
                # Переходим в некомпактный режим с этим блоком
                st.session_state.ui_state['selected_block_id'] = block.id
                st.session_state.ui_state['compact_view'] = False
                st.rerun()
            with cols[4].popover("⚙️", use_container_width=True):
                if st.button("🔄 Заменить переменные", key=f"replace_{block.id}", use_container_width=True):
                    self._apply_variable_replacement(block.id)
                    st.rerun()
                if st.button("🔧 Добавить значение", key=f"autofix_{block.id}", use_container_width=True):
                    self._auto_insert_regular_blocks(block.id)
                    st.rerun()
                if st.button("⚖️ Удалить единицы", key=f"remove_{block.id}", use_container_width=True):
                    units = st.session_state.ui_state.get('selected_units_global', [])
                    self._apply_unit_removal(block.id, units)
                    st.rerun()
                if st.button("🌐 HTML", key=f"html_{block.id}", use_container_width=True):
                    self._apply_generate_html(block.id)
                    st.rerun()
                if st.button("⚡ Удалить спецсимволы", key=f"spec_{block.id}", use_container_width=True):
                    symbols = st.session_state.ui_state.get('selected_symbols_global', [])
                    self._apply_special_symbol_removal(block.id, symbols)
                    st.rerun()
            st.caption(f"{block.characteristic_name or '-'}: {block.characteristic_value or '-'}")
            if block.errors:
                st.caption(f"❌ {len(block.errors)} ошибок")

    def _display_inline_block_editor(self, block: FragmentBlock):
        st.markdown("---")
        st.subheader(f"Редактирование: {block.fragment_name}")

        # Информация о блоке (как раньше)
        col1, col2, col3, col4 = st.columns(4)
        col1.write(f"**Тип:** {block.block_type}")
        col2.write(f"**Хар-ка:** {block.characteristic_name or '-'}")
        col3.write(f"**Значение:** {block.characteristic_value or '-'}")
        col4.write(f"**Статус:** {block.status}")

        # Ошибки и спецсимволы
        if block.errors:
            with st.expander(f"❌ Ошибки ({len(block.errors)})", expanded=False):
                for e in block.errors:
                    st.write(f"- {e}")
        if block.special_symbols:
            with st.expander(f"⚡ Спецсимволы ({len(block.special_symbols)})", expanded=False):
                for sym, st_pos, end_pos in block.special_symbols[:20]:
                    st.write(f"- '{sym}' на {st_pos}-{end_pos}")
                if len(block.special_symbols) > 20:
                    st.write(f"... и ещё {len(block.special_symbols) - 20}")

        # Кнопки операций (как раньше)
        with st.popover("⚙️", use_container_width=True):
            if st.button("🔄 Заменить переменные", key=f"pop_replace_{block.id}", use_container_width=True):
                self._apply_variable_replacement(block.id)
                st.rerun()
            if st.button("🔧 Добавить значение", key=f"pop_autofix_{block.id}", use_container_width=True):
                self._auto_insert_regular_blocks(block.id)
                st.rerun()
            if st.button("⚖️ Удалить единицы", key=f"pop_remove_{block.id}", use_container_width=True):
                units = st.session_state.ui_state.get('selected_units_global', [])
                self._apply_unit_removal(block.id, units)
                st.rerun()
            if st.button("🌐 HTML", key=f"pop_html_{block.id}", use_container_width=True):
                self._apply_generate_html(block.id)
                st.rerun()
            if st.button("⚡ Удалить спецсимволы", key=f"pop_spec_{block.id}", use_container_width=True):
                symbols = st.session_state.ui_state.get('selected_symbols_global', [])
                self._apply_special_symbol_removal(block.id, symbols)
                st.rerun()

        st.divider()

        # --- ПАНЕЛЬ ВСТАВКИ ПЕРЕМЕННЫХ ---
        st.subheader("🔄 Вставка переменных")
        textarea_key = f"editor_text_{block.id}"
        if textarea_key not in st.session_state:
            st.session_state[textarea_key] = block.processed_text

        col_pos1, col_pos2 = st.columns([2, 2])
        with col_pos1:
            insert_mode = st.radio(
                "Позиция вставки:",
                ["в конец", "в начало", "после слова"],
                horizontal=True,
                key=f"ins_mode_{block.id}"
            )
        with col_pos2:
            word_index = 0
            if insert_mode == "после слова":
                words = st.session_state[textarea_key].split()
                if words:
                    word_index = st.selectbox(
                        "После какого слова:",
                        options=list(range(len(words))),
                        format_func=lambda i: f"{i + 1}. {words[i][:20]}",
                        key=f"ins_word_{block.id}"
                    )
                else:
                    st.info("Текст пуст, вставка в конец")
                    insert_mode = "в конец"

        suggestions = self.vm.get_variable_suggestions()
        city_vars = [v for v in suggestions if 'город' in v['name'].lower()]
        product_vars = [v for v in suggestions if 'товар' in v['name'].lower()]
        category_vars = [v for v in suggestions if 'категория' in v['name'].lower()]
        prop_var = next((v for v in suggestions if v['type'] == 'prop'), None)
        frag_var = next((v for v in suggestions if v['type'] == 'fragment'), None)
        other_vars = [v for v in suggestions if v not in city_vars + product_vars + category_vars
                      and v != prop_var and v != frag_var]

        def insert_variable(text: str, var_value: str, mode: str, word_idx: int = 0) -> str:
            if mode == "в начало":
                return var_value + " " + text if text else var_value
            elif mode == "после слова" and word_idx < len(text.split()):
                parts = text.split()
                parts.insert(word_idx + 1, var_value)
                return " ".join(parts)
            else:
                if text and not text.endswith(' '):
                    text += ' '
                return text + var_value

        col_city, col_prod, col_cat, col_propfrag, col_other = st.columns(5)

        with col_city:
            with st.popover("🌆 Город", use_container_width=True):
                for idx, var in enumerate(city_vars):
                    if st.button(var['value'], key=f"city_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()
        with col_prod:
            with st.popover("🏷️ Товар", use_container_width=True):
                for idx, var in enumerate(product_vars):
                    if st.button(var['value'], key=f"prod_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()
        with col_cat:
            with st.popover("📂 Категория", use_container_width=True):
                for idx, var in enumerate(category_vars):
                    if st.button(var['value'], key=f"cat_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()
        with col_propfrag:
            col_p, col_f = st.columns(2)
            with col_p:
                if prop_var and st.button("prop", key=f"prop_{block.id}", use_container_width=True):
                    st.session_state[textarea_key] = insert_variable(
                        st.session_state[textarea_key],
                        prop_var['value'],
                        insert_mode,
                        word_index if insert_mode == "после слова" else 0
                    )
                    st.rerun()
            with col_f:
                if frag_var and st.button("fragment", key=f"frag_{block.id}", use_container_width=True):
                    st.session_state[textarea_key] = insert_variable(
                        st.session_state[textarea_key],
                        frag_var['value'],
                        insert_mode,
                        word_index if insert_mode == "после слова" else 0
                    )
                    st.rerun()
        with col_other:
            with st.popover("📝 Прочие", use_container_width=True):
                for idx, var in enumerate(other_vars):
                    if st.button(var['name'], key=f"other_{block.id}_{idx}", use_container_width=True):
                        st.session_state[textarea_key] = insert_variable(
                            st.session_state[textarea_key],
                            var['value'],
                            insert_mode,
                            word_index if insert_mode == "после слова" else 0
                        )
                        st.rerun()

        st.divider()

        # --- РЕДАКТОР ТЕКСТА ---
        textarea_key = f"inline_editor_text_{block.id}"
        if textarea_key not in st.session_state:
            st.session_state[textarea_key] = block.processed_text

        edited_text = st.text_area(
            "Текст блока:",
            value=st.session_state[textarea_key],
            height=200,
            key=textarea_key,
            label_visibility="collapsed"
        )
        if st.session_state[textarea_key] != edited_text:
            st.session_state[textarea_key] = edited_text

        # Кнопки сохранения, закрытия, удаления
        col_save, col_close, col_delete = st.columns(3)
        with col_save:
            if st.button("💾 Сохранить", type="primary", key=f"inline_save_{block.id}", use_container_width=True):
                # Сохраняем, обновляем ошибки
                old_text = block.processed_text
                block.processed_text = edited_text
                block.last_modified = datetime.now()
                # Проверка regular-блоков по новому методу
                if block.block_type == 'regular':
                    errors = self.text_processor.check_regular_brackets(
                        block.processed_text, block.characteristic_value
                    )
                    block.errors = [e for e in block.errors if "значение" not in e]
                    if errors:
                        block.errors.extend(errors)
                        block.status = 'error'
                    else:
                        block.status = 'fixed' if not block.errors else block.status
                else:
                    # Для non-regular пока оставляем старую логику (или можно добавить проверку)
                    pass
                block.special_symbols = self.text_processor._find_special_symbols(block.processed_text)
                trans = TextTransformation(...)  # создаём трансформацию
                st.session_state.transformation_registry.add(trans)
                st.success("✅ Текст сохранён")
                st.rerun()
        with col_close:
            if st.button("🚫 Закрыть", key=f"inline_close_{block.id}", use_container_width=True):
                st.session_state.ui_state['editing_block_id'] = None
                if textarea_key in st.session_state:
                    del st.session_state[textarea_key]
                st.rerun()
        with col_delete:
            if st.button("🗑️ Удалить", key=f"inline_delete_{block.id}", use_container_width=True):
                if st.session_state.fragment_manager.delete_block(block.id):
                    st.success("Блок удалён")
                    st.session_state.ui_state['editing_block_id'] = None
                    if textarea_key in st.session_state:
                        del st.session_state[textarea_key]
                    st.rerun()
                else:
                    st.error("Не удалось удалить блок")

    # ------------------------------------------------------------------
    #                     ИСТОРИЯ ТРАНСФОРМАЦИЙ
    # ------------------------------------------------------------------
    def _display_transformations_interface(self):
        st.header("📋 История замен и трансформаций")
        registry = st.session_state.transformation_registry

        if not registry.transformations:
            st.info("Нет записей о трансформациях")
            return

        col1, col2 = st.columns(2)
        with col1:
            type_filter = st.selectbox(
                "Тип трансформации",
                ["Все"] + [t.value for t in TransformationType],
                key="trans_type_filter"
            )
        with col2:
            severity_filter = st.selectbox(
                "Важность",
                ["Все"] + [s.value for s in SeverityLevel],
                key="trans_sev_filter"
            )

        filtered = registry.transformations
        if type_filter != "Все":
            filtered = [t for t in filtered if t.transformation_type.value == type_filter]
        if severity_filter != "Все":
            filtered = [t for t in filtered if t.severity.value == severity_filter]

        data = []
        for t in filtered:
            data.append({
                "Время": t.timestamp.strftime("%H:%M:%S"),
                "Фрагмент": t.fragment_name,
                "Тип": t.transformation_type.value,
                "Было": t.original[:50] + ("..." if len(t.original) > 50 else ""),
                "Стало": t.result[:50] + ("..." if len(t.result) > 50 else ""),
                "Важность": t.severity.value,
                "Пользователь": t.user
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, height=500)

        st.subheader("Статистика")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Всего операций", len(registry.transformations))
        col2.metric("Замен переменных", len([t for t in registry.transformations if
                                             t.transformation_type == TransformationType.VARIABLE_REPLACE]))
        col3.metric("Ошибок", len(registry.get_errors()))
        col4.metric("Предупреждений", len(registry.get_warnings()))

    # ------------------------------------------------------------------
    #                     ШАБЛОНЫ И HTML
    # ------------------------------------------------------------------
    def _display_templates_interface(self):
        st.header("🧩 Шаблоны и HTML предпросмотр")
        fm = st.session_state.fragment_manager

        if not fm.fragment_names:
            st.info("Нет фрагментов для построения шаблона")
            return

        tab1, tab2 = st.tabs(["Конструктор шаблона", "HTML предпросмотр"])

        with tab1:
            self._display_template_builder()
        with tab2:
            self._display_html_preview()

    def _display_template_builder(self):
        fm = st.session_state.fragment_manager
        cat_code = st.text_input("Код категории:", value=fm.category, key="template_cat_code")

        st.subheader("Порядок фрагментов")
        frags = sorted(fm.fragment_names)
        if not fm.template_order:
            fm.template_order = frags.copy()

        selected = st.multiselect(
            "Выберите и упорядочьте фрагменты:",
            frags,
            default=fm.template_order,
            key="template_order_selector"
        )
        if selected:
            fm.template_order = selected
            tmpl_data = fm.generate_template(cat_code)
            template_text = tmpl_data['template']

            st.write("**Итоговый шаблон:**")
            st.code(template_text, language="text")

            col1, col2, col3 = st.columns(3)
            col1.button("📋 Копировать", key="copy_template")
            col2.download_button(
                "💾 Скачать шаблон",
                data=template_text,
                file_name=f"шаблон_{cat_code}.txt",
                mime="text/plain",
                use_container_width=True
            )
            if col3.button("🔄 Автоупорядочить", use_container_width=True):
                priority = ['заголовок', 'название', 'описание', 'характеристик', 'параметр', 'примечание']
                ordered = []
                for kw in priority:
                    for f in frags:
                        if kw in f.lower() and f not in ordered:
                            ordered.append(f)
                for f in frags:
                    if f not in ordered:
                        ordered.append(f)
                fm.template_order = ordered
                st.rerun()

    def _display_html_preview(self):
        fm = st.session_state.fragment_manager

        st.subheader("🔄 Предпросмотр HTML")
        st.info("HTML генерируется из обработанного текста с заменой переменных на заглушки. "
                "Для полноценного отображения необходимы реальные данные на сайте.")

        mode = st.radio("Режим:", ["Все фрагменты", "Выбрать фрагмент"], horizontal=True, key="html_mode")

        if mode == "Все фрагменты":
            combined_html = []
            for f in fm.fragments:
                if f.html_text:
                    combined_html.append(f"<!-- Фрагмент: {f.fragment_name} -->")
                    combined_html.append(f.html_text)
                    combined_html.append("<hr>")
            if not combined_html:
                st.info("Нет сгенерированного HTML. Сначала сгенерируйте HTML для блоков.")
                return
            html_all = "\n".join(combined_html)
            st.markdown("**Предпросмотр (рендер):**")
            st.markdown(html_all, unsafe_allow_html=True)
            with st.expander("📄 Исходный HTML код"):
                st.code(html_all, language="html")
            st.download_button(
                "📥 Скачать полный HTML",
                data=html_all,
                file_name=f"все_фрагменты_{fm.category}.html",
                mime="text/html"
            )
        else:
            frag_names = sorted(fm.fragment_names)
            if not frag_names:
                return
            selected_frag = st.selectbox("Выберите фрагмент:", frag_names, key="html_frag_select")
            blocks = fm.get_fragment_blocks(selected_frag)
            html_blocks = [b.html_text for b in blocks if b.html_text]
            if not html_blocks:
                st.info("HTML для этого фрагмента не сгенерирован.")
                return
            combined_html = []
            for b in blocks:
                if b.html_text:
                    combined_html.append(f"<!-- Блок {b.id[:8]} -->")
                    combined_html.append(b.html_text)
            html_frag = "\n".join(combined_html)
            st.markdown("**Предпросмотр (рендер):**")
            st.markdown(html_frag, unsafe_allow_html=True)
            with st.expander("📄 Исходный HTML код"):
                st.code(html_frag, language="html")
            st.download_button(
                "📥 Скачать HTML фрагмента",
                data=html_frag,
                file_name=f"{selected_frag}.html",
                mime="text/html"
            )


def main():
    if 'current_phase' not in st.session_state:
        st.session_state.current_phase = 6

    if 'app_data' not in st.session_state:
        st.error("❌ Нет данных приложения")
        st.info("Завершите предыдущие фазы")
        if st.button("← Вернуться к началу", use_container_width=True):
            st.session_state.current_phase = 1
            st.rerun()
        return

    interface = Phase6Interface()
    interface.display_main_interface()


if __name__ == "__main__":
    main()