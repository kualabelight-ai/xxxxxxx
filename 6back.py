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

    def replace_variables(self, text: str, block_type: str,
                         char_name: Optional[str] = None,
                         char_value: Optional[str] = None) -> Dict:
        """
        Заменяет выражения [variable] на соответствующие переменные.
        Если в regular блоке нет ни одной скобки, но есть characteristic_value,
        автоматически добавляет [значение] в конец текста.
        """
        errors = []
        warnings = []
        special_symbols = self._find_special_symbols(text)

        matches = list(self.pattern.finditer(text))
        processed_text = text
        offset = 0
        replacements = []

        # Автоматическое добавление значения для regular блока, если нет скобок
        auto_added = False
        added_value_text = None

        if block_type == 'regular' and not matches and char_value:
            # Добавляем [значение] в конец текста
            if processed_text and not processed_text.endswith(' '):
                processed_text += ' '
            added_text = f"[{char_value}]"
            processed_text += added_text
            auto_added = True
            added_value_text = added_text
            # Зарегистрируем это как автоматическую вставку (будет обработано в вызывающем коде)
            warnings.append(f"Автоматически добавлено значение: {added_text}")
            # После добавления нужно снова найти скобки, чтобы заменить их на prop
            matches = list(self.pattern.finditer(processed_text))
            # offset не меняем, так как добавляли в конец после всех совпадений

        # Теперь заменяем все найденные скобки
        offset = 0
        for match in matches:
            var_name = match.group(1).strip()
            start, end = match.span()

            if block_type == 'regular':
                replacement = f"{{prop {char_name if char_name else var_name}}}"
            else:
                var_lower = var_name.lower()
                found = False
                for sys_var, data in self.vm.system_vars.items():
                    if sys_var.lower() == var_lower:
                        replacement = data['variants'][0]
                        found = True
                        break
                if not found:
                    replacement = f"{{system {var_name}}}"

            new_start = start + offset
            new_end = end + offset
            processed_text = processed_text[:new_start] + replacement + processed_text[new_end:]
            offset += len(replacement) - (end - start)

            replacements.append({
                'original': match.group(),
                'replacement': replacement,
                'position': (start, end)
            })

        # Если regular блок и после всех действий всё ещё нет скобок — ошибка
        if block_type == 'regular' and not matches and not auto_added:
            errors.append("В regular-блоке отсутствует значение в квадратных скобках [...]")

        return {
            'processed_text': processed_text,
            'replacements': replacements,
            'auto_added': auto_added,
            'added_value': char_value if auto_added else None,
            'errors': errors,
            'warnings': warnings,
            'special_symbols': special_symbols
        }

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

    def check_missing_brackets(self, text: str, block_type: str) -> List[str]:
        if block_type == 'regular' and not self.pattern.search(text):
            return ["В regular-блоке отсутствует значение в квадратных скобках [...]"]
        return []

    def _find_special_symbols(self, text: str) -> List[Tuple[str, int, int]]:
        specials = []
        for match in self.special_symbols_pattern.finditer(text):
            symbol = match.group()
            if symbol not in ['[', ']', ',', '.', '-', '_', ' ', '\t', '\n']:
                specials.append((symbol, match.start(), match.end()))
        return specials

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

    def add_unit_to_remove(self, unit: str):
        if unit and unit not in self.units_to_remove:
            self.units_to_remove.append(unit)

    def remove_unit_from_list(self, unit: str):
        if unit in self.units_to_remove:
            self.units_to_remove.remove(unit)

    def find_units_in_text(self, text: str) -> List[str]:
        found = set()
        text_lower = text.lower()
        for unit in self.units_to_remove:
            pattern = r'\b' + re.escape(unit.lower()) + r'\b'
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
        if 'show_replace_table' not in st.session_state:
            st.session_state.show_replace_table = False
        if 'replace_table_data' not in st.session_state:
            st.session_state.replace_table_data = None

    def _init_ui_state(self):
        default_ui_state = {
            'selected_block_id': None,
            'editing_mode': False,
            'active_tab': 'fragments',
            'show_html': False,
            'selected_issues': set(),
            'fragments_page': 1,
            'fragments_per_page': 20,
            'fragment_search': '',
            'fragment_group_by': 'none',
            'insert_position_mode': 'end',
            'insert_position_word_index': 0,
            'selected_units_global': [],
            'compact_view': True
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

    def _manage_units(self):
        with st.sidebar.expander("⚖️ Единицы измерения", expanded=False):
            st.write("### Все доступные единицы")
            st.write("Список по умолчанию + пользовательские:")
            for unit in st.session_state.units_manager['units']:
                st.write(f"- {unit}")

            st.divider()
            st.write("### Найденные в текстах единицы")
            found = st.session_state.get('found_units', [])
            if found:
                selected = st.multiselect(
                    "Выберите единицы для удаления:",
                    found,
                    default=st.session_state.ui_state.get('selected_units_global', []),
                    key="selected_units_global_widget"
                )
                st.session_state.ui_state['selected_units_global'] = selected
            else:
                st.info("В текстах не найдено стандартных единиц измерения.")
                st.session_state.ui_state['selected_units_global'] = []

            st.divider()
            new_unit = st.text_input("Добавить свою единицу:")
            if st.button("➕ Добавить", use_container_width=True):
                if new_unit and new_unit not in st.session_state.units_manager['units']:
                    st.session_state.units_manager['units'].append(new_unit)
                    self.text_processor.add_unit_to_remove(new_unit)
                    st.session_state.found_units = self._scan_units_in_texts()
                    st.rerun()

            if st.button("🔄 Сбросить к настройкам по умолчанию", use_container_width=True):
                default_units = [
                    "мм", "метр", "м", "см", "дм", "км", "миллиметр", "сантиметр", "дециметр", "километр",
                    "кг", "г", "мг", "тонна", "т", "грамм", "миллиграмм", "килограмм",
                    "л", "мл", "литр", "миллилитр", "шт", "штук", "штука", "штуки",
                    "кг/м", "г/см³", "г/см3", "кг/м³", "кг/м3", "°C", "°F", "град", "градус", "градусов"
                ]
                st.session_state.units_manager['units'] = default_units
                self.text_processor.units_to_remove = default_units.copy()
                st.session_state.found_units = self._scan_units_in_texts()
                st.rerun()

    # ------------------------------------------------------------------
    #                     ОПЕРАЦИИ НАД БЛОКАМИ (ИНДИВИДУАЛЬНЫЕ И ОБЩИЕ)
    # ------------------------------------------------------------------
    def _apply_variable_replacement(self, block_id: str = None):
        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        blocks = [next((b for b in fm.fragments if b.id == block_id), None)] if block_id else fm.fragments
        blocks = [b for b in blocks if b is not None]

        all_replacements = []
        auto_inserts = []

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
            block.errors = list(set([e for e in block.errors if "отсутствует значение в квадратных скобках" not in e] + result['errors']))
            if result['auto_added']:
                block.auto_corrected = True
                block.added_value = result['added_value']
                auto_inserts.append((block, result['added_value']))
            if result['errors']:
                block.status = 'error'
            else:
                block.status = 'processed'
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

            if result['auto_added']:
                trans = TextTransformation(
                    block_id=block.id,
                    fragment_name=block.fragment_name,
                    transformation_type=TransformationType.AUTO_INSERT,
                    original="",
                    result=f"[{result['added_value']}]",
                    meta={'value': result['added_value']},
                    severity=SeverityLevel.WARNING,
                    user="system"
                )
                registry.add(trans)

        if all_replacements or auto_inserts:
            st.success("✅ Переменные заменены")
            if all_replacements:
                df = pd.DataFrame(all_replacements)
                st.dataframe(df, use_container_width=True)
            if auto_inserts:
                for block, val in auto_inserts:
                    st.info(f"ℹ️ Блок {block.fragment_name}: автоматически добавлено значение [{val}]")
        else:
            st.info("Нет замен для выполнения")

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

        if all_removed:
            st.success(f"✅ Удалены единицы из {len(set(b for b,_ in all_removed))} блоков")
            df = pd.DataFrame(all_removed, columns=["Фрагмент", "Единица"]).drop_duplicates()
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Единицы для удаления не найдены в текстах.")

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

        st.success(f"🌐 HTML сгенерирован для {generated} блоков")
        if generated == 1 and block_id:
            st.markdown(blocks[0].html_text, unsafe_allow_html=True)

    def _check_all_errors(self):
        fm = st.session_state.fragment_manager
        registry = st.session_state.transformation_registry
        errors_found = 0
        for block in fm.fragments:
            missing = self.text_processor.check_missing_brackets(block.processed_text, block.block_type)
            if missing:
                new_errors = [e for e in missing if e not in block.errors]
                if new_errors:
                    block.errors.extend(new_errors)
                    block.status = 'error'
                    for err in new_errors:
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
                    errors_found += len(new_errors)

        if errors_found:
            st.error(f"❌ Найдено {errors_found} ошибок. Проверьте вкладку 'Проблемы'.")
        else:
            st.success("✅ Ошибок не найдено")

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

        # Сканируем единицы в текстах
        st.session_state.found_units = self._scan_units_in_texts()

        self._manage_units()

        # Общие кнопки для массовых операций
        with st.container():
            st.subheader("🛠️ Массовые операции")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("🔄 Заменить переменные во всех блоках", use_container_width=True):
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

        st.markdown("---")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📤 Экспорт отчета",
            "🏷️ Фрагменты",
            "⚠️ Проблемы",
            "📋 История замен",
            "🧩 Шаблоны и HTML"
        ])

        with tab1:
            self._display_export_interface()
        with tab2:
            self._display_fragments_interface()
        with tab3:
            self._display_issues_interface()
        with tab4:
            self._display_transformations_interface()
        with tab5:
            self._display_templates_interface()

    # ------------------------------------------------------------------
    #                     ЭКСПОРТ
    # ------------------------------------------------------------------
    def _display_export_interface(self):
        st.header("📤 Экспорт отчета")
        fm = st.session_state.fragment_manager
        if not fm.fragments:
            st.info("Нет данных для экспорта")
            return

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
        st.header("🏷️ Управление фрагментами")
        fm = st.session_state.fragment_manager

        if not fm.fragments:
            st.info("Нет фрагментов для отображения")
            return

        # Если выбран режим редактирования конкретного блока – показываем редактор
        if st.session_state.ui_state.get('editing_mode') and st.session_state.ui_state.get('selected_block_id'):
            block_id = st.session_state.ui_state['selected_block_id']
            block = next((b for b in fm.fragments if b.id == block_id), None)
            if block:
                self._display_block_editor(block)
                return
            else:
                st.session_state.ui_state['editing_mode'] = False
                st.session_state.ui_state['selected_block_id'] = None

        # Компактный вид - чекбокс
        compact = st.checkbox("Компактный вид", value=st.session_state.ui_state.get('compact_view', True))
        st.session_state.ui_state['compact_view'] = compact

        # Фильтры
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_type = st.selectbox("Тип блока", ["Все", "regular", "unique", "other"], key="frag_filter_type")
        with col2:
            filter_status = st.selectbox("Статус", ["Все", "pending", "error", "processed"], key="frag_filter_status")
        with col3:
            search_text = st.text_input("🔍 Поиск по тексту", value=st.session_state.ui_state.get('fragment_search', ''))
            st.session_state.ui_state['fragment_search'] = search_text

        # Применяем фильтры
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

        # Пагинация
        per_page = st.selectbox("Записей на странице", [10, 20, 50, 100],
                                index=1, key="frag_per_page")
        st.session_state.ui_state['fragments_per_page'] = per_page

        total_blocks = len(filtered_blocks)
        total_pages = max(1, (total_blocks + per_page - 1) // per_page)
        current_page = st.session_state.ui_state.get('fragments_page', 1)
        if current_page > total_pages:
            current_page = total_pages
            st.session_state.ui_state['fragments_page'] = current_page

        # Навигация
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
            self._render_block_card(block, compact)

    def _render_block_card(self, block: FragmentBlock, compact: bool = True):
        """Карточка блока с кнопками операций."""
        if compact:
            with st.container(border=True):
                cols = st.columns([2, 1, 1, 1, 1])
                cols[0].write(f"**{block.fragment_name}** ({block.block_type})")
                cols[1].write(f"Статус: {block.status}")
                cols[2].write(f"Ошибок: {len(block.errors)}")
                if cols[3].button("✏️", key=f"edit_card_{block.id}", use_container_width=True):
                    st.session_state.ui_state['selected_block_id'] = block.id
                    st.session_state.ui_state['editing_mode'] = True
                    st.rerun()
                with cols[4].popover("⚙️", use_container_width=True):
                    if st.button("🔄 Заменить переменные", key=f"replace_{block.id}", use_container_width=True):
                        self._apply_variable_replacement(block.id)
                        st.rerun()
                    if st.button("⚖️ Удалить единицы", key=f"remove_{block.id}", use_container_width=True):
                        units = st.session_state.ui_state.get('selected_units_global', [])
                        self._apply_unit_removal(block.id, units)
                        st.rerun()
                    if st.button("🌐 HTML", key=f"html_{block.id}", use_container_width=True):
                        self._apply_generate_html(block.id)
                        st.rerun()
                st.caption(f"{block.characteristic_name or '-'}: {block.characteristic_value or '-'}")
        else:
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 1])
                cols[0].write(f"**{block.fragment_name}** ({block.block_type})")
                cols[1].write(f"Статус: {block.status}")
                cols[2].write(f"Ошибок: {len(block.errors)}")
                if cols[3].button("✏️ Редактировать", key=f"edit_card_{block.id}", use_container_width=True):
                    st.session_state.ui_state['selected_block_id'] = block.id
                    st.session_state.ui_state['editing_mode'] = True
                    st.rerun()

                col_op1, col_op2, col_op3, _ = st.columns([1, 1, 1, 2])
                with col_op1:
                    if st.button("🔄 Заменить переменные", key=f"replace_{block.id}", use_container_width=True):
                        self._apply_variable_replacement(block.id)
                        st.rerun()
                with col_op2:
                    if st.button("⚖️ Удалить единицы", key=f"remove_{block.id}", use_container_width=True):
                        units = st.session_state.ui_state.get('selected_units_global', [])
                        self._apply_unit_removal(block.id, units)
                        st.rerun()
                with col_op3:
                    if st.button("🌐 HTML", key=f"html_{block.id}", use_container_width=True):
                        self._apply_generate_html(block.id)
                        st.rerun()

                st.caption(f"ID: {block.id[:8]} | Хар-ка: {block.characteristic_name or '-'} | Знач: {block.characteristic_value or '-'}")
                with st.expander("👁️ Текущий текст"):
                    st.text(block.processed_text[:300] + ("..." if len(block.processed_text) > 300 else ""))

    def _display_block_editor(self, block: FragmentBlock):
        st.subheader(f"✏️ Редактирование: {block.fragment_name}")

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

        st.divider()

        # --- КНОПКИ ОПЕРАЦИЙ ---
        st.subheader("🛠️ Операции над текстом")
        col_op1, col_op2, col_op3 = st.columns(3)
        with col_op1:
            if st.button("🔄 Заменить переменные", key=f"editor_replace_{block.id}", use_container_width=True):
                self._apply_variable_replacement(block.id)
                st.rerun()
        with col_op2:
            if st.button("⚖️ Удалить единицы", key=f"editor_remove_{block.id}", use_container_width=True):
                units = st.session_state.ui_state.get('selected_units_global', [])
                self._apply_unit_removal(block.id, units)
                st.rerun()
        with col_op3:
            if st.button("🌐 Сгенерировать HTML", key=f"editor_html_{block.id}", use_container_width=True):
                self._apply_generate_html(block.id)
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
        edited_text = st.text_area(
            "Текст блока:",
            value=st.session_state[textarea_key],
            height=200,
            key=textarea_key,
            label_visibility="collapsed"
        )
        if st.session_state[textarea_key] != edited_text:
            st.session_state[textarea_key] = edited_text

        # --- КНОПКИ СОХРАНЕНИЯ / ОТМЕНЫ ---
        col_save, col_cancel, col_delete = st.columns(3)
        with col_save:
            if st.button("💾 Сохранить изменения вручную", type="primary", key=f"save_{block.id}", use_container_width=True):
                old_text = block.processed_text
                block.processed_text = edited_text
                block.last_modified = datetime.now()
                missing = self.text_processor.check_missing_brackets(block.processed_text, block.block_type)
                if missing:
                    block.errors = list(set([e for e in block.errors if "отсутствует значение в квадратных скобках" not in e] + missing))
                    block.status = 'error'
                else:
                    block.errors = [e for e in block.errors if "отсутствует значение в квадратных скобках" not in e]
                    block.status = 'fixed' if not block.errors else block.status
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
                time.sleep(0.5)
                st.session_state.ui_state['editing_mode'] = False
                st.session_state.ui_state['selected_block_id'] = None
                if textarea_key in st.session_state:
                    del st.session_state[textarea_key]
                st.rerun()
        with col_cancel:
            if st.button("🚫 Отмена", key=f"cancel_{block.id}", use_container_width=True):
                st.session_state.ui_state['editing_mode'] = False
                st.session_state.ui_state['selected_block_id'] = None
                if textarea_key in st.session_state:
                    del st.session_state[textarea_key]
                st.rerun()
        with col_delete:
            if st.button("🗑️ Удалить блок", key=f"delete_{block.id}", use_container_width=True):
                if st.session_state.fragment_manager.delete_block(block.id):
                    st.success("Блок удалён")
                    st.session_state.ui_state['editing_mode'] = False
                    st.session_state.ui_state['selected_block_id'] = None
                    if textarea_key in st.session_state:
                        del st.session_state[textarea_key]
                    st.rerun()
                else:
                    st.error("Не удалось удалить блок")

    # ------------------------------------------------------------------
    #                     ПРОБЛЕМЫ И ОШИБКИ
    # ------------------------------------------------------------------
    def _display_issues_interface(self):
        st.header("⚠️ Проблемы и ошибки")
        fm = st.session_state.fragment_manager

        # Обновляем ошибки для regular-блоков
        for f in fm.fragments:
            missing = self.text_processor.check_missing_brackets(f.processed_text, f.block_type)
            if missing:
                f.errors = list(set([e for e in f.errors if "отсутствует значение в квадратных скобках" not in e] + missing))
                f.status = 'error'
            else:
                f.errors = [e for e in f.errors if "отсутствует значение в квадратных скобках" not in e]

        all_issues = []
        for f in fm.fragments:
            for err in f.errors:
                all_issues.append({
                    'block_id': f.id,
                    'fragment_name': f.fragment_name,
                    'issue_type': 'error',
                    'message': err,
                    'block': f
                })
            for warn in f.warnings:
                all_issues.append({
                    'block_id': f.id,
                    'fragment_name': f.fragment_name,
                    'issue_type': 'warning',
                    'message': warn,
                    'block': f
                })
            for sym, st_pos, end_pos in f.special_symbols:
                all_issues.append({
                    'block_id': f.id,
                    'fragment_name': f.fragment_name,
                    'issue_type': 'special_symbol',
                    'message': f"Символ '{sym}' на {st_pos}-{end_pos}",
                    'block': f
                })

        if not all_issues:
            st.success("🎉 Проблем не найдено!")
            return

        col1, col2 = st.columns(2)
        with col1:
            issue_filter = st.selectbox("Тип проблемы", ["Все", "error", "warning", "special_symbol"],
                                        key="issue_type_filter")
        with col2:
            frag_filter = st.selectbox("Фрагмент", ["Все"] + sorted(fm.fragment_names), key="issue_frag_filter")

        filtered = all_issues
        if issue_filter != "Все":
            filtered = [i for i in filtered if i['issue_type'] == issue_filter]
        if frag_filter != "Все":
            filtered = [i for i in filtered if i['fragment_name'] == frag_filter]

        st.write(f"Найдено проблем: {len(filtered)}")

        for i, issue in enumerate(filtered):
            with st.container(border=True):
                cols = st.columns([1, 4, 1])
                icon = "❌" if issue['issue_type'] == 'error' else "⚠️" if issue['issue_type'] == 'warning' else "⚡"
                cols[0].write(f"{icon} **{issue['issue_type'].upper()}**")
                cols[1].write(f"**{issue['fragment_name']}** — {issue['message']}")
                if cols[2].button("✏️ Исправить", key=f"fix_issue_{i}_{issue['block_id']}", use_container_width=True):
                    st.session_state.ui_state['selected_block_id'] = issue['block_id']
                    st.session_state.ui_state['editing_mode'] = True
                    st.rerun()

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