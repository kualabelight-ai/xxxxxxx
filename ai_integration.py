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
        if model.startswith("gpt-"):
            results = self._call_openai(prompt, model, num_variants, settings)
        elif model.startswith("claude-"):
            results = self._call_anthropic(prompt, model, num_variants, settings)
        elif "deepseek" in model.lower():
            results = self._call_deepseek(prompt, model, num_variants, settings)
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

    def _call_openai(self, prompt: str, model: str, n: int, settings: Dict) -> List[str]:
        """Вызывает OpenAI API"""
        try:
            if "openai" not in self.clients:
                return ["OpenAI клиент не инициализирован"]

            response = self.clients["openai"].chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                n=n,
                temperature=settings["temperature"],
                max_tokens=settings["max_tokens"],
                top_p=settings["top_p"],
                frequency_penalty=settings["frequency_penalty"],
                presence_penalty=settings["presence_penalty"]
            )

            return [choice.message.content for choice in response.choices]
        except Exception as e:
            return [f"OpenAI ошибка: {str(e)}"]

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
            "gpt-4": "GPT-4",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "claude-3-opus": "Claude 3 Opus",
            "claude-3-sonnet": "Claude 3 Sonnet",
            "claude-3-haiku": "Claude 3 Haiku",
            "deepseek-chat": "DeepSeek Chat"
        }

        available = {}
        if self.config.get("openai_api_key"):
            for model, desc in models.items():
                if model.startswith("gpt-"):
                    available[model] = desc

        if self.config.get("anthropic_api_key"):
            for model, desc in models.items():
                if model.startswith("claude-"):
                    available[model] = desc

        if self.config.get("deepseek_api_key"):
            for model, desc in models.items():
                if "deepseek" in model:
                    available[model] = desc

        return available

    def clear_cache(self):
        """Очищает кэш генераций"""
        self.generations = {}
        self.save_generations()