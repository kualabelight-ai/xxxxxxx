# styles.py
import streamlit as st

def load_css():
    st.markdown("""
    <style>
        /* ========== БАЗОВЫЙ МИНИМАЛИСТИЧНЫЙ СТИЛЬ ========== */
        .stApp {
            background-color: #ffffff;
            color: #1e1e1e;
        }

        /* Типографика */
        h1, h2, h3, h4, h5, h6, .stMarkdown, .stText, label, span, p, div {
            color: #1e1e1e !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
            line-height: 1.5;
        }

        h1 { font-size: 2rem; font-weight: 500; margin-bottom: 1rem; }
        h2 { font-size: 1.5rem; font-weight: 500; margin-bottom: 0.75rem; }
        h3 { font-size: 1.25rem; font-weight: 500; margin-bottom: 0.5rem; }

        /* ========== КНОПКИ ========== */
        .stButton > button {
            background-color: #f5f5f5 !important;
            color: #1e1e1e !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 6px !important;
            font-size: 14px !important;
            padding: 6px 16px !important;
            font-family: inherit !important;
            font-weight: 400 !important;
            transition: all 0.15s ease !important;
            box-shadow: none !important;
        }
        .stButton > button:hover {
            background-color: #e9e9e9 !important;
            border-color: #cccccc !important;
            color: #000000 !important;
        }
        .stButton > button:active {
            background-color: #d0d0d0 !important;
        }
        .stButton > button:focus {
            box-shadow: 0 0 0 2px rgba(59, 110, 156, 0.3) !important;
            outline: none !important;
        }

        /* Маленькие кнопки (для инлайн использования) */
        .stButton.small-button > button {
            padding: 2px 10px !important;
            font-size: 12px !important;
        }

        /* ========== ПОЛЯ ВВОДА ========== */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > textarea,
        .stSelectbox > div > div > div,
        .stMultiselect > div > div,
        .stDateInput > div > div > input,
        .stTimeInput > div > div > input {
            background-color: #ffffff !important;
            border: 1px solid #d1d1d1 !important;
            border-radius: 4px !important;
            color: #1e1e1e !important;
            font-family: inherit !important;
            padding: 0.5rem 0.75rem !important;
            box-shadow: none !important;
        }
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stTextArea > div > textarea:focus {
            border-color: #3b6e9c !important;
            box-shadow: 0 0 0 2px rgba(59, 110, 156, 0.2) !important;
            outline: none !important;
        }

        /* ========== ЧЕКБОКСЫ / РАДИО ========== */
           
        .stCheckbox > label,
        .stRadio > label {
            color: #5e4b3c !important;
            font-family: 'Courier New', monospace !important;
        }

        /* ========== СЛАЙДЕРЫ ========== */
        .stSlider > div > div > div {
            background-color: #3b6e9c !important;
        }
        .stSlider > div > div > div > div {
            background-color: #3b6e9c !important;
        }

        /* ========== ТАБЛИЦЫ / DATAFRAME ========== */
        .stDataFrame {
            font-family: inherit !important;
            font-size: 0.9rem !important;
        }
        .stDataFrame table {
            border-collapse: collapse !important;
            width: 100% !important;
            border: none !important;
        }
        .stDataFrame th {
            background-color: #f5f5f5 !important;
            color: #1e1e1e !important;
            border-bottom: 2px solid #e0e0e0 !important;
            border-top: none !important;
            border-left: none !important;
            border-right: none !important;
            padding: 0.75rem 0.5rem !important;
            font-weight: 600 !important;
            text-align: left !important;
        }
        .stDataFrame td {
            background-color: #ffffff !important;
            border-bottom: 1px solid #f0f0f0 !important;
            border-top: none !important;
            border-left: none !important;
            border-right: none !important;
            padding: 0.5rem !important;
            color: #1e1e1e !important;
        }

        /* ========== ИНДИКАТОРЫ ========== */
        div.stAlert, div.stSuccess, div.stWarning, div.stInfo, div.stError {
            background-color: #f9f9f9 !important;
            border-left: 4px solid #3b6e9c !important;
            color: #1e1e1e !important;
            border-radius: 0 !important;
            padding: 1rem !important;
            margin: 1rem 0 !important;
            font-family: inherit !important;
            box-shadow: none !important;
        }
        div.stSuccess { border-left-color: #2e7d32 !important; }
        div.stWarning { border-left-color: #f9a825 !important; }
        div.stInfo { border-left-color: #0288d1 !important; }
        div.stError { border-left-color: #c62828 !important; }

        /* ========== ВКЛАДКИ (TABS) ========== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0 !important;
            background-color: transparent !important;
            border-bottom: 1px solid #e0e0e0 !important;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
            border-bottom: 2px solid transparent !important;
            border-radius: 0 !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.9rem !important;
            color: #5f5f5f !important;
            margin-right: 0 !important;
            transition: all 0.15s ease !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #1e1e1e !important;
            border-bottom-color: #c0c0c0 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #1e1e1e !important;
            border-bottom-color: #3b6e9c !important;
            font-weight: 500 !important;
        }

        /* ========== ЭКСПАНДЕРЫ ========== */
        .streamlit-expanderHeader {
            background-color: #f9f9f9 !important;
            color: #1e1e1e !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 4px !important;
            font-family: inherit !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
        }
        .streamlit-expanderHeader:hover {
            background-color: #f0f0f0 !important;
        }
        .streamlit-expanderContent {
            background-color: #ffffff !important;
            border: 1px solid #e0e0e0 !important;
            border-top: none !important;
            border-radius: 0 0 4px 4px !important;
            padding: 1rem !important;
        }

        /* ========== СПИННЕР / ПРОГРЕСС ========== */
        .stSpinner > div {
            border-color: #3b6e9c !important;
            border-top-color: transparent !important;
        }

        /* ========== ЛИНИИ, РАЗДЕЛИТЕЛИ ========== */
        hr {
            border: none !important;
            border-top: 1px solid #eaeaea !important;
            margin: 1.5rem 0 !important;
        }

        /* ========== ОТСТУПЫ КОНТЕЙНЕРА ========== */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
        }

        /* ========== УБИРАЕМ ЛИШНИЕ ТЕНИ И ГРАДИЕНТЫ ========== */
        .st-bs, .st-br, .st-cj, .st-b7, .st-dg {
            box-shadow: none !important;
            background-image: none !important;
        }

        /* ========== КОМПАКТНЫЕ КОЛОНКИ ========== */
        div[data-testid="column"] {
            min-width: 0 !important;
            overflow: visible !important;
        }

        /* ========== КАРТОЧКИ ФАЗ ========== */
        .phase-card {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin: 0.5rem 0;
            border: 1px solid #f0f0f0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
            transition: box-shadow 0.15s ease;
        }
        .phase-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        }
        .phase-active {
            border-left: 4px solid #3b6e9c;
        }
        .phase-completed {
            border-left: 4px solid #2e7d32;
        }
        .phase-pending {
            border-left: 4px solid #b0b0b0;
            opacity: 0.9;
        }

        /* ========== СКРЫВАЕМ ЛИШНИЕ ЭЛЕМЕНТЫ STREAMLIT ========== */
        span[data-testid="stIconMaterial"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            width: 0 !important;
            height: 0 !important;
            position: absolute !important;
            left: -9999px !important;
        }
        button[data-testid="collapsedControl"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
        }
        section[data-testid="stSidebar"] + div {
            margin-left: 0 !important;
        }
        .main > div {
            padding-left: 0 !important;
            margin-left: 0 !important;
        }
        header[data-testid="stHeader"] {
            display: none !important;
        }
        .block-container {
            padding-top: 0rem !important;
        }

        /* ========== КОМПАКТНЫЕ КАРТОЧКИ ХАРАКТЕРИСТИК ========== */
        .characteristic-container {
            padding: 0.75rem 1rem !important;
            margin-bottom: 0.5rem !important;
            border-radius: 6px !important;
            background-color: #fafafa;
            border: 1px solid #f0f0f0;
            transition: all 0.15s ease !important;
        }
        .characteristic-container .stCheckbox label {
            font-size: 0.9rem !important;
        }
        .characteristic-container .stRadio div[role="radiogroup"] {
            gap: 0.25rem !important;
            flex-wrap: nowrap !important;
        }
        .characteristic-container .stRadio label {
            padding: 0.25rem 0.75rem !important;
            font-size: 0.8rem !important;
            background: #f0f0f0;
            border-radius: 16px;
            border: 1px solid transparent;
            transition: all 0.1s ease;
        }
        .characteristic-container .stRadio label:hover {
            background: #e0e0e0;
        }
        .characteristic-container .stRadio label[data-checked="true"] {
            background: #3b6e9c;
            border-color: #3b6e9c;
            color: white !important;
        }
        .characteristic-container .stNumberInput input {
            padding: 0.2rem 0.5rem !important;
            font-size: 0.8rem !important;
            width: 70px !important;
        }
        .characteristic-container .stMultiselect div[data-baseweb="select"] {
            min-height: 30px !important;
            font-size: 0.8rem !important;
        }
        .characteristic-container::after {
            content: '';
            display: block;
            height: 1px;
            background: linear-gradient(90deg, transparent, #eaeaea, transparent);
            margin-top: 1rem;
            margin-bottom: 0;
        }

        /* Кнопка-иконка раскрытия */
        .compact-expand-btn {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 0.25rem !important;
            margin: 0 !important;
            color: #7a7a7a !important;
            font-size: 1.2rem !important;
            line-height: 1 !important;
            min-width: 28px !important;
            transition: color 0.1s !important;
        }
        .compact-expand-btn:hover {
            color: #1e1e1e !important;
            background: transparent !important;
        }
        .compact-expand-btn p {
            font-size: 1.2rem !important;
            margin: 0 !important;
        }

        /* Дополнительная панель (скрыта по умолчанию, показывается по клику) */
        .compact-details-panel {
            background-color: #fafafa;
            border-top: 1px dashed #e0e0e0;
            margin-top: 0.75rem;
            padding-top: 0.75rem;
        }

    </style>
    """, unsafe_allow_html=True)