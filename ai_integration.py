# ai_integration.py
import json
import os
import time
import hashlib
import requests
import streamlit as st
from typing import Dict, List, Optional, Any
import openai
from openai import OpenAI
from anthropic import Anthropic


# --- AI Manager ---
class AIManager:
    """Менеджер для работы с ИИ API"""

    def __init__(self):
        self.config_file = "config/ai_config.json"
        self.generations_file = "pages/data/ai_generations.json"
        self.config = self._load_config()
        self.generations = self._load_generations()
        self.clients = {}

        self._init_clients()

    def _load_config(self) -> Dict:
        """Загружает конфигурацию AI"""
        default_config = {
            "openai_api_key": "",
            "anthropic_api_key": "",
            "deepseek_api_key": "",
            "default_model": "gpt-3.5-turbo",
            "default_temperature": 0.7,
            "default_max_tokens": 2000,
            "default_top_p": 0.9,
            "default_frequency_penalty": 0.0,
            "default_presence_penalty": 0.1,
            "cache_enabled": True
        }

        try:
            os.makedirs("config", exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Обновляем только существующие ключи
                    for key in default_config:
                        if key not in loaded:
                            loaded[key] = default_config[key]
                    return loaded
        except:
            pass

        return default_config

    def save_config(self):
        """Сохраняет конфигурацию"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def _load_generations(self) -> Dict:
        """Загружает сохраненные генерации"""
        try:
            os.makedirs("data", exist_ok=True)
            if os.path.exists(self.generations_file):
                with open(self.generations_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_generations(self):
        """Сохраняет генерации"""
        try:
            with open(self.generations_file, 'w', encoding='utf-8') as f:
                json.dump(self.generations, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def _init_clients(self):
        """Инициализирует клиентов API"""
        # OpenAI
        if self.config.get("openai_api_key"):
            self.clients["openai"] = OpenAI(api_key=self.config["openai_api_key"])

        # Anthropic
        if self.config.get("anthropic_api_key"):
            self.clients["anthropic"] = Anthropic(api_key=self.config["anthropic_api_key"])

    def get_cache_key(self, prompt: str, context: Dict, model: str, settings: Dict) -> str:
        """Создает ключ для кэша"""
        data = {
            "prompt": prompt,
            "context": json.dumps(context, sort_keys=True),
            "model": model,
            "settings": json.dumps(settings, sort_keys=True)
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    def generate(
            self,
            prompt_template: str,
            context: Dict,
            model: Optional[str] = None,
            num_variants: int = 1,
            **kwargs
    ) -> List[str]:
        """Генерирует текст через AI API"""

        # Подставляем контекст
        prompt = prompt_template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            prompt = prompt.replace(placeholder, str(value))

        # Проверяем кэш
        model = model or self.config["default_model"]
        settings = {
            "temperature": kwargs.get("temperature", self.config["default_temperature"]),
            "max_tokens": kwargs.get("max_tokens", self.config["default_max_tokens"]),
            "top_p": kwargs.get("top_p", self.config["default_top_p"]),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config["default_frequency_penalty"]),
            "presence_penalty": kwargs.get("presence_penalty", self.config["default_presence_penalty"]),
        }

        cache_key = self.get_cache_key(prompt_template, context, model, settings)

        if self.config.get("cache_enabled") and cache_key in self.generations:
            cached = self.generations[cache_key]["results"]
            if len(cached) >= num_variants:
                return cached[:num_variants]

        # Определяем провайдера
        if model.startswith("gpt-") or model in ["gpt-4o-mini", "gpt-4-turbo-preview", "gpt-3.5-turbo"]:
            results = self._call_openai(prompt, model, num_variants, settings)  # через gen-api, как было

        elif model.startswith("claude-"):
            results = self._call_anthropic(prompt, model, num_variants, settings)

        elif "deepseek" in model.lower():
            results = self._call_deepseek(prompt, model, num_variants, settings)


        elif model.startswith("genapi-") or model.startswith("genapi_"):

            # Gemini через gen-api.ru

            results = self._call_genapi_gemini(prompt, model, num_variants, settings)


        elif model.startswith("gemini-"):

            # Настоящий Google Gemini

            results = self._call_true_gemini(prompt, model, num_variants, settings)

        else:
            results = [f"Неизвестная модель: {model}"]

        # Сохраняем в кэш
        if results and self.config.get("cache_enabled"):
            self.generations[cache_key] = {
                "prompt_template": prompt_template,
                "context": context,
                "model": model,
                "settings": settings,
                "results": results,
                "timestamp": time.time()
            }
            self.save_generations()

        return results

    def _call_genapi_gemini(self, prompt: str, model: str, n: int, settings: Dict) -> List[str]:
        """Вызывает Gemini через GenAPI (синхронный режим)"""
        api_key = self.config.get("genapi_api_key", "")
        if not api_key:
            return ["GenAPI ключ не настроен"]

        # Модель без префикса "genapi_", например gemini-2-5-flash-lite
        clean_model = model.replace("genapi_", "").replace("genapi-", "")

        base_url = self.config.get("genapi_gemini_endpoint_base", "https://api.gen-api.ru/api/v1/networks")
        url = f"{base_url}/{clean_model}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        data = {
            "messages": [
                {"role": "system", "content": "Ты - опытный технический копирайтер и SEO-специалист."},
                {"role": "user", "content": prompt}
            ],
            "temperature": settings["temperature"],
            "max_tokens": settings["max_tokens"],
            "top_p": settings["top_p"],
            "frequency_penalty": settings["frequency_penalty"],
            "presence_penalty": settings["presence_penalty"],
            "n": n,
            "is_sync": True,
            "stream": False,
            "reasoning_effort": "none"
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=90)
            response.raise_for_status()
            result = response.json()

            # Новый парсинг — актуальная структура gen-api (2026 год)
            generated_texts = []
            if "response" in result and isinstance(result["response"], list):
                for item in result["response"]:
                    message = item.get("message", {})
                    content = message.get("content", "").strip()
                    if content:
                        generated_texts.append(content)

            # Запасной вариант на случай старой структуры
            if not generated_texts and "output" in result:
                output = result["output"]
                if isinstance(output, str):
                    generated_texts = [output]
                elif isinstance(output, dict) and "choices" in output:
                    generated_texts = [
                        ch.get("message", {}).get("content", "")
                        for ch in output.get("choices", [])
                    ]

            if not generated_texts:
                return [f"Не удалось извлечь текст из ответа GenAPI: {result}"]

            # Возвращаем столько текстов, сколько запрошено (или меньше, если вернулось меньше)
            return generated_texts[:n]

        except requests.exceptions.RequestException as e:
            error_msg = f"GenAPI Gemini ошибка HTTP: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" - {e.response.text[:200]}"  # обрезаем длинный ответ
            return [error_msg]

        except Exception as e:
            return [f"GenAPI Gemini ошибка: {str(e)}"]
    def _call_true_gemini(self, prompt: str, model: str, n: int, settings: Dict) -> List[str]:
        """Вызывает официальный Google Gemini API"""
        api_key = self.config.get("true_gemini_api_key", "")
        if not api_key:
            return ["Google Gemini API ключ не настроен"]

        base_url = self.config.get("true_gemini_base_url", "https://generativelanguage.googleapis.com/v1beta")
        url = f"{base_url}/models/{model}:generateContent"
        params = {"key": api_key}

        headers = {"Content-Type": "application/json"}

        # Конвертация в формат Google (нет system role → всё в user/model)
        contents = [{"role": "user", "parts": [{"text": prompt}]}]

        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": settings["temperature"],
                "maxOutputTokens": settings["max_tokens"],
                "topP": settings["top_p"],
                # frequency_penalty и presence_penalty → нет прямых аналогов, можно игнорировать или использовать topK
            }
        }

        try:
            results = []
            for _ in range(n):
                response = requests.post(url, headers=headers, json=data, params=params, timeout=90)
                response.raise_for_status()
                resp_json = response.json()

                # Путь к тексту в официальном Gemini API
                try:
                    text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    results.append(text)
                except (KeyError, IndexError):
                    return [f"Не удалось извлечь текст: {resp_json}"]

            return results

        except Exception as e:
            return [f"True Gemini ошибка: {str(e)} — возможно нужен VPN / зарубежный IP"]
    def _call_openai(self, prompt: str, model: str, n: int, settings: Dict) -> List[str]:
        """Вызывает OpenAI через GenAPI"""
        api_key = self.config.get("openai_api_key", "")
        if not api_key:
            return ["OpenAI API ключ (GenAPI) не настроен"]

        # Базовый URL GenAPI
        base_url = "https://api.gen-api.ru/api/v1/networks"
        url = f"{base_url}/{model}"  # model уже должна содержать ID модели GenAPI (например, "gpt-4o-mini")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Формируем тело запроса
        data = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": settings["temperature"],
            "max_tokens": settings["max_tokens"],
            "top_p": settings["top_p"],
            "frequency_penalty": settings["frequency_penalty"],
            "presence_penalty": settings["presence_penalty"],
            "n": n,
            "is_sync": True  # синхронный режим для получения ответа сразу
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                # Предполагаем, что структура ответа аналогична OpenAI
                # (нужно проверить по документации GenAPI, возможно, поле называется "output")
                if "choices" in result:
                    return [choice["message"]["content"] for choice in result["choices"]]
                elif "output" in result:
                    # Альтернативный формат
                    return [result["output"]]
                else:
                    return [f"Неожиданный формат ответа: {result}"]
            else:
                return [f"Ошибка API (HTTP {response.status_code}): {response.text}"]
        except Exception as e:
            return [f"Исключение при вызове GenAPI: {str(e)}"]

    def _call_anthropic(self, prompt: str, model: str, n: int, settings: Dict) -> List[str]:
        """Вызывает Anthropic API"""
        try:
            if "anthropic" not in self.clients:
                return ["Anthropic клиент не инициализирован"]

            results = []
            for _ in range(n):
                response = self.clients["anthropic"].messages.create(
                    model=model,
                    max_tokens=settings["max_tokens"],
                    temperature=settings["temperature"],
                    top_p=settings["top_p"],
                    messages=[{"role": "user", "content": prompt}]
                )
                results.append(response.content[0].text)

            return results
        except Exception as e:
            return [f"Anthropic ошибка: {str(e)}"]

    def _call_deepseek(self, prompt: str, model: str, n: int, settings: Dict) -> List[str]:
        """Вызывает DeepSeek API"""
        try:
            api_key = self.config.get("deepseek_api_key", "")
            if not api_key:
                return ["DeepSeek API ключ не настроен"]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            results = []
            for _ in range(n):
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": settings["temperature"],
                    "max_tokens": settings["max_tokens"],
                    "top_p": settings["top_p"],
                    "frequency_penalty": settings["frequency_penalty"],
                    "presence_penalty": settings["presence_penalty"]
                }

                response = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()["choices"][0]["message"]["content"]
                    results.append(result)
                else:
                    results.append(f"API ошибка: {response.status_code}")

            return results
        except Exception as e:
            return [f"DeepSeek ошибка: {str(e)}"]

    def get_available_models(self) -> Dict[str, str]:
        """Возвращает доступные модели"""
        models = {
            # OpenAI через GenAPI
            "gpt-4o-mini": "GPT-4o mini",
            "gpt-4-turbo-preview": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            # Gemini через gen-api
            "gemini-2-5-flash-lite": "Gemini 2.5 Flash-Lite (GenAPI)",
            "gemini-2-5-flash": "Gemini 2.5 Flash (GenAPI)",
            # Настоящий Gemini (требует VPN + ключ)
            "gemini-2.5-flash": "Gemini 2.5 Flash (Google direct)",
            "gemini-1.5-pro": "Gemini 1.5 Pro (Google direct)",
            # Anthropic (прямое API)
            "claude-3-opus": "Claude 3 Opus",
            "claude-3-sonnet": "Claude 3 Sonnet",
            "claude-3-haiku": "Claude 3 Haiku",
            # DeepSeek (прямое API)
            "deepseek-chat": "DeepSeek Chat"
        }

        available = {}
        if self.config.get("openai_api_key"):
            # Добавляем все OpenAI-модели, которые поддерживает GenAPI
            # Лучше запросить список через API, но для начала можно статически
            openai_models = ["gpt-4o-mini", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
            for model_id in openai_models:
                available[model_id] = models.get(model_id, model_id)

        if self.config.get("anthropic_api_key"):
            for model, desc in models.items():
                if model.startswith("claude-"):
                    available[model] = desc

        if self.config.get("deepseek_api_key"):
            for model, desc in models.items():
                if "deepseek" in model:
                    available[model] = desc
        if self.config.get("genapi_api_key"):
            for m in ["gemini-2-5-flash-lite", "gemini-2-5-flash"]:
                if m in models:
                    available[m] = models[m]

        if self.config.get("true_gemini_api_key"):
            for m in ["gemini-2.5-flash", "gemini-1.5-pro"]:
                if m in models:
                    available[m] = models[m]
        return available

    def clear_cache(self):
        """Очищает кэш генераций"""
        self.generations = {}
        self.save_generations()