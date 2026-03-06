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
    available_providers = ["openai", "deepseek", "genapi_gemini", "true_gemini"]
    current_default = config_manager.config.get("default_provider", "deepseek")

    default_provider = st.selectbox(
        "Провайдер по умолчанию:",
        available_providers,
        index=available_providers.index(current_default) if current_default in available_providers else 1
    )

    if default_provider != config_manager.config["default_provider"]:
        config_manager.set_default_provider(default_provider)
        st.success(f"Провайдер по умолчанию изменен на {default_provider}")

    # Настройки для каждого провайдера
    providers = ["openai", "deepseek", "genapi_gemini", "true_gemini"]

    # Создаём вкладки с красивыми названиями
    tabs = st.tabs([p.replace("_", " ").title() for p in providers])

    for idx, provider in enumerate(providers):
        with tabs[idx]:
            provider_config = config_manager.get_provider_config(provider) or {}

            st.subheader(f"Настройки {provider.upper().replace('_', ' ')}")

            # API ключ
            api_key = st.text_input(
                f"API ключ {provider}:",
                value=provider_config.get("api_key", ""),
                type="password",
                key=f"{provider}_api_key"
            )

            # Выбор модели — в зависимости от провайдера
            if provider == "openai":
                models = ["gpt-4o-mini", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
            elif provider == "deepseek":
                models = ["deepseek-chat", "deepseek-coder"]
            elif provider == "genapi_gemini":
                models = [
                    "gemini-2-5-flash-lite",
                    "gemini-2-5-flash",
                    "gemini-3-1-pro",
                    "gemini-flash-image"
                ]
            elif provider == "true_gemini":
                models = [
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-1.5-pro",
                    "gemini-1.5-flash"
                ]
            else:
                models = ["неизвестный провайдер"]

            model = st.selectbox(
                "Модель:",
                models,
                index=models.index(provider_config.get("model", models[0]))
                if provider_config.get("model") in models else 0,
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
                    max_value=16384,  # для новых Gemini можно больше
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

                # Для true_gemini frequency/presence не влияют → отключаем
                freq_disabled = (provider == "true_gemini")
                frequency_penalty = st.slider(
                    "Frequency Penalty:",
                    min_value=-2.0,
                    max_value=2.0,
                    value=float(provider_config.get("frequency_penalty", 0.0)),
                    step=0.1,
                    disabled=freq_disabled,
                    key=f"{provider}_freq"
                )

                presence_penalty = st.slider(
                    "Presence Penalty:",
                    min_value=-2.0,
                    max_value=2.0,
                    value=float(provider_config.get("presence_penalty", 0.0)),
                    step=0.1,
                    disabled=freq_disabled,
                    key=f"{provider}_pres"
                )

            # Специфические поля для отдельных провайдеров
            extra_config = {}
            if provider == "genapi_gemini":
                is_sync = st.checkbox(
                    "Синхронный режим (is_sync = true)",
                    value=provider_config.get("is_sync", True),
                    key=f"{provider}_is_sync"
                )
                extra_config["is_sync"] = is_sync

            if provider == "true_gemini":
                st.caption("⚠️ Для работы из России обычно нужен VPN или прокси-сервер")

            # Ограничения запросов — общие для всех
            st.subheader("Ограничения запросов (общие)")
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
            if st.button(f"💾 Сохранить настройки {provider.upper().replace('_', ' ')}", key=f"save_{provider}"):
                new_config = {
                    "api_key": api_key.strip(),
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "frequency_penalty": frequency_penalty if not freq_disabled else 0.0,
                    "presence_penalty": presence_penalty if not freq_disabled else 0.0,
                    **extra_config
                }

                if config_manager.update_provider_config(provider, new_config):
                    # Сохраняем общий rate limit (перезаписывается при любом сохранении)
                    config_manager.config["rate_limit"]["delay_between_requests"] = delay
                    config_manager.config["rate_limit"]["requests_per_minute"] = requests_per_minute
                    config_manager.save_config()
                    st.success(f"Настройки {provider} сохранены!")
                else:
                    st.error(f"Ошибка при сохранении настроек {provider}")

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

        # Добавляем выбор провайдера специально для теста
        test_provider = st.selectbox(
            "Провайдер для теста:",
            available_providers,
            index=available_providers.index(default_provider),
            key="test_provider_select"
        )

        if st.button("Отправить тестовый запрос"):
            from ai_module import AIGenerator
            ai_generator = AIGenerator(config_manager)

            with st.spinner("Отправка запроса..."):
                result = ai_generator.generate_instruction(
                    test_prompt,
                    {},
                    provider=test_provider,  # ← теперь берём из этого selectbox
                    num_variants=1
                )[0]

                if result["success"]:
                    st.success("✅ Запрос успешен!")
                    st.text_area("Ответ AI:", value=result["text"], height=150)
                    if "usage" in result:
                        usage = result["usage"]
                        st.caption(
                            f"Токены: {usage.get('total_tokens', 0)} "
                            f"(prompt: {usage.get('prompt_tokens', 0)}, "
                            f"completion: {usage.get('completion_tokens', 0)})"
                        )
                else:
                    st.error(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")


if __name__ == "__main__":
    show_ai_config_interface()