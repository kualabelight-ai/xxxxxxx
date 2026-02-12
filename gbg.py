import streamlit as st
import json
import re
from typing import Dict, List, Any

# --- CSS стили ---
def local_css():
    st.markdown("""
    <style>
    .block-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .variable-chip {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 2px 8px;
        border-radius: 12px;
        margin: 2px;
        font-size: 0.8em;
    }
    .preview-box {
        background: #f8f9fa;
        border-left: 4px solid #1976d2;
        padding: 15px;
        margin: 10px 0;
        font-family: monospace;
        white-space: pre-wrap;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Функции для работы с переменными ---
def extract_variables_from_template(template: str) -> List[str]:
    """Извлекает все переменные из шаблона типа {var_name}"""
    pattern = r'\{([^}]+)\}'
    return re.findall(pattern, template)

def parse_instruction_line(line: str) -> Dict[str, Any]:
    """Парсит строку с инструкциями вида 'инструкция; другая инструкция'"""
    instructions = [i.strip() for i in line.split(';') if i.strip()]
    return {
        "type": "dynamic_list",
        "values": instructions,
        "selection_strategy": "random"
    }

# --- Основное приложение ---
def main():
    st.set_page_config(page_title="Prompt Builder - Phase 2", layout="wide")
    local_css()
    
    st.title("🧩 Конструктор промптов (Фаза 2)")
    st.markdown("### Настройка блоков и переменных для генерации промптов")
    
    # --- Инициализация session_state ---
    if 'blocks' not in st.session_state:
        # Стандартные блоки
        st.session_state.blocks = {
            "characteristic_common": {
                "name": "Обычная характеристика",
                "description": "Шаблон для обычных характеристик со значением в [скобках]",
                "template": """Ты должен генерировать текст, полностью исключая определительные конструкции с тире и союзом 'что'.
{стиль_текста}.
Объем: {объем_характеристики}.

{контекст_категория}.
{скобки_характеристика}.
Тут крайне внимательно: {инструкция_характеристика} {название_характеристики} так, чтобы значение [[значение_характеристики]] было логично вставлено в текст, {подводка_характеристика}
Обязательно используй "{характеристика_маркер}" один раз в начале текста.
Структура предложения: {структура_характеристики}.

{ограничение_повторы}.
{требование_тошноты}.

Обрати внимание: {стоп}.""",
                "variables": {}
            },
            "characteristic_unique": {
                "name": "Уникальная характеристика",
                "description": "Шаблон для уникальных характеристик (значение уже в промпте)",
                "template": """Напиши абзац для текста-описания товара категории: {контекст_категория}.
Не используй слово "{категория_слово}" в тексте.
Раскрой смысл характеристики {название_характеристики} так, чтобы значение "{значение_характеристики}" было логично вставлено в текст, {подводка_характеристика}
Обязательно используй "{характеристика_маркер}" один раз в тексте.
Структура предложения: {структура_характеристики}.
Объем: {объем_характеристики}.
{стиль_текста}
{ограничение_повторы}
{ограничение_слова}""",
                "variables": {}
            },
            "product_title": {
                "name": "Заголовок товара",
                "description": "Генерация SEO-заголовка",
                "template": """Сгенерируй SEO-заголовок для товара: {название_товара}
Основные характеристики: {основные_характеристики}
Требования: {требования_заголовка}
Длина: {длина_заголовка}
Ключевые слова: {ключевые_слова}""",
                "variables": {}
            }
        }
    
    if 'characteristics_mapping' not in st.session_state:
        st.session_state.characteristics_mapping = {}
    
    if 'variable_definitions' not in st.session_state:
        st.session_state.variable_definitions = {}
    
    # --- Загрузка данных из Фазы 1 ---
    st.sidebar.header("📂 Загрузка данных")
    uploaded_result = st.sidebar.file_uploader("Результат Фазы 1", type="json")
    
    characteristics_list = []
    if uploaded_result:
        try:
            phase1_data = json.load(uploaded_result)
            characteristics_list = phase1_data
            st.sidebar.success(f"Загружено {len(characteristics_list)} характеристик")
        except Exception as e:
            st.sidebar.error(f"Ошибка загрузки: {e}")
    
    # --- Основные вкладки ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Управление блоками",
        "🔧 Редактор переменных", 
        "🔗 Привязка к характеристикам",
        "👁️ Предпросмотр"
    ])
    
    with tab1:
        st.header("Управление блоками контента")
        
        # Список блоков
        for block_id, block in st.session_state.blocks.items():
            with st.expander(f"📦 {block['name']} - {block['description']}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Редактирование названия и описания
                    new_name = st.text_input(
                        "Название блока",
                        value=block['name'],
                        key=f"name_{block_id}"
                    )
                    new_desc = st.text_area(
                        "Описание",
                        value=block['description'],
                        key=f"desc_{block_id}"
                    )
                    
                    # Редактор шаблона
                    st.subheader("Шаблон промпта")
                    template = st.text_area(
                        "Шаблон (используйте {переменные})",
                        value=block['template'],
                        height=200,
                        key=f"template_{block_id}"
                    )
                    
                    # Автоматическое определение переменных
                    variables_in_template = extract_variables_from_template(template)
                    if variables_in_template:
                        st.info(f"Обнаружены переменные: {', '.join(variables_in_template)}")
                    
                    # Кнопки сохранения
                    if st.button("💾 Сохранить блок", key=f"save_{block_id}"):
                        st.session_state.blocks[block_id].update({
                            "name": new_name,
                            "description": new_desc,
                            "template": template
                        })
                        st.success("Блок сохранен!")
                        st.rerun()
                
                with col2:
                    st.metric("Переменные", len(variables_in_template))
                    if st.button("❌ Удалить", key=f"del_{block_id}"):
                        if len(st.session_state.blocks) > 1:
                            del st.session_state.blocks[block_id]
                            st.rerun()
        
        # Добавление нового блока
        with st.expander("➕ Добавить новый блок"):
            new_block_name = st.text_input("Название нового блока")
            new_block_desc = st.text_input("Описание")
            new_block_template = st.text_area("Шаблон", height=100)
            
            if st.button("Создать блок") and new_block_name:
                new_id = f"block_{len(st.session_state.blocks)}"
                st.session_state.blocks[new_id] = {
                    "name": new_block_name,
                    "description": new_block_desc,
                    "template": new_block_template,
                    "variables": {}
                }
                st.success(f"Блок '{new_block_name}' создан!")
                st.rerun()
    
    with tab2:
        st.header("Редактор переменных")
        
        # Сбор всех переменных из всех блоков
        all_variables = set()
        for block_id, block in st.session_state.blocks.items():
            vars_in_block = extract_variables_from_template(block['template'])
            all_variables.update(vars_in_block)
        
        if not all_variables:
            st.info("Нет переменных в шаблонах")
        else:
            # Группировка переменных по типам
            variable_groups = {}
            for var in sorted(all_variables):
                if var.endswith(('_текста', '_стиль')):
                    variable_groups.setdefault("Стилистика", []).append(var)
                elif var.endswith(('_инструкция', '_подводка', '_фокус')):
                    variable_groups.setdefault("Инструкции", []).append(var)
                elif var.endswith(('_объем', '_длина')):
                    variable_groups.setdefault("Формат", []).append(var)
                elif var.endswith(('_ограничение', '_требование', '_стоп')):
                    variable_groups.setdefault("Ограничения", []).append(var)
                else:
                    variable_groups.setdefault("Прочие", []).append(var)
            
            # Редактор для каждой группы
            for group_name, vars_in_group in variable_groups.items():
                with st.expander(f"📁 {group_name} ({len(vars_in_group)} переменных)"):
                    for var_name in vars_in_group:
                        st.subheader(f"`{var_name}`")
                        
                        # Определяем тип переменной по имени
                        var_type = st.selectbox(
                            "Тип переменной",
                            ["static", "dynamic_list", "ai_generated", "data_dependent"],
                            key=f"type_{var_name}"
                        )
                        
                        if var_type == "static":
                            value = st.text_area(
                                "Статическое значение",
                                value=st.session_state.variable_definitions.get(var_name, {}).get('value', ''),
                                key=f"static_{var_name}"
                            )
                            
                        elif var_type == "dynamic_list":
                            st.markdown("Введите варианты (каждый с новой строки или через ';')")
                            list_input = st.text_area(
                                "Список вариантов",
                                value='\n'.join(st.session_state.variable_definitions.get(var_name, {}).get('values', [])),
                                height=100,
                                key=f"list_{var_name}"
                            )
                            
                            # Парсинг вариантов
                            if list_input:
                                lines = [line.strip() for line in list_input.split('\n') if line.strip()]
                                all_values = []
                                for line in lines:
                                    if ';' in line:
                                        all_values.extend([v.strip() for v in line.split(';') if v.strip()])
                                    else:
                                        all_values.append(line)
                                
                                if all_values:
                                    st.info(f"Найдено {len(all_values)} вариантов")
                                    with st.expander("Предпросмотр вариантов"):
                                        for i, val in enumerate(all_values[:10], 1):
                                            st.write(f"{i}. {val}")
                                        if len(all_values) > 10:
                                            st.write(f"... и еще {len(all_values) - 10} вариантов")
                            
                        elif var_type == "ai_generated":
                            st.text_area(
                                "Промпт для генерации переменной",
                                value=st.session_state.variable_definitions.get(var_name, {}).get('ai_prompt', ''),
                                key=f"ai_{var_name}",
                                placeholder="Пример: Сгенерируй 5 вариантов инструкций для характеристики 'диаметр трубы'"
                            )
                            
                        elif var_type == "data_dependent":
                            data_source = st.selectbox(
                                "Источник данных",
                                ["название_характеристики", "значение_характеристики", "единица_измерения", "категория"],
                                key=f"source_{var_name}"
                            )
                        
                        # Кнопка сохранения
                        if st.button("💾 Сохранить переменную", key=f"save_var_{var_name}"):
                            # Здесь сохраняем определение переменной
                            st.success(f"Переменная `{var_name}` сохранена")
        
        # Быстрая загрузка стандартных инструкций
        with st.expander("⚡ Быстрая загрузка стандартных инструкций"):
            st.markdown("Вставьте список инструкций (каждая с новой строки или через ';'):")
            bulk_instructions = st.text_area("Инструкции", height=150)
            
            if bulk_instructions and st.button("Распарсить и распределить"):
                # Парсинг инструкций
                lines = [line.strip() for line in bulk_instructions.split('\n') if line.strip()]
                instructions = []
                for line in lines:
                    if ';' in line:
                        instructions.extend([i.strip() for i in line.split(';') if i.strip()])
                    else:
                        instructions.append(line)
                
                # Распределение по переменным
                for var_name in all_variables:
                    if 'инструкция' in var_name:
                        st.session_state.variable_definitions[var_name] = {
                            'type': 'dynamic_list',
                            'values': instructions
                        }
                
                st.success(f"Инструкции распределены по {len([v for v in all_variables if 'инструкция' in v])} переменным")
    
    with tab3:
        st.header("Привязка характеристик к блокам")
        
        if not characteristics_list:
            st.warning("Сначала загрузите данные из Фазы 1")
        else:
            # Таблица привязки
            for char in characteristics_list:
                char_id = char.get("char_id", char.get("id", ""))
                char_name = char.get("char_name", char.get("name", ""))
                
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**{char_name}**")
                    if char.get("is_duplicate"):
                        st.warning("⚠️ Дубликат")
                
                with col2:
                    # Выбор типа характеристики
                    char_type = st.selectbox(
                        "Тип",
                        ["Обычная", "Уникальная", "Пропустить"],
                        key=f"type_{char_id}",
                        index=0 if not char.get("is_unique", False) else 1
                    )
                
                with col3:
                    if char_type != "Пропустить":
                        # Выбор блока
                        block_options = {
                            bid: f"{block['name']} ({bid})" 
                            for bid, block in st.session_state.blocks.items()
                        }
                        
                        selected_block = st.selectbox(
                            "Блок промпта",
                            options=list(block_options.keys()),
                            format_func=lambda x: block_options[x],
                            key=f"block_{char_id}"
                        )
                    else:
                        selected_block = None
                
                with col4:
                    # Предпросмотр промпта
                    if st.button("👁️", key=f"preview_{char_id}"):
                        st.session_state[f"show_preview_{char_id}"] = True
                
                # Сохраняем привязку
                if char_type != "Пропустить" and selected_block:
                    st.session_state.characteristics_mapping[char_id] = {
                        "name": char_name,
                        "type": "unique" if char_type == "Уникальная" else "common",
                        "block": selected_block,
                        "original_data": char
                    }
                
                # Показ предпросмотра
                if st.session_state.get(f"show_preview_{char_id}"):
                    with st.expander("Предпросмотр промпта", expanded=True):
                        # Генерация примерного промпта
                        if selected_block:
                            template = st.session_state.blocks[selected_block]["template"]
                            # Заменяем переменные на примерные значения
                            preview = template
                            for var in extract_variables_from_template(template):
                                if 'название' in var:
                                    preview = preview.replace(f"{{{var}}}", char_name)
                                elif 'значение' in var:
                                    preview = preview.replace(f"{{{var}}}", "примерное_значение")
                                else:
                                    preview = preview.replace(f"{{{var}}}", f"[{var}]")
                            
                            st.code(preview, language="markdown")
                        
                        if st.button("Закрыть", key=f"close_{char_id}"):
                            st.session_state[f"show_preview_{char_id}"] = False
                            st.rerun()
                
                st.divider()
            
            # Экспорт конфигурации
            if st.button("💾 Экспортировать конфигурацию промптов"):
                config = {
                    "blocks": st.session_state.blocks,
                    "characteristics_mapping": st.session_state.characteristics_mapping,
                    "variable_definitions": st.session_state.variable_definitions
                }
                
                st.download_button(
                    "Скачать конфигурацию",
                    data=json.dumps(config, ensure_ascii=False, indent=2),
                    file_name="prompt_config.json",
                    mime="application/json"
                )
    
    with tab4:
        st.header("Полный предпросмотр системы")
        
        # Генерация примерных промптов
        if characteristics_list and st.session_state.characteristics_mapping:
            selected_char = st.selectbox(
                "Выберите характеристику для примера",
                options=list(st.session_state.characteristics_mapping.keys()),
                format_func=lambda x: st.session_state.characteristics_mapping[x]["name"]
            )
            
            if selected_char:
                mapping = st.session_state.characteristics_mapping[selected_char]
                block = st.session_state.blocks[mapping["block"]]
                
                st.subheader(f"Шаблон: {block['name']}")
                st.code(block["template"], language="markdown")
                
                # Показываем как будет выглядеть финальный промпт
                st.subheader("Пример сгенерированного промпта:")
                
                # Собираем все данные
                template = block["template"]
                
                # Для примера, создаем демо-замены
                demo_data = {
                    "название_характеристики": mapping["name"],
                    "значение_характеристики": "3 мм" if mapping["type"] == "common" else "лакированная",
                    "категория": "Труба чугунная",
                    "стиль_текста": "Стиль — аккуратный и профессиональный.",
                    "объем_характеристики": "1 развернутое предложение, 150-180 символов.",
                    "инструкция_характеристика": "Опиши влияние характеристики на использование товара",
                    "подводка_характеристика": "поясни влияние на эксплуатацию",
                    "структура_характеристики": "Сложноподчинённое",
                    "ограничение_повторы": "Контролируй употребление «и», не делай текст перегруженным, используй синонимы.",
                    "требование_тошноты": "Плотность ключевых терминов ≤ 10%.",
                    "стоп": "не применять слова: безупречный, высококачественный..."
                }
                
                # Заменяем переменные
                final_prompt = template
                for var, value in demo_data.items():
                    final_prompt = final_prompt.replace(f"{{{var}}}", value)
                
                # Обрабатываем скобки в зависимости от типа
                if mapping["type"] == "common":
                    final_prompt = final_prompt.replace("[[значение_характеристики]]", "[3 мм]")
                else:
                    final_prompt = final_prompt.replace("[[значение_характеристики]]", "лакированная")
                
                st.markdown('<div class="preview-box">', unsafe_allow_html=True)
                st.text(final_prompt)
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()