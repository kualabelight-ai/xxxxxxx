import streamlit as st
import json
from pathlib import Path
import os
from datetime import datetime


# =============================================================================
# ДИЗАЙН-СИСТЕМА – минималистичный премиальный UI (Linear / Vercel стиль)
# Только CSS, без изменения логики.
# =============================================================================
def local_css():
    st.markdown("""
    <style>
    /* ---------- CSS Variables (используем Streamlit theme) ---------- */
    :root {
        --font-sans: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        --font-mono: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;

        /* Отступы – строгая система */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 32px;
        --space-2xl: 48px;

        /* Скругления – мягкие, но сдержанные */
        --radius-sm: 6px;
        --radius-md: 8px;
        --radius-lg: 12px;
        --radius-xl: 16px;

        /* Тени – почти незаметные, только глубина */
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.02);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.01);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.02), 0 4px 6px -2px rgba(0, 0, 0, 0.01);

        /* Transition – плавно, без рывков */
        --transition: all 0.2s cubic-bezier(0.2, 0, 0, 1);
    }

    /* ---------- Базовые настройки ---------- */
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
        font-family: var(--font-sans);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* Убираем весь визуальный мусор */
    .stApp > header {
        background-color: transparent !important;
    }
    .stApp [data-testid="stToolbar"] {
        display: none;
    }

    /* ---------- Типографика – строгая иерархия ---------- */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 500;
        letter-spacing: -0.01em;
        color: var(--text-color);
    }
    h1 {
        font-size: 2rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        margin-bottom: var(--space-sm);
    }
    h2 {
        font-size: 1.5rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        margin-bottom: var(--space-md);
    }
    h3 {
        font-size: 1.25rem;
        font-weight: 500;
        margin-bottom: var(--space-sm);
    }
    p, li, .stMarkdown {
        font-size: 0.9375rem;
        line-height: 1.6;
        color: var(--text-color);
    }
    .text-secondary {
        font-size: 0.875rem;
        color: var(--text-color);
        opacity: 0.65;
    }
    .text-small {
        font-size: 0.8125rem;
        opacity: 0.6;
    }

    /* ---------- Карточки фаз – премиальный дашборд ---------- */
    .phase-card {
        background-color: var(--secondary-background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        transition: var(--transition);
        box-shadow: var(--shadow-sm);
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .phase-card:hover {
        border-color: rgba(128, 128, 128, 0.1);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    .phase-card.active {
        border: 1px solid var(--primary-color);
        box-shadow: 0 0 0 2px rgba(var(--primary-color-rgb), 0.08);
        background-color: var(--secondary-background-color);
    }
    .phase-card.completed {
        opacity: 0.9;
    }
    .phase-card.pending {
        opacity: 0.7;
    }
    .phase-header {
        display: flex;
        align-items: center;
        gap: var(--space-sm);
        margin-bottom: var(--space-sm);
    }
    .phase-icon {
        font-size: 1.5rem;
        line-height: 1;
    }
    .phase-title {
        font-weight: 600;
        font-size: 1.1rem;
        color: var(--text-color);
        margin: 0;
    }
    .phase-description {
        font-size: 0.875rem;
        color: var(--text-color);
        opacity: 0.65;
        margin-bottom: var(--space-md);
        flex: 1;
    }
    .phase-status {
        display: inline-flex;
        align-items: center;
        gap: var(--space-xs);
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        color: var(--text-color);
        opacity: 0.8;
        margin-top: var(--space-xs);
    }
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: currentColor;
    }
    .status-dot.active { background-color: var(--primary-color); }
    .status-dot.completed { background-color: #34a853; } /* зеленый, но приглушенный */
    .status-dot.pending { background-color: #9aa0a6; }   /* серый */

    /* Кнопки внутри карточек – минимализм */
    .phase-card .stButton button {
        background-color: transparent;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: var(--radius-md);
        color: var(--text-color);
        font-size: 0.8125rem;
        font-weight: 500;
        padding: var(--space-xs) var(--space-md);
        transition: var(--transition);
        width: 100%;
    }
    .phase-card .stButton button:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
        background-color: transparent;
    }

    /* ---------- Sidebar – чистая панель состояния ---------- */
    [data-testid="stSidebar"] {
        background-color: var(--background-color);
        border-right: 1px solid rgba(128, 128, 128, 0.08);
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: var(--text-color);
    }
    .sidebar-section {
        margin-bottom: var(--space-xl);
    }
    .sidebar-header {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 600;
        color: var(--text-color);
        opacity: 0.5;
        margin-bottom: var(--space-md);
    }
    .status-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--space-sm) 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.06);
        font-size: 0.875rem;
    }
    .status-label {
        display: flex;
        align-items: center;
        gap: var(--space-sm);
        color: var(--text-color);
        opacity: 0.8;
    }
    .status-value {
        font-weight: 500;
        color: var(--text-color);
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        background-color: rgba(128, 128, 128, 0.08);
        color: var(--text-color);
    }

    /* ---------- Переопределение стандартных Streamlit сообщений – нейтральные, без цвета ---------- */
    .stAlert {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid rgba(128, 128, 128, 0.08) !important;
        border-radius: 0 !important;
        padding: var(--space-sm) 0 !important;
        color: var(--text-color) !important;
    }
    .stAlert [data-testid="stAlertIcon"] {
        display: none;
    }
    .stAlert .stMarkdown {
        color: var(--text-color) !important;
        opacity: 0.8;
        font-size: 0.875rem;
    }
    div[data-baseweb="notification"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid rgba(128, 128, 128, 0.08) !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }

    /* ---------- Expander – чистый ---------- */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid rgba(128, 128, 128, 0.08) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: var(--text-color) !important;
        padding: var(--space-sm) 0 !important;
    }
    .streamlit-expanderContent {
        border: none !important;
        background-color: transparent !important;
        padding: var(--space-md) 0 !important;
    }

    /* ---------- Divider – тонкая линия ---------- */
    hr {
        margin: var(--space-xl) 0 !important;
        border: none !important;
        border-top: 1px solid rgba(128, 128, 128, 0.08) !important;
    }

    /* ---------- Блок AI – отдельный, но вписанный ---------- */
    .ai-card {
        background-color: var(--secondary-background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        margin-top: var(--space-lg);
    }
    .ai-card .stButton button {
        background-color: transparent;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: var(--radius-md);
        color: var(--text-color);
    }
    .ai-card .stButton button:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
    }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# Класс состояния – БЕЗ ИЗМЕНЕНИЙ
# =============================================================================
class AppState:
    def __init__(self):
        if 'current_phase' not in st.session_state:
            st.session_state.current_phase = 1
        if 'app_data' not in st.session_state:
            st.session_state.app_data = {
                'phase1': {},
                'phase2': {},
                'phase3': {},
                'phase4': {},
                'phase5': {},
                'phase6': {},
                'category': '',
                'project_name': 'Новый проект'
            }
        if 'phase6_auto_load' not in st.session_state:
            st.session_state.phase6_auto_load = True

    def get_phase_data(self, phase):
        return st.session_state.app_data.get(f'phase{phase}', {})

    def set_phase_data(self, phase, data):
        st.session_state.app_data[f'phase{phase}'] = data

    def get_all_data_for_phase3(self):
        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', '')
        }

    def get_all_data_for_phase4(self):
        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', '')
        }

    def get_all_data_for_phase5(self):
        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'phase4_data': st.session_state.app_data.get('phase4', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', '')
        }

    def get_all_data_for_phase6(self):
        phase5_data = self.get_phase_data(5)
        return {
            'phase1_data': st.session_state.app_data.get('phase1', {}),
            'phase2_data': st.session_state.app_data.get('phase2', {}),
            'phase4_data': st.session_state.app_data.get('phase4', {}),
            'phase5_data': phase5_data,
            'generation_results': phase5_data.get('results', {}),
            'generation_stats': phase5_data.get('statistics', {}),
            'generation_settings': phase5_data.get('generation_settings', {}),
            'category': st.session_state.app_data.get('category', ''),
            'project_name': st.session_state.app_data.get('project_name', ''),
            'total_prompts': phase5_data.get('statistics', {}).get('total', 0),
            'successful_generations': phase5_data.get('statistics', {}).get('success', 0)
        }


# =============================================================================
# Карточка фазы – обновленный дизайн, но логика прежняя
# =============================================================================
def show_phase_card(phase_num, title, description, icon, status="pending"):
    """Минималистичная карточка, статус отображается точкой."""
    status_dot_class = {
        "active": "active",
        "completed": "completed",
        "pending": "pending"
    }.get(status, "pending")

    # Кнопка "Перейти" показывается только если фаза активна?
    # В оригинале кнопка была внутри карточки только для активной фазы.
    # Оставляем как есть, но стилизуем.

    with st.container():
        st.markdown(f"""
        <div class="phase-card {status}">
            <div class="phase-header">
                <span class="phase-icon">{icon}</span>
                <span class="phase-title">Фаза {phase_num}: {title}</span>
            </div>
            <div class="phase-description">{description}</div>
            <div class="phase-status">
                <span class="status-dot {status_dot_class}"></span>
                <span>{status.capitalize()}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if status == "active":
            if st.button(f"Перейти", key=f"goto_phase_{phase_num}", use_container_width=True):
                st.session_state.current_phase = phase_num
                st.rerun()


# =============================================================================
# СТАРТОВЫЙ ЭКРАН (home)
# =============================================================================
def render_home():
    """Только стартовый экран с заголовком, описанием и кнопкой перехода."""
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("# Data Harvester Pro")
    st.markdown("""
    <p style="font-size: 1.2rem; opacity: 0.7; max-width: 600px; margin: 1.5rem auto;">
        Комплексная обработка данных и генерация промптов с AI
    </p>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Перейти к генерации", type="primary", use_container_width=True):
            st.session_state.app_mode = "generator"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# ОСНОВНОЙ ИНТЕРФЕЙС ГЕНЕРАТОРА (весь существующий UI)
# =============================================================================
def render_generator():
    """Полностью перенесённая логика исходного main().
       Добавлена кнопка '← Выйти в меню' в сайдбаре."""

    # Состояние для AI настроек – без изменений
    if 'show_ai_config' not in st.session_state:
        st.session_state.show_ai_config = False

    app_state = AppState()

    # =========================================================================
    # SIDEBAR – полностью переработан, стал компактным и чистым
    # =========================================================================
    with st.sidebar:
        st.markdown('<div class="sidebar-header">Статус передачи данных</div>', unsafe_allow_html=True)

        # Данные фаз в виде компактного списка
        phase1_data = app_state.get_phase_data(1)
        phase2_data = app_state.get_phase_data(2)
        phase4_data = app_state.get_phase_data(4)
        phase5_data = app_state.get_phase_data(5)
        phase6_data = app_state.get_phase_data(6)

        # Фаза 1
        with st.container():
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<span class="status-label">📦 Фаза 1</span>', unsafe_allow_html=True)
            with col2:
                if phase1_data:
                    st.markdown('<span class="status-badge">Готово</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-badge">Ожидание</span>', unsafe_allow_html=True)
            if phase1_data:
                st.caption(f"{phase1_data.get('category', '—')} · {len(phase1_data.get('characteristics', []))} хар.")

        # Фаза 2
        with st.container():
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<span class="status-label">🏷️ Фаза 2</span>', unsafe_allow_html=True)
            with col2:
                if phase2_data:
                    st.markdown('<span class="status-badge">Готово</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-badge">Ожидание</span>', unsafe_allow_html=True)
            if phase2_data:
                st.caption(f"{len(phase2_data.get('markers', []))} маркеров")

        # Фаза 3
        blocks_dir = Path("blocks")
        has_blocks = blocks_dir.exists() and any(blocks_dir.iterdir())
        with st.container():
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<span class="status-label">📝 Фаза 3</span>', unsafe_allow_html=True)
            with col2:
                if has_blocks:
                    st.markdown('<span class="status-badge">Готово</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-badge">Ожидание</span>', unsafe_allow_html=True)
            if has_blocks:
                block_count = len([d for d in blocks_dir.iterdir() if d.is_dir()])
                st.caption(f"{block_count} блоков")

        # Фаза 4
        with st.container():
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<span class="status-label">🚀 Фаза 4</span>', unsafe_allow_html=True)
            with col2:
                if phase4_data and phase4_data.get('prompts'):
                    st.markdown('<span class="status-badge">Готово</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-badge">Ожидание</span>', unsafe_allow_html=True)
            if phase4_data:
                st.caption(f"{len(phase4_data.get('prompts', []))} промптов")

        # Фаза 5
        with st.container():
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<span class="status-label">📄 Фаза 5</span>', unsafe_allow_html=True)
            with col2:
                if phase5_data and phase5_data.get('results'):
                    st.markdown('<span class="status-badge">Готово</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-badge">Ожидание</span>', unsafe_allow_html=True)
            if phase5_data:
                st.caption(f"{len(phase5_data.get('results', {}))} текстов")

        # Фаза 6
        with st.container():
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<span class="status-label">📊 Фаза 6</span>', unsafe_allow_html=True)
            with col2:
                if phase6_data and phase6_data.get('processed'):
                    st.markdown('<span class="status-badge">Готово</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-badge">Ожидание</span>', unsafe_allow_html=True)
            if phase6_data:
                st.caption("Обработано")

        st.divider()

        # ========== AI НАСТРОЙКИ (компактно) ==========
        st.markdown('<div class="sidebar-header">🤖 AI</div>', unsafe_allow_html=True)

        ai_config_file = Path("config/ai_config.json")
        has_ai_config = ai_config_file.exists()
        if has_ai_config:
            try:
                with open(ai_config_file, 'r', encoding='utf-8') as f:
                    ai_config = json.load(f)
                    provider = ai_config.get("default_provider", "openai")
                    provider_config = ai_config.get("providers", {}).get(provider, {})
                    api_key_set = bool(provider_config.get("api_key", ""))
                    if api_key_set:
                        st.markdown(f'<span class="status-badge">{provider.upper()} · Активен</span>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="status-badge">{provider.upper()} · Нет ключа</span>',
                                    unsafe_allow_html=True)
            except:
                st.markdown('<span class="status-badge">Ошибка конфига</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge">Не настроен</span>', unsafe_allow_html=True)

        if st.button("⚙️ Настроить AI", use_container_width=True):
            st.session_state.show_ai_config = True

        if st.session_state.get('show_ai_config', False):
            with st.expander("AI настройки открыты", expanded=True):
                st.caption("Используйте кнопку 'Закрыть' в основной области.")
                if st.button("← Закрыть", key="close_ai_sidebar", use_container_width=True):
                    st.session_state.show_ai_config = False
                    st.rerun()

        st.divider()

        # ========== БЫСТРЫЙ ПЕРЕХОД – selectbox вместо 7 кнопок ==========
        st.markdown('<div class="sidebar-header">⚡ Быстрый переход</div>', unsafe_allow_html=True)

        phase_options = {
            1: "Фаза 1: Сбор характеристик",
            2: "Фаза 2: Управление маркерами",
            3: "Фаза 3: Редактирование блоков",
            4: "Фаза 4: Генерация промптов",
            5: "Фаза 5: Генерация текстов",
            6: "Фаза 6: Анализ и экспорт"
        }
        selected_phase = st.selectbox(
            "Перейти к фазе",
            options=list(phase_options.keys()),
            format_func=lambda x: phase_options[x],
            index=st.session_state.current_phase - 1,
            label_visibility="collapsed"
        )
        if selected_phase != st.session_state.current_phase:
            st.session_state.current_phase = selected_phase
            st.rerun()

        # ========== КНОПКА ВЫХОДА В МЕНЮ ==========
        st.divider()
        if st.button("← Выйти в меню", use_container_width=True):
            st.session_state.app_mode = "home"
            st.rerun()

    # =========================================================================
    # ОСНОВНАЯ ОБЛАСТЬ – полная перестройка сетки фаз
    # =========================================================================
    # Заголовок приложения – убираем тяжелый градиент, оставляем минимализм
    st.markdown("""
    <div style="margin-bottom: var(--space-2xl);">
        <h1 style="margin-bottom: 4px;">Data Harvester Pro</h1>
        <p class="text-secondary" style="margin-top: 0;">Комплексная обработка данных и генерация промптов с AI</p>
    </div>
    """, unsafe_allow_html=True)

    # Если открыты настройки AI – показываем их и выходим
    if st.session_state.get('show_ai_config', False):
        st.markdown("---")
        st.markdown("### 🤖 Настройки AI")
        col_back1, col_back2 = st.columns([1, 5])
        with col_back1:
            if st.button("← Вернуться", use_container_width=True):
                st.session_state.show_ai_config = False
                st.rerun()
        try:
            from ai_config import show_ai_config_interface
            show_ai_config_interface()
        except ImportError:
            st.error("Модуль ai_config.py не найден.")
        except Exception as e:
            st.error(f"Ошибка загрузки настроек AI: {e}")
        return

    # ========== ЭТАПЫ ОБРАБОТКИ ДАННЫХ – новая сетка 3+3 ==========
    st.markdown("### 🎯 Этапы обработки данных")

    # Определяем статусы фаз (без изменений в логике)
    phase_status = {}
    for phase in [1, 2, 3, 4, 5, 6]:
        if phase == st.session_state.current_phase:
            phase_status[phase] = "active"
        elif phase == 3:
            blocks_dir = Path("blocks")
            has_blocks = blocks_dir.exists() and any(blocks_dir.iterdir())
            phase_status[phase] = "completed" if has_blocks else "pending"
        elif phase == 4:
            has_prompts = bool(st.session_state.app_data.get('phase4', {}).get('prompts', []))
            phase_status[phase] = "completed" if has_prompts else "pending"
        elif phase == 5:
            has_results = bool(st.session_state.app_data.get('phase5', {}).get('results', {}))
            phase_status[phase] = "completed" if has_results else "pending"
        elif phase == 6:
            phase6_data = app_state.get_phase_data(6)
            phase_status[phase] = "completed" if phase6_data else "pending"
        else:
            phase_status[phase] = "completed" if st.session_state.app_data.get(f'phase{phase}') else "pending"

    # Первый ряд: фазы 1-3
    col1, col2, col3 = st.columns(3)
    with col1:
        show_phase_card(1, "Сбор характеристик", "Загрузка и фильтрация характеристик товаров", "📦", phase_status[1])
    with col2:
        show_phase_card(2, "Управление маркерами", "Настройка ключевых слов для категорий", "🏷️", phase_status[2])
    with col3:
        show_phase_card(3, "Редактирование блоков", "Создание и настройка шаблонов промптов", "📝", phase_status[3])

    # Второй ряд: фазы 4-6
    col4, col5, col6 = st.columns(3)
    with col4:
        show_phase_card(4, "Генерация промптов", "Создание промптов для ИИ на основе данных", "🚀", phase_status[4])
    with col5:
        show_phase_card(5, "Генерация текстов", "Создание текстов через ИИ и форматирование", "📄", phase_status[5])
    with col6:
        show_phase_card(6, "Анализ и экспорт", "Анализ результатов и финальный экспорт", "📊", phase_status[6])

    st.divider()

    # ========== ТЕКУЩАЯ ФАЗА – отображение контента ==========
    st.markdown(f"### 🎮 Текущая фаза: {st.session_state.current_phase}")

    # Получаем данные (без изменений)
    phase1_data = app_state.get_phase_data(1)
    phase2_data = app_state.get_phase_data(2)
    phase4_data = app_state.get_phase_data(4)
    phase5_data = app_state.get_phase_data(5)

    # ========== ИНФОРМАЦИОННЫЕ БЛОКИ – теперь без визуального шума,
    # но логика полностью сохранена ==========
    if st.session_state.current_phase == 2 and phase1_data:
        st.info(
            f"📥 Данные из фазы 1: **{phase1_data.get('category', '—')}** ({len(phase1_data.get('characteristics', []))} характеристик)")

    elif st.session_state.current_phase == 3:
        if phase1_data and phase2_data:
            st.success(
                f"✅ Категория: {phase1_data.get('category', '—')} · {len(phase2_data.get('markers', []))} маркеров")
            st.caption("Фаза 3 поддерживает AI-генерацию инструкций. Настройте AI в боковой панели.")
        else:
            st.info("ℹ️ Фаза 3 работает независимо, но для тестирования нужны данные из фаз 1 и 2.")

    elif st.session_state.current_phase == 4:
        if phase1_data and phase2_data:
            st.success(
                f"✅ Данные готовы: {phase1_data.get('category', '—')}, {len(phase2_data.get('markers', []))} маркеров, {len(phase1_data.get('characteristics', []))} характеристик")
            # Проверка AI конфигурации
            ai_config_file = Path("config/ai_config.json")
            if ai_config_file.exists():
                try:
                    with open(ai_config_file, 'r', encoding='utf-8') as f:
                        ai_config = json.load(f)
                        provider = ai_config.get("default_provider", "openai")
                        provider_config = ai_config.get("providers", {}).get(provider, {})
                        if provider_config.get("api_key"):
                            st.info(f"🤖 AI: {provider.upper()} готов")
                        else:
                            st.warning(f"⚠️ Требуется API ключ для {provider}")
                except:
                    st.warning("⚠️ Ошибка AI конфигурации")
            else:
                st.info("ℹ️ AI не настроен. Используйте боковую панель.")

            try:
                import phase4
                phase4.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 4: {e}")
        else:
            st.warning("⚠️ Недостаточно данных: выполните фазы 1 и 2")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Фаза 1", use_container_width=True):
                    st.session_state.current_phase = 1
                    st.rerun()
            with col2:
                if st.button("← Фаза 2", use_container_width=True):
                    st.session_state.current_phase = 2
                    st.rerun()

    elif st.session_state.current_phase == 5:
        if phase1_data and phase2_data and phase4_data:
            st.success(
                f"✅ Все данные загружены: {phase1_data.get('category', '—')}, {len(phase4_data.get('prompts', []))} промптов")
            # Проверка AI
            ai_config_file = Path("config/ai_config.json")
            if ai_config_file.exists():
                try:
                    with open(ai_config_file, 'r', encoding='utf-8') as f:
                        ai_config = json.load(f)
                        provider = ai_config.get("default_provider", "openai")
                        provider_config = ai_config.get("providers", {}).get(provider, {})
                        if provider_config.get("api_key"):
                            st.info(f"🤖 AI: {provider.upper()} готов")
                        else:
                            st.warning(f"⚠️ Требуется API ключ для {provider}")
                except:
                    st.warning("⚠️ Ошибка AI конфигурации")
            else:
                st.info("ℹ️ AI не настроен. Настройте в боковой панели.")

            try:
                import phase5
                phase5.main()
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 5: {e}")
        else:
            st.warning("⚠️ Недостаточно данных: выполните фазы 1, 2 и 4")
            cols = st.columns(3)
            with cols[0]:
                if st.button("← Фаза 1", key="b1", use_container_width=True):
                    st.session_state.current_phase = 1
                    st.rerun()
            with cols[1]:
                if st.button("← Фаза 2", key="b2", use_container_width=True):
                    st.session_state.current_phase = 2
                    st.rerun()
            with cols[2]:
                if st.button("← Фаза 4", key="b4", use_container_width=True):
                    st.session_state.current_phase = 4
                    st.rerun()

    elif st.session_state.current_phase == 6:
        phase5_data = app_state.get_phase_data(5)
        if phase5_data:
            st.success(f"✅ Данные из фазы 5 получены")
            if not st.session_state.app_data.get('phase6'):
                phase6_input_data = {
                    'phase5_data': phase5_data,
                    'category': st.session_state.app_data.get('category', ''),
                    'project_name': st.session_state.app_data.get('project_name', ''),
                    'phase1_data': st.session_state.app_data.get('phase1', {}),
                    'phase2_data': st.session_state.app_data.get('phase2', {}),
                    'phase4_data': st.session_state.app_data.get('phase4', {})
                }
                app_state.set_phase_data(6, {
                    'input_data': phase6_input_data,
                    'processed': False,
                    'received_from_phase5': True,
                    'received_at': datetime.now().isoformat()
                })
                st.caption("📥 Данные автоматически переданы из фазы 5")

            try:
                import phase6
                phase6.main()
            except ImportError:
                with st.expander("⚠️ Фаза 6 не реализована"):
                    st.json(phase5_data)
            except Exception as e:
                st.error(f"Ошибка загрузки фазы 6: {e}")
        else:
            st.warning("⚠️ Для фазы 6 необходимо выполнить фазу 5")
            if st.button("← Фаза 5", use_container_width=True):
                st.session_state.current_phase = 5
                st.rerun()

    else:
        # Фаза 1 и другие – загружаем модули
        try:
            if st.session_state.current_phase == 1:
                import phase1
                phase1.main()
        except Exception as e:
            st.error(f"Ошибка загрузки фазы {st.session_state.current_phase}: {e}")

    # ========== НАВИГАЦИЯ (без изменений в логике) ==========
    st.divider()
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.session_state.current_phase > 1:
            if st.button("← Предыдущая фаза", use_container_width=True):
                st.session_state.current_phase -= 1
                st.rerun()
    with nav_col2:
        if st.session_state.current_phase < 6:
            if st.session_state.current_phase == 1:
                can_proceed = bool(phase1_data)
            elif st.session_state.current_phase == 2:
                can_proceed = bool(phase1_data and phase2_data)
            elif st.session_state.current_phase == 3:
                can_proceed = bool(phase1_data and phase2_data)
            elif st.session_state.current_phase == 4:
                can_proceed = bool(phase1_data and phase2_data and phase4_data)
            elif st.session_state.current_phase == 5:
                can_proceed = bool(phase5_data)
            else:
                can_proceed = True

            if can_proceed:
                if st.button("Следующая фаза →", type="primary", use_container_width=True):
                    st.session_state.current_phase += 1
                    st.rerun()
            else:
                st.caption("⚠️ Завершите текущую фазу")


# =============================================================================
# ТОЧКА ВХОДА (ROUTER)
# =============================================================================
def main():
    st.set_page_config(
        page_title="Data Harvester Pro",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    local_css()

    # Инициализация режима отображения
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = 'home'  # по умолчанию стартовый экран

    # Роутинг
    if st.session_state.app_mode == 'home':
        render_home()
    else:
        render_generator()


if __name__ == "__main__":
    main()