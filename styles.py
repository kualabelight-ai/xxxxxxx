# styles.py
import streamlit as st

def load_css():
    st.markdown("""
    <style>
        /* ========== БАЗОВАЯ РЕТРО-ТЕМА ========== */
        .stApp {
            background-color: #faf7f2;
            color: #3e3a36;
        }

        /* Типографика */
        h1, h2, h3, h4, h5, h6, .stMarkdown, .stText, label, span, p, div {
            color: #5e4b3c !important;
            font-family: 'Courier New', monospace !important;
        }

        /* ========== КНОПКИ ========== */
        .stButton > button {
            background-color: #e6dacd !important;
            color: #4a3f38 !important;
            border: 1px solid #b7a99a !important;
            border-radius: 6px !important;
            font-size: 14px !important;
            padding: 4px 12px !important;
            font-family: 'Courier New', monospace !important;
            box-shadow: none !important;
            transition: 0.2s !important;
        }
        .stButton > button:hover {
            background-color: #d4c3b2 !important;
            border-color: #8c7a6a !important;
            color: #2d2a24 !important;
        }
        .stButton > button:active {
            background-color: #c6b2a0 !important;
        }

        /* Маленькие кнопки (для инлайн использования) */
        .stButton.small-button > button {
            padding: 2px 8px !important;
            font-size: 12px !important;
        }

        /* ========== ПОЛЯ ВВОДА ========== */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > textarea,
        .stSelectbox > div > div > select,
        .stMultiselect > div > div,
        .stDateInput > div > div > input,
        .stTimeInput > div > div > input {
            background-color: #fffbf5 !important;
            border: 1px solid #d4c3a2 !important;
            border-radius: 4px !important;
            color: #3e3a36 !important;
            font-family: 'Courier New', monospace !important;
        }

        /* ========== ЧЕКБОКСЫ / РАДИО ========== */
        .stCheckbox > label,
        .stRadio > label {
            color: #5e4b3c !important;
            font-family: 'Courier New', monospace !important;
        }

        /* ========== СЛАЙДЕРЫ ========== */
        .stSlider > div > div > div {
            background-color: #d4c3a2 !important;
        }

        /* ========== ТАБЛИЦЫ / DATAFRAME ========== */
        .stDataFrame {
            font-family: 'Courier New', monospace !important;
        }
        .stDataFrame table {
            border-collapse: collapse !important;
            width: 100% !important;
        }
        .stDataFrame th {
            background-color: #e6dacd !important;
            color: #4a3f38 !important;
            border: 1px solid #b7a99a !important;
            padding: 6px !important;
            font-weight: bold !important;
        }
        .stDataFrame td {
            background-color: #fffbf5 !important;
            border: 1px solid #d4c3a2 !important;
            padding: 4px !important;
            color: #3e3a36 !important;
        }

        /* ========== ИНДИКАТОРЫ ========== */
        div.stAlert {
            background-color: #f0ebe4 !important;
            border-left: 4px solid #b08968 !important;
            color: #3e3a36 !important;
            border-radius: 0 !important;
            padding: 1rem !important;
        }
        div.stSuccess {
            background-color: #e6f0da !important;
            border-left: 4px solid #7f9f6f !important;
        }
        div.stWarning {
            background-color: #fff1d6 !important;
            border-left: 4px solid #e6b89c !important;
        }
        div.stInfo {
            background-color: #e1e7e0 !important;
            border-left: 4px solid #8d9f87 !important;
        }
        div.stError {
            background-color: #f4dbd6 !important;
            border-left: 4px solid #c45a4a !important;
        }

        /* ========== ВКЛАДКИ (TABS) ========== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px !important;
            background-color: #f0ebe4 !important;
            border-bottom: 1px solid #d4c3a2 !important;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #e6dacd !important;
            border-radius: 4px 4px 0 0 !important;
            padding: 6px 12px !important;
            font-size: 13px !important;
            color: #4a3f38 !important;
            border: 1px solid #d4c3a2 !important;
            border-bottom: none !important;
            margin-right: 2px !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #d4c3b2 !important;
            color: #2d2a24 !important;
            border-bottom: 1px solid #d4c3b2 !important;
        }

        /* ========== ЭКСПАНДЕРЫ ========== */
        .streamlit-expanderHeader {
            background-color: #e6dacd !important;
            color: #4a3f38 !important;
            border: 1px solid #b7a99a !important;
            border-radius: 4px !important;
            font-family: 'Courier New', monospace !important;
        }
        .streamlit-expanderContent {
            background-color: #fffbf5 !important;
            border: 1px solid #d4c3a2 !important;
            border-top: none !important;
            border-radius: 0 0 4px 4px !important;
        }

        /* ========== СПИННЕР / ПРОГРЕСС ========== */
        .stSpinner > div {
            border-color: #b08968 !important;
        }

        /* ========== ЛИНИИ, РАЗДЕЛИТЕЛИ ========== */
        hr {
            border-top: 1px solid #d4c3a2 !important;
            margin-top: 1rem !important;
            margin-bottom: 1rem !important;
        }

        /* ========== ОТСТУПЫ КОНТЕЙНЕРА ========== */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
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

        /* ========== КАРТОЧКИ ФАЗ (ЕСЛИ ИСПОЛЬЗУЮТСЯ) ========== */
        .phase-card {
            background-color: white;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            border: 1px solid #e0e0e0;
            transition: all 0.2s ease;
        }
        .phase-card:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .phase-active {
            border-left: 5px solid #b08968;
            background-color: #fbf7f0;
        }
        .phase-completed {
            border-left: 5px solid #7f9f6f;
        }
        .phase-pending {
            border-left: 5px solid #d4c3a2;
            opacity: 0.8;
        }
        span[data-testid="stIconMaterial"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            width: 0 !important;
            height: 0 !important;
            position: absolute !important;
            left: -9999px !important;
        }
        
        /* 2. Скрываем родительскую кнопку (на всякий случай) */
        button[data-testid="collapsedControl"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
        }
        
        /* 2. Скрываем сам сайдбар */
        section[data-testid="stSidebar"] + div {
            margin-left: 0 !important;
        }
        
        /* 4. Полное уничтожение левого отступа у главного контейнера */
        .main > div {
            padding-left: 0 !important;
            margin-left: 0 !important;
        }
        
        /* ========== СКРЫВАЕМ ВЕРХНЮЮ ПАНЕЛЬ STREAMLIT ========== */
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        /* ========== ОБНУЛЯЕМ ВЕРХНИЙ ОТСТУП ========== */
        .block-container {
            padding-top: 0rem !important;
        }
        /* ========== КОМПАКТНЫЕ КАРТОЧКИ ХАРАКТЕРИСТИК ========== */
        .characteristic-container {
            padding: 8px 12px !important;
            margin-bottom: 6px !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
        }
        .characteristic-container .stCheckbox label {
            font-size: 13px !important;
        }
        .characteristic-container .stRadio div[role="radiogroup"] {
            gap: 4px !important;
            flex-wrap: nowrap !important;
        }
        .characteristic-container .stRadio label {
            padding: 2px 8px !important;
            font-size: 12px !important;
            background: #f3eee8;
            border-radius: 12px;
            border: 1px solid transparent;
        }
        .characteristic-container .stRadio label:hover {
            background: #e6dacd;
            border-color: #b7a99a;
        }
        .characteristic-container .stRadio label[data-checked="true"] {
            background: #d4c3b2;
            border-color: #8c7a6a;
        }
        .characteristic-container .stNumberInput input {
            padding: 2px 6px !important;
            font-size: 12px !important;
            width: 60px !important;
        }
        .characteristic-container .stMultiselect div[data-baseweb="select"] {
            min-height: 24px !important;
            font-size: 12px !important;
        }
        .characteristic-container::after {
            content: '';
            display: block;
            height: 1px;
            background: linear-gradient(90deg, transparent 0%, rgba(0,0,0,0.1) 20%, rgba(0,0,0,0.1) 80%, transparent 100%);
            margin-top: 16px;
            margin-bottom: 0;
        }
                
        /* Кнопка-иконка раскрытия */
        .compact-expand-btn {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 4px !important;
            margin: 0 !important;
            color: #8c7a6a !important;
            font-size: 18px !important;
            line-height: 1 !important;
            min-width: 28px !important;
            transition: color 0.1s !important;
        }
        .compact-expand-btn:hover {
            color: #4a3f38 !important;
            background: rgba(0,0,0,0.02) !important;
        }
        .compact-expand-btn p {
            font-size: 18px !important;
            margin: 0 !important;
        }
        
        /* Дополнительная панель (скрыта по умолчанию, показывается по клику) */
        .compact-details-panel {
            background-color: #faf7f2;
            border-top: 1px dashed #d4c3a2;
            margin-top: 10px;
            padding-top: 12px;
        }
                           
         
    </style>
    """, unsafe_allow_html=True)