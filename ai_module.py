import json
import os
import re
import time
from typing import Dict, List, Optional, Any
import httpx
from openai import OpenAI
import streamlit as st
import requests
import re


class AIConfigManager:
    """Менеджер настроек AI"""

    def __init__(self, config_file="config/ai_config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Загружает конфигурацию AI из файла"""
        default_config = {
            "providers": {
                "openai": {
                    "api_key": "",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                },
                "deepseek": {
                    "api_key": "",
                    "model": "deepseek-chat",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                },
                "genapi_gemini": {
                    "api_key": "",
                    "model": "gemini-2-5-flash-lite",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0,
                    "is_sync": True,
                    "stream": False
                },
                "true_gemini": {
                    "api_key": "",  # AI Studio / Google API key
                    "model": "gemini-2.5-flash",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9
                    # frequency/presence не поддерживаются → не добавляем
                }
            },
            "default_provider": "openai",
            "rate_limit": {
                "requests_per_minute": 30,
                "delay_between_requests": 2.0
            }
        }

        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Объединяем с дефолтными настройками
                    self.merge_configs(default_config, loaded_config)
            else:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"Ошибка загрузки конфига AI: {e}")

        return default_config

    def merge_configs(self, default: Dict, loaded: Dict) -> None:
        """Рекурсивно объединяет конфиги"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self.merge_configs(default[key], value)
                else:
                    default[key] = value

    def save_config(self) -> bool:
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Ошибка сохранения конфига AI: {e}")
            return False

    def get_provider_config(self, provider: str) -> Dict:
        """Возвращает конфигурацию для провайдера"""
        return self.config["providers"].get(provider, {})

    def update_provider_config(self, provider: str, config: Dict) -> bool:
        """Обновляет конфигурацию провайдера"""
        self.config["providers"][provider] = config
        return self.save_config()

    def set_default_provider(self, provider: str) -> bool:
        """Устанавливает провайдера по умолчанию"""
        self.config["default_provider"] = provider
        return self.save_config()


class AIGenerator:
    """Генератор инструкций через AI API"""

    def __init__(self, config_manager: AIConfigManager):
        self.config_manager = config_manager
        self.rate_limit_delay = config_manager.config["rate_limit"]["delay_between_requests"]
        self.last_request_time = 0

    def _rate_limit(self):
        """Ограничение частоты запросов"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _prepare_prompt(self, prompt_template: str, context: Dict) -> str:
        """Подготавливает промпт с подстановкой контекста"""
        prompt = prompt_template

        # Заменяем плейсхолдеры из контекста
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))

        return prompt

    def _call_openai(self, prompt: str, config: Dict) -> Dict:
        """Вызов OpenAI API"""
        try:
            client = OpenAI(api_key=config["api_key"])

            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system",
                     "content": "Ты - эксперт по созданию технических инструкций и аналитических текстов."},
                    {"role": "user", "content": prompt}
                ],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                top_p=config["top_p"],
                frequency_penalty=config["frequency_penalty"],
                presence_penalty=config["presence_penalty"]
            )

            return {
                "success": True,
                "text": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }

    def _call_deepseek(self, prompt: str, config: Dict) -> Dict:
        """Вызов DeepSeek API"""
        try:
            client = OpenAI(
                api_key=config["api_key"],
                base_url="https://api.deepseek.com/v1"
            )

            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system",
                     "content": "Ты - эксперт по созданию технических инструкций и аналитических текстов."},
                    {"role": "user", "content": prompt}
                ],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                top_p=config["top_p"],
                frequency_penalty=config["frequency_penalty"],
                presence_penalty=config["presence_penalty"]
            )

            return {
                "success": True,
                "text": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }

    def call_grok_genapi(
            self, prompt: str, config: Dict, num_variants: int
    ) -> List[Dict]:
        """Вызов Grok-4.1 через gen-api.ru (синхронный режим)"""
        results = []

        try:
            api_key = config["api_key"]
            if not api_key:
                raise ValueError("API ключ GenAPI не настроен")

            # Можно передать конкретную версию, например grok-4-1-fast-reasoning
            model = config.get("model", "grok-4-1")  # или "grok-4-1-fast-reasoning"
            url = f"https://api.gen-api.ru/api/v1/networks/{model}"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты - опытный технический копирайтер и SEO-специалист."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": config.get("temperature", 0.7),
                "max_tokens": config.get("max_tokens", 2000),
                "top_p": config.get("top_p", 0.95),  # у Grok часто дефолт 1.0, но 0.95 обычно ок
                "frequency_penalty": config.get("frequency_penalty", 0.0),
                "presence_penalty": config.get("presence_penalty", 0.0),
                "n": num_variants,
                "is_sync": config.get("is_sync", True),
                "stream": config.get("stream", False),
                # "stop": [...],           # если нужно — можно добавить
                # "seed": 42,              # для воспроизводимости
            }

            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            # ────────────────────────────────────────────────
            # Парсинг ответа — самые вероятные варианты на 2026 год для gen-api
            # ────────────────────────────────────────────────
            generated_texts = []

            # Вариант 1: OpenAI-совместимый формат (самый вероятный)
            if "choices" in data and isinstance(data["choices"], list):
                for choice in data["choices"]:
                    msg = choice.get("message", {})
                    content = msg.get("content")
                    if content:
                        if isinstance(content, str):
                            generated_texts.append(content.strip())
                        elif isinstance(content, list):
                            text = " ".join(
                                p.get("text", "") for p in content
                                if p.get("type") == "text"
                            ).strip()
                            if text:
                                generated_texts.append(text)

            # Вариант 2: просто "response" как список
            elif "response" in data and isinstance(data["response"], list):
                for item in data["response"]:
                    if isinstance(item, dict):
                        content = item.get("content") or item.get("text") or item.get("message", {}).get("content")
                        if content:
                            if isinstance(content, str):
                                generated_texts.append(content.strip())
                            elif isinstance(content, list):
                                text = " ".join(
                                    p.get("text", "") for p in content if p.get("type") == "text"
                                ).strip()
                                if text:
                                    generated_texts.append(text)

            # Вариант 3: старый / запасной — "output"
            if not generated_texts and "output" in data:
                output = data["output"]
                if isinstance(output, str):
                    generated_texts = [output.strip()]
                elif isinstance(output, list):
                    generated_texts = [
                        x.strip() if isinstance(x, str) else
                        " ".join(p.get("text", "") for p in x if isinstance(p, dict) and p.get("type") == "text")
                        for x in output if x
                    ]

            if not generated_texts:
                full_resp_str = json.dumps(data, ensure_ascii=False, indent=2)
                raise ValueError(
                    f"Не удалось извлечь текст из ответа GenAPI (Grok).\n"
                    f"Полный ответ:\n{full_resp_str}"
                )

            # Формируем результаты
            for i, text in enumerate(generated_texts[:num_variants]):
                results.append({
                    "success": True,
                    "text": text,
                    "variant": i + 1,
                    "model": model,
                    "provider": "genapi_grok"
                })

        except Exception as e:
            results.append({
                "success": False,
                "error": f"GenAPI Grok ошибка: {str(e)}",
                "text": "",
                "variant": 1
            })

        return results
    def _call_genapi_gemini(self, prompt: str, config: Dict, num_variants: int) -> List[Dict]:
        """Вызов Gemini через gen-api.ru (синхронный режим)"""
        results = []

        try:
            api_key = config["api_key"]
            if not api_key:
                raise ValueError("API ключ GenAPI не настроен")

            model = config.get("model", "gemini-2-5-flash-lite")
            url = f"https://api.gen-api.ru/api/v1/networks/{model}"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": "Ты - опытный технический копирайтер и SEO-специалист."}]
                    },
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}]
                    }
                ],
                "temperature": config.get("temperature", 0.7),
                "max_tokens": config.get("max_tokens", 2000),
                "top_p": config.get("top_p", 0.9),
                "frequency_penalty": config.get("frequency_penalty", 0.0),
                "presence_penalty": config.get("presence_penalty", 0.0),
                "n": num_variants,
                "is_sync": config.get("is_sync", True),
                "stream": config.get("stream", False),
                #"reasoning_effort": "none"
            }


            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()

            # Парсинг ответа (наиболее вероятные варианты по документации gen-api)
            generated_texts = []

            if "response" in data and isinstance(data["response"], list):
                for item in data["response"]:
                    # Вариант 1: прямой message (как в gemini-2-5-flash)
                    if "message" in item:
                        content = item["message"].get("content")
                        if content:
                            if isinstance(content, str):
                                generated_texts.append(content.strip())
                            elif isinstance(content, list):  # на случай content как массив
                                text = " ".join(
                                    p.get("text", "") for p in content if p.get("type") == "text"
                                ).strip()
                                if text:
                                    generated_texts.append(text)

                    # Вариант 2: choices внутри item (как в gemini-3-1-pro)
                    if "choices" in item and isinstance(item["choices"], list):
                        for choice in item["choices"]:
                            msg = choice.get("message", {})
                            content = msg.get("content")
                            if content:
                                if isinstance(content, str):
                                    generated_texts.append(content.strip())
                                elif isinstance(content, list):
                                    text = " ".join(
                                        p.get("text", "") for p in content if p.get("type") == "text"
                                    ).strip()
                                    if text:
                                        generated_texts.append(text)

            # Дополнительный запасной путь (output)
            if not generated_texts and "output" in data:
                output = data["output"]
                if isinstance(output, str):
                    generated_texts = [output.strip()]
                elif isinstance(output, list):
                    generated_texts = [
                        (x.strip() if isinstance(x, str) else
                         " ".join(p.get("text", "") for p in x if isinstance(p, dict) and p.get("type") == "text"))
                        for x in output if x
                    ]

            if not generated_texts:
                # Для отладки — покажи полный ответ в ошибке
                full_resp_str = json.dumps(data, ensure_ascii=False, indent=2)
                raise ValueError(f"Не удалось извлечь текст из ответа GenAPI.\nПолный ответ:\n{full_resp_str}")

            # Добавляем результаты (как было)
            for i, text in enumerate(generated_texts[:num_variants]):
                results.append({
                    "success": True,
                    "text": text,
                    "variant": i + 1,
                    "model": config.get("model"),
                    "provider": "genapi_gemini"
                })
            # дальше как было
            for i, text in enumerate(generated_texts[:num_variants]):
                results.append({
                    "success": True,
                    "text": text,
                    "variant": i + 1,
                    "model": model,
                    "provider": "genapi_gemini"
                })

        except Exception as e:
            results.append({
                "success": False,
                "error": f"GenAPI Gemini ошибка: {str(e)}",
                "text": "",
                "variant": 1
            })

        return results

    def _call_true_gemini(self, prompt: str, config: Dict, num_variants: int) -> List[Dict]:
        """Вызов официального Google Gemini API"""
        results = []

        try:
            api_key = config["api_key"]
            if not api_key:
                raise ValueError("Google API ключ не настроен")

            model = config.get("model", "gemini-2.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            params = {"key": api_key}

            headers = {"Content-Type": "application/json"}

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": config.get("temperature", 0.7),
                    "maxOutputTokens": config.get("max_tokens", 2000),
                    "topP": config.get("top_p", 0.9)
                }
            }

            for i in range(num_variants):
                response = requests.post(url, headers=headers, json=payload, params=params, timeout=90)
                response.raise_for_status()
                data = response.json()

                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    results.append({
                        "success": True,
                        "text": text,
                        "variant": i + 1,
                        "model": model,
                        "provider": "true_gemini"
                    })
                except (KeyError, IndexError):
                    raise ValueError(f"Не удалось извлечь текст из ответа True Gemini: {data}")

        except Exception as e:
            results.append({
                "success": False,
                "error": f"True Gemini ошибка: {str(e)} (возможно нужен VPN)",
                "text": "",
                "variant": 1
            })

        return results

    def generate_instruction(self, prompt_template: str, context: Dict,
                             provider: str = None, num_variants: int = 1,
                             return_full_response: bool = False) -> List[Dict]:
        """
        Генерирует инструкции через AI

        Args:
            prompt_template: Шаблон промпта с плейсхолдерами
            context: Словарь с данными для подстановки
            provider: Провайдер AI (openai/deepseek)
            num_variants: Количество вариантов для генерации
            return_full_response: Вернуть полный ответ от AI API

        Returns:
            Список словарей с результатами генерации
        """
        if provider is None:
            provider = self.config_manager.config["default_provider"]

        config = self.config_manager.get_provider_config(provider)

        if not config.get("api_key"):
            return [{
                "success": False,
                "error": f"API ключ для провайдера {provider} не настроен",
                "text": "",
                "variant": 1,
                "full_response": None if return_full_response else None
            }]

        results = []

        # Подготавливаем промпт с подстановкой контекста
        prompt = prompt_template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            prompt = prompt.replace(placeholder, str(value))

        try:
            # Генерация через OpenAI
            if provider == "openai":
                api_key = config.get("api_key")
                if not api_key:
                    raise ValueError("API ключ OpenAI (GenAPI) не настроен")

                model_id = config.get("model", "gpt-4o-mini")  # ID модели в GenAPI
                url = f"https://api.gen-api.ru/api/v1/networks/{model_id}"

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                # Формируем тело запроса
                payload = {
                    "messages": [
                        {"role": "system", "content": "Ты - опытный технический копирайтер и SEO-специалист."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": config.get("temperature", 0.7),
                    "max_tokens": config.get("max_tokens", 1000),
                    "top_p": config.get("top_p", 0.9),
                    "frequency_penalty": config.get("frequency_penalty", 0.0),
                    "presence_penalty": config.get("presence_penalty", 0.0),
                    "n": num_variants,  # запрашиваем нужное количество вариантов сразу
                    "is_sync": True  # синхронный режим
                }

                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=60)
                    response.raise_for_status()
                    data = response.json()

                    # Проверяем структуру ответа (ожидаем choices как в OpenAI)
                    # Проверяем структуру ответа GenAPI (поле response)
                    if "response" not in data or not isinstance(data["response"], list):
                        raise ValueError(f"Неожиданный формат ответа GenAPI: {data}")

                    # Обрабатываем каждый вариант из списка response
                    for i, resp_item in enumerate(data["response"]):
                        # Извлекаем текст из message
                        if "message" in resp_item and "content" in resp_item["message"]:
                            text = resp_item["message"]["content"].strip()
                        else:
                            text = ""  # или можно выбросить ошибку, если структура не соответствует

                        result = {
                            "success": True,
                            "text": text,
                            "variant": i + 1,
                            "model": model_id,
                            "provider": provider
                        }

                        if return_full_response:
                            # Можно сохранить весь ответ, но лучше сохранить data целиком
                            result["full_response"] = data

                        results.append(result)

                except requests.exceptions.RequestException as e:
                    error_msg = f"Ошибка HTTP запроса к GenAPI: {str(e)}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f" - {e.response.text}"
                    results.append({
                        "success": False,
                        "error": error_msg,
                        "text": "",
                        "variant": 1,
                        "full_response": None if return_full_response else None
                    })
                except Exception as e:
                    results.append({
                        "success": False,
                        "error": f"Ошибка при обработке ответа GenAPI: {str(e)}",
                        "text": "",
                        "variant": 1,
                        "full_response": None if return_full_response else None
                    })

            # Генерация через DeepSeek
            elif provider == "deepseek":
                client = OpenAI(
                    api_key=config["api_key"],
                    base_url="https://api.deepseek.com/v1"
                )

                for i in range(num_variants):
                    try:
                        response = client.chat.completions.create(
                            model=config.get("model", "deepseek-chat"),
                            messages=[
                                {"role": "system", "content": "Ты - опытный технический копирайтер и SEO-специалист."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=config.get("temperature", 0.7),
                            max_tokens=config.get("max_tokens", 1000)
                        )

                        # Получаем текст ответа
                        text = response.choices[0].message.content.strip()

                        # Формируем результат
                        result = {
                            "success": True,
                            "text": text,
                            "variant": i + 1,
                            "model": config.get("model", "deepseek-chat"),
                            "provider": provider
                        }

                        # Если нужно вернуть полный ответ
                        if return_full_response:
                            # Сохраняем полный ответ API
                            result["full_response"] = {
                                "id": response.id,
                                "model": response.model,
                                "choices": [
                                    {
                                        "index": choice.index,
                                        "message": {
                                            "role": choice.message.role,
                                            "content": choice.message.content
                                        },
                                        "finish_reason": choice.finish_reason
                                    }
                                    for choice in response.choices
                                ],
                                "usage": {
                                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                                    "total_tokens": response.usage.total_tokens if response.usage else None
                                },
                                "created": response.created
                            }

                        results.append(result)

                    except Exception as e:
                        results.append({
                            "success": False,
                            "error": f"Ошибка DeepSeek: {str(e)}",
                            "text": "",
                            "variant": i + 1,
                            "full_response": None if return_full_response else None
                        })
            elif provider == "genapi_gemini":
                results = self._call_genapi_gemini(prompt, config, num_variants)

            elif provider == "true_gemini":
                results = self._call_true_gemini(prompt, config, num_variants)


            else:
                results.append({
                    "success": False,
                    "error": f"Неподдерживаемый провайдер: {provider}",
                    "text": "",
                    "variant": 1,
                    "full_response": None if return_full_response else None
                })

        except Exception as e:
            results.append({
                "success": False,
                "error": f"Общая ошибка: {str(e)}",
                "text": "",
                "variant": 1,
                "full_response": None if return_full_response else None
            })

        return results

    def batch_generate_for_characteristics(self, prompt_template: str,
                                           characteristics: List[Dict],
                                           category: str,
                                           provider: str = None) -> Dict[str, List[Dict]]:
        """
        Пакетная генерация инструкций для списка характеристик

        Args:
            prompt_template: Шаблон промпта
            characteristics: Список характеристик
            category: Категория товара
            provider: Провайдер AI

        Returns:
            Словарь {characteristic_id: [результаты]}
        """
        results = {}

        for char in characteristics:
            char_id = char.get("char_id", "")
            char_name = char.get("char_name", "")
            is_unique = char.get("is_unique", False)
            values = char.get("values", [])

            char_results = []

            if is_unique:
                # Для unique характеристик генерируем для каждого значения
                for value_item in values:
                    value = value_item.get("value", "")

                    context = {
                        "категория": category,
                        "характеристика": char_name,
                        "значение": value,
                        "тип": "unique"
                    }

                    variants = self.generate_instruction(
                        prompt_template, context, provider, num_variants=1
                    )

                    if variants:
                        char_results.append({
                            "value": value,
                            "results": variants
                        })
            else:
                # Для regular характеристик генерируем общую инструкцию
                context = {
                    "категория": category,
                    "характеристика": char_name,
                    "тип": "regular"
                }

                variants = self.generate_instruction(
                    prompt_template, context, provider, num_variants=3
                )

                char_results = variants

            results[char_id] = char_results

        return results


class AIInstructionManager:
    """Менеджер для работы с AI-инструкциями"""

    def __init__(self, storage_file="data/ai_instructions.json"):
        self.storage_file = storage_file
        self.instructions = self.load_instructions()

    @staticmethod
    def normalize_string(s):
        """Удаляет лишние пробелы и приводит к нижнему регистру"""
        if not isinstance(s, str):
            return ""
        return re.sub(r'\s+', ' ', s.strip()).lower()

    def load_instructions(self) -> Dict:
        """Загружает сохраненные инструкции"""
        try:
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    def reload(self):
        """Перезагружает инструкции из файла (сбрасывает кэш в памяти)"""
        self.instructions = self.load_instructions()
        return True

    def clear_all_instructions(self):
        """Полностью очищает все инструкции (память и файл)"""
        self.instructions = {}
        return self.save_instructions()
    def save_instructions(self) -> bool:
        """Сохраняет инструкции в файл"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.instructions, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Ошибка сохранения AI инструкций: {e}")
            return False

    def find_matching_context_hash(self, block_id: str, var_name: str,
                                   expected_context: Dict) -> Optional[str]:
        """
        Находит хэш контекста, который соответствует ожидаемому контексту
        """
        if block_id not in self.instructions:
            return None

        if var_name not in self.instructions[block_id]:
            return None

        # Нормализуем ожидаемый контекст
        exp_norm = {
            "категория": self.normalize_string(expected_context.get("категория", "")),
            "характеристика": self.normalize_string(expected_context.get("характеристика", "")),
            "тип": self.normalize_string(expected_context.get("тип", "regular")),
            "значение": self.normalize_string(expected_context.get("значение", "")),
            "block_id": self.normalize_string(expected_context.get("block_id", ""))
        }

        for context_hash, data in self.instructions[block_id][var_name].items():
            stored_context = data.get("context", {})
            stored_norm = {
                "категория": self.normalize_string(stored_context.get("категория", "")),
                "характеристика": self.normalize_string(stored_context.get("характеристика", "")),
                "тип": self.normalize_string(stored_context.get("тип", "regular")),
                "значение": self.normalize_string(stored_context.get("значение", "")),
                "block_id": self.normalize_string(stored_context.get("block_id", ""))
            }

            expected_type = exp_norm["тип"]
            stored_type = stored_norm["тип"]

            # Для разных типов - разные правила сравнения
            if expected_type != stored_type:
                continue

            # 1. Для OTHER блоков: сравниваем категорию, block_id и тип
            if expected_type == "other":
                if (stored_norm["категория"] == exp_norm["категория"] and
                        stored_norm["block_id"] == exp_norm["block_id"]):
                    return context_hash

            # 2. Для REGULAR характеристик: сравниваем категорию и характеристику
            elif expected_type == "regular":
                if (stored_norm["категория"] == exp_norm["категория"] and
                        stored_norm["характеристика"] == exp_norm["характеристика"]):
                    return context_hash

            # 3. Для UNIQUE характеристик: сравниваем категорию, характеристику и значение
            elif expected_type == "unique":
                if (stored_norm["категория"] == exp_norm["категория"] and
                        stored_norm["характеристика"] == exp_norm["характеристика"] and
                        stored_norm["значение"] == exp_norm["значение"]):
                    return context_hash

            # 4. Для других типов (старая логика для совместимости)
            else:
                match = True
                for key in ["категория", "характеристика", "тип", "block_id"]:
                    if exp_norm.get(key) and stored_norm.get(key) != exp_norm[key]:
                        match = False
                        break
                if match and exp_norm["тип"] == "unique" and exp_norm.get("значение"):
                    if stored_norm.get("значение") != exp_norm["значение"]:
                        match = False
                if match:
                    return context_hash

        return None

    def get_all_contexts_for_variable(self, block_id: str, var_name: str) -> List[Dict]:
        """
        Возвращает все контексты для переменной

        Args:
            block_id: ID блока
            var_name: Имя переменной

        Returns:
            Список контекстов
        """
        if block_id not in self.instructions:
            return []

        if var_name not in self.instructions[block_id]:
            return []

        contexts = []
        for context_hash, data in self.instructions[block_id][var_name].items():
            context_info = {
                "hash": context_hash,
                "context": data.get("context", {}),
                "values_count": len(data.get("values", [])),
                "original_count": len(data.get("original_values", [])),
                "updated_at": data.get("updated_at", 0)
            }
            contexts.append(context_info)

        return contexts

    def get_instruction(self, block_id: str, var_name: str,
                        expected_context: Dict = None) -> Optional[List[str]]:
        """Получает инструкции для переменной по контексту"""
        if block_id not in self.instructions:
            return None

        if var_name not in self.instructions[block_id]:
            return None

        if expected_context is None:
            # Если контекст не указан, возвращаем первую найденную инструкцию
            for context_hash, data in self.instructions[block_id][var_name].items():
                return data.get("values", [])
            return None

        # Нормализуем ожидаемый контекст
        exp_norm = {
            "категория": self.normalize_string(expected_context.get("категория", "")),
            "характеристика": self.normalize_string(expected_context.get("характеристика", "")),
            "тип": self.normalize_string(expected_context.get("тип", "regular")),
            "значение": self.normalize_string(expected_context.get("значение", "")),
            "block_id": self.normalize_string(expected_context.get("block_id", ""))
        }

        for context_hash, data in self.instructions[block_id][var_name].items():
            stored_context = data.get("context", {})
            stored_norm = {
                "категория": self.normalize_string(stored_context.get("категория", "")),
                "характеристика": self.normalize_string(stored_context.get("характеристика", "")),
                "тип": self.normalize_string(stored_context.get("тип", "regular")),
                "значение": self.normalize_string(stored_context.get("значение", "")),
                "block_id": self.normalize_string(stored_context.get("block_id", ""))
            }

            expected_type = exp_norm["тип"]
            stored_type = stored_norm["тип"]

            if expected_type != stored_type:
                continue

            # 1. Для OTHER блоков
            if expected_type == "other":
                if (stored_norm["категория"] == exp_norm["категория"] and
                        stored_norm["block_id"] == exp_norm["block_id"]):
                    return data.get("values", [])

            # 2. Для REGULAR характеристик
            elif expected_type == "regular":
                if (stored_norm["категория"] == exp_norm["категория"] and
                        stored_norm["характеристика"] == exp_norm["характеристика"]):
                    return data.get("values", [])

            # 3. Для UNIQUE характеристик
            elif expected_type == "unique":
                if (stored_norm["категория"] == exp_norm["категория"] and
                        stored_norm["характеристика"] == exp_norm["характеристика"] and
                        stored_norm["значение"] == exp_norm["значение"]):
                    return data.get("values", [])

        return None

    def save_instruction(self, block_id: str, var_name: str,
                         values: List[str], context: Dict = None,
                         metadata: Dict = None) -> bool:
        """Сохраняет сгенерированные инструкции с разбивкой по пунктам"""
        if block_id not in self.instructions:
            self.instructions[block_id] = {}

        if var_name not in self.instructions[block_id]:
            self.instructions[block_id][var_name] = {}

            # Нормализуем контекст
        if context:
            normalized_context = {
                "категория": self.normalize_string(context.get("категория", "")),
                "характеристика": self.normalize_string(context.get("характеристика", "")),
                "тип": self.normalize_string(context.get("тип", "regular")),
                "значение": self.normalize_string(context.get("значение", "")),
                "block_id": self.normalize_string(context.get("block_id", ""))
            }
        else:
            normalized_context = {
                "категория": "",
                "характеристика": "",
                "тип": "regular",
                "значение": "",
                "block_id": ""
            }

        # Создаем хэш контекста для уникального ключа
        import hashlib
        context_str = json.dumps(normalized_context, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()

        # Разбиваем инструкции на пункты
        split_values = []
        for value in values:
            if isinstance(value, str):
                items = [item.strip() for item in value.split(';') if item.strip()]
                split_values.extend(items)
            else:
                split_values.append(str(value))

        # Сохраняем
        self.instructions[block_id][var_name][context_hash] = {
            "values": split_values,
            "original_values": values,
            "context": normalized_context,  # Сохраняем нормализованный контекст
            "metadata": metadata or {},
            "updated_at": time.time()
        }

        return self.save_instructions()

    def update_instruction_value(self, block_id: str, var_name: str,
                                 context_hash: str, index: int, new_value: str) -> bool:
        """Обновляет конкретное значение инструкции"""
        try:
            if (block_id in self.instructions and
                    var_name in self.instructions[block_id] and
                    context_hash in self.instructions[block_id][var_name]):

                values = self.instructions[block_id][var_name][context_hash]["values"]
                if 0 <= index < len(values):
                    values[index] = new_value
                    return self.save_instructions()
        except:
            pass
        return False

    def update_full_instruction(self, block_id: str, var_name: str,
                                context_hash: str, index: int, new_full_value: str) -> bool:
        """Обновляет полную инструкцию и переразбивает ее на пункты"""
        try:
            if (block_id in self.instructions and
                    var_name in self.instructions[block_id] and
                    context_hash in self.instructions[block_id][var_name]):

                # Обновляем оригинальное значение
                original_values = self.instructions[block_id][var_name][context_hash]["original_values"]
                if 0 <= index < len(original_values):
                    original_values[index] = new_full_value

                # Переразбиваем на пункты
                split_values = []
                for value in original_values:
                    if isinstance(value, str):
                        items = [item.strip() for item in value.split(';') if item.strip()]
                        split_values.extend(items)
                    else:
                        split_values.append(str(value))

                # Обновляем разбитые значения
                self.instructions[block_id][var_name][context_hash]["values"] = split_values

                return self.save_instructions()
        except:
            pass
        return False

    def delete_instruction(self, block_id: str, var_name: str,
                           context_hash: str = None) -> bool:
        """Удаляет инструкции"""
        try:
            if block_id in self.instructions:
                if var_name in self.instructions[block_id]:
                    if context_hash:
                        if context_hash in self.instructions[block_id][var_name]:
                            del self.instructions[block_id][var_name][context_hash]
                    else:
                        del self.instructions[block_id][var_name]

                    # Удаляем пустые структуры
                    if not self.instructions[block_id][var_name]:
                        del self.instructions[block_id][var_name]
                    if not self.instructions[block_id]:
                        del self.instructions[block_id]

                    return self.save_instructions()
        except:
            pass
        return False