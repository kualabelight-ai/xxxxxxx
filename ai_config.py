import streamlit as st
from ai_module import AIConfigManager


def show_ai_config_interface():
    """Интерфейс для настройки параметров AI"""

    if 'ai_config_manager' not in st.session_state:
        st.session_state.ai_config_manager = AIConfigManager()

    config_manager = st.session_state.ai_config_manager

    st.title("⚙️ Настройки AI")
    st.markdown("---")

    # Выбор провайдера по умолчанию
    default_provider = st.selectbox(
        "Провайдер по умолчанию:",
        ["openai", "deepseek"],
        index=0 if config_manager.config["default_provider"] == "openai" else 1
    )

    if default_provider != config_manager.config["default_provider"]:
        config_manager.set_default_provider(default_provider)
        st.success(f"Провайдер по умолчанию изменен на {default_provider}")

    # Настройки для каждого провайдера
    tabs = st.tabs(["OpenAI", "DeepSeek"])

    for idx, provider in enumerate(["openai", "deepseek"]):
        with tabs[idx]:
            provider_config = config_manager.get_provider_config(provider)

            st.subheader(f"Настройки {provider.upper()}")

            # API ключ
            api_key = st.text_input(
                f"API ключ {provider}:",
                value=provider_config.get("api_key", ""),
                type="password",
                key=f"{provider}_api_key"
            )

            # Модель
            if provider == "openai":
                models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
            else:
                models = ["deepseek-chat", "deepseek-coder"]

            model = st.selectbox(
                "Модель:",
                models,
                index=models.index(provider_config.get("model", models[0])),
                key=f"{provider}_model"
            )

            # Параметры генерации
            col1, col2 = st.columns(2)

            with col1:
                temperature = st.slider(
                    "Temperature:",
                    min_value=0.0,
                    max_value=2.0,
                    value=float(provider_config.get("temperature", 0.7)),
                    step=0.1,
                    key=f"{provider}_temp"
                )

                max_tokens = st.number_input(
                    "Max Tokens:",
                    min_value=100,
                    max_value=8000,
                    value=int(provider_config.get("max_tokens", 2000)),
                    key=f"{provider}_tokens"
                )

            with col2:
                top_p = st.slider(
                    "Top P:",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(provider_config.get("top_p", 0.9)),
                    step=0.01,
                    key=f"{provider}_top_p"
                )

                frequency_penalty = st.slider(
                    "Frequency Penalty:",
                    min_value=-2.0,
                    max_value=2.0,
                    value=float(provider_config.get("frequency_penalty", 0.0)),
                    step=0.1,
                    key=f"{provider}_freq"
                )

                presence_penalty = st.slider(
                    "Presence Penalty:",
                    min_value=-2.0,
                    max_value=2.0,
                    value=float(provider_config.get("presence_penalty", 0.0)),
                    step=0.1,
                    key=f"{provider}_pres"
                )

            # Настройки rate limit
            st.subheader("Ограничения запросов")
            col_r1, col_r2 = st.columns(2)

            with col_r1:
                delay = st.number_input(
                    "Задержка между запросами (сек):",
                    min_value=0.5,
                    max_value=10.0,
                    value=float(config_manager.config["rate_limit"]["delay_between_requests"]),
                    step=0.5,
                    key=f"{provider}_delay"
                )

            with col_r2:
                requests_per_minute = st.number_input(
                    "Запросов в минуту:",
                    min_value=1,
                    max_value=60,
                    value=int(config_manager.config["rate_limit"]["requests_per_minute"]),
                    key=f"{provider}_rpm"
                )

            # Кнопка сохранения
            if st.button(f"💾 Сохранить настройки {provider}", key=f"save_{provider}"):
                new_config = {
                    "api_key": api_key,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "frequency_penalty": frequency_penalty,
                    "presence_penalty": presence_penalty
                }

                if config_manager.update_provider_config(provider, new_config):
                    # Обновляем rate limit
                    config_manager.config["rate_limit"]["delay_between_requests"] = delay
                    config_manager.config["rate_limit"]["requests_per_minute"] = requests_per_minute
                    config_manager.save_config()

                    st.success(f"Настройки {provider} сохранены!")
                else:
                    st.error(f"Ошибка сохранения настроек {provider}")

    # Информация о доступных плейсхолдерах
    with st.expander("📋 Доступные плейсхолдеры для промптов"):
        st.markdown("""
        **Для характеристик:**
        - `{категория}` - название категории товара
        - `{характеристика}` - название характеристики
        - `{значение}` - значение характеристики (только для unique)
        - `{тип}` - тип характеристики (regular/unique)

        **Для других блоков:**
        - `{категория}` - название категории товара
        - `{маркер}` - маркер из фазы 2
        - `{маркер_заголовка}` - маркер для заголовка
        - `{маркер_описания}` - маркер для описания

        **Пример промпта для характеристики:**
        ```
        Сгенерируй линейный перечень (8-12 пунктов) обобщённых аналитических тезисов-вопросов, разделённых “;”, 
        для глубокого инженерно-технического анализа заданной ХАРАКТЕРИСТИКИ в рамках указанной КАТЕГОРИИ продукции.

        Категория: {категория}
        Характеристика: {характеристика}

        Каждый тезис должен начинаться с глагола-запроса (опиши, укажи, поясни, объясни, покажи, расскажи, оцени, сравни, определи).
        ```
        """)

    # Тестовый вызов API
    with st.expander("🧪 Тестовый вызов API"):
        test_prompt = st.text_area(
            "Тестовый промпт:",
            value="Привет! Ответь одним предложением.",
            height=100
        )

        if st.button("Отправить тестовый запрос"):
            from ai_module import AIGenerator
            ai_generator = AIGenerator(config_manager)

            with st.spinner("Отправка запроса..."):
                result = ai_generator.generate_instruction(
                    test_prompt,
                    {},
                    provider=default_provider,
                    num_variants=1
                )[0]

                if result["success"]:
                    st.success("✅ Запрос успешен!")
                    st.text_area("Ответ AI:", value=result["text"], height=150)

                    if "usage" in result:
                        usage = result["usage"]
                        st.caption(
                            f"Токены: {usage.get('total_tokens', 0)} (prompt: {usage.get('prompt_tokens', 0)}, completion: {usage.get('completion_tokens', 0)})")
                else:
                    st.error(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")


if __name__ == "__main__":
    show_ai_config_interface()