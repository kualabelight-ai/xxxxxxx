import streamlit as st
from pathlib import Path

# ---------- Единая дизайн-система (копия из main_app) ----------
def local_css():
    st.markdown("""
    <style>
    :root {
        --font-sans: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        --space-xs: 4px; --space-sm: 8px; --space-md: 16px; --space-lg: 24px; --space-xl: 32px; --space-2xl: 48px;
        --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-xl: 16px;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.02); --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.02), 0 2px 4px -1px rgba(0,0,0,0.01);
        --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.02), 0 4px 6px -2px rgba(0,0,0,0.01);
        --transition: all 0.2s cubic-bezier(0.2,0,0,1);
    }
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
        font-family: var(--font-sans);
        -webkit-font-smoothing: antialiased;
    }
    /* Карточка приложения – полный аналог .phase-card */
    .app-card {
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
    .app-card:hover {
        border-color: rgba(128,128,128,0.1);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    .app-icon {
        font-size: 2rem;
        margin-bottom: var(--space-sm);
    }
    .app-title {
        font-weight: 600;
        font-size: 1.2rem;
        color: var(--text-color);
        margin-bottom: var(--space-xs);
    }
    .app-description {
        font-size: 0.875rem;
        color: var(--text-color);
        opacity: 0.65;
        margin-bottom: var(--space-md);
        flex: 1;
    }
    .app-card .stButton button {
        background-color: transparent;
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: var(--radius-md);
        color: var(--text-color);
        font-size: 0.8125rem;
        font-weight: 500;
        padding: var(--space-xs) var(--space-md);
        transition: var(--transition);
        width: 100%;
    }
    .app-card .stButton button:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
        background-color: transparent;
    }
    h1, h2, h3 {
        font-weight: 500;
        letter-spacing: -0.01em;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------- Конфигурация приложений (легко расширяется) ----------
APPS = [
    {
        "name": "Data Harvester Pro",
        "icon": "📦",
        "desc": "Комплексная обработка данных, генерация промптов и текстов с AI",
        "page": "DataHarv",          # только имя файла, без параметров
        "start_mode": "generator"       # какой режим включить при запуске
    },
    # Добавляйте новые приложения аналогично
    # {
    #     "name": "Другое приложение",
    #     "icon": "🔬",
    #     "desc": "Описание",
    #     "page": "other_app.py",
    #     "start_mode": None            # или другой режим, если нужно
    # },
]

# ---------- Отрисовка сетки карточек ----------
def render_app_grid():
    st.markdown("# 🚀 Лаунчер приложений")
    st.markdown("""
    <p style="font-size: 1.1rem; opacity: 0.7; max-width: 600px; margin-bottom: 2rem;">
        Выберите приложение для запуска
    </p>
    """, unsafe_allow_html=True)

    cols_per_row = 3
    for i in range(0, len(APPS), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, app in zip(cols, APPS[i:i+cols_per_row]):
            with col:
                with st.container():
                    st.markdown(f"""
                    <div class="app-card">
                        <div class="app-icon">{app['icon']}</div>
                        <div class="app-title">{app['name']}</div>
                        <div class="app-description">{app['desc']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    # Кнопка запуска – переключение на страницу через switch_page
                    if st.button("🚀 Запустить", key=f"btn_{app['name']}", use_container_width=True):
                        # Передаём режим запуска через session_state
                        if app.get("start_mode"):
                            st.session_state.launcher_start_mode = app["start_mode"]
                        st.switch_page(app["page"])

# ---------- Точка входа ----------
def main():
    st.set_page_config(
        page_title="Лаунчер приложений",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    local_css()
    render_app_grid()

if __name__ == "__main__":
    main()