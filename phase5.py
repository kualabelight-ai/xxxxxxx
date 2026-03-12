import streamlit as st
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from ai_module import AIGenerator, AIConfigManager
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, TimeoutError
# --- CSS стили для фазы 5 ---
def local_css():
    st.markdown("""
    <style>
    .phase5-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .prompt-card {
        background-color: white;
        border-left: 4px solid #4CAF50;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .result-card {
        background-color: #e8f5e9;
        border-left: 4px solid #2196F3;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .error-card {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .pending-card {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        margin: 0 5px;
    }
    .status-success { background-color: #c8e6c9; color: #2e7d32; }
    .status-error { background-color: #ffcdd2; color: #c62828; }
    .status-pending { background-color: #ffe0b2; color: #ef6c00; }
    .status-running { background-color: #bbdefb; color: #1565c0; }
    .generation-progress {
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
        height: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .text-preview {
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid #ddd;
        padding: 10px;
        border-radius: 5px;
        background-color: #fafafa;
        font-size: 0.9em;
    }
    .stats-box {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Менеджер данных фазы 5 ---
class Phase5DataManager:
    """Управление данными для фазы 5"""

    def __init__(self):
        self.init_session_state()

    def init_session_state(self):
        """Инициализация состояния фазы 5 в session_state"""
        # Инициализируем phase5_prompts если не существует
        if 'phase5_prompts' not in st.session_state:
            st.session_state.phase5_prompts = []

        if 'phase5' not in st.session_state:
            st.session_state.phase5 = {
                'generation_status': 'idle',  # idle, running, paused, stopped, completed
                'selected_prompt_ids': [],
                'results': {},  # prompt_id -> result_data
                'statistics': {
                    'total': 0,
                    'selected': 0,
                    'completed': 0,
                    'success': 0,
                    'error': 0,
                    'pending': 0
                },
                'generation_settings': {
                    'provider': 'openai',
                    'temperature': 0.7,
                    'max_tokens': 2000,
                    'retry_count': 3,
                    'delay_between_requests': 2.0
                },
                'export_format': 'json',
                'current_batch': 0,
                'total_batches': 0,
                'generation_start_time': None,
                'generation_end_time': None,
                'generation_queue': [],
                'current_index': 0,
                'generation_running': False,
                'initialized': False  # Флаг инициализации
            }

    def reset_session_data(self):
        """Полный сброс данных фазы 5"""
        st.session_state.phase5_prompts = []
        st.session_state.phase5 = {
            'generation_status': 'idle',
            'selected_prompt_ids': [],
            'results': {},
            'statistics': {
                'total': 0,
                'selected': 0,
                'completed': 0,
                'success': 0,
                'error': 0,
                'pending': 0
            },
            'generation_settings': {
                'provider': 'openai',
                'temperature': 0.7,
                'max_tokens': 2000,
                'retry_count': 3,
                'delay_between_requests': 2.0
            },
            'export_format': 'json',
            'current_batch': 0,
            'total_batches': 0,
            'generation_start_time': None,
            'generation_end_time': None,
            'generation_queue': [],
            'current_index': 0,
            'generation_running': False,
            'initialized': False
        }

    def reload_from_phase4(self):
        """Перезагрузить данные из фазы 4 (сброс текущих результатов)"""
        self.reset_session_data()
        return self.load_prompts_from_phase4()

    def load_prompts_from_phase4(self):
        """Загрузка промптов из фазы 4"""
        prompts = []

        # Пробуем загрузить из session_state
        if 'phase4_generated_prompts' in st.session_state and st.session_state.phase4_generated_prompts:
            prompts = st.session_state.phase4_generated_prompts.copy()
            st.success(f"✅ Загружено {len(prompts)} промптов из session_state")

        # Если в session_state нет, пробуем загрузить из app_data
        elif 'app_data' in st.session_state and 'phase4' in st.session_state.app_data:
            phase4_data = st.session_state.app_data['phase4']
            if 'prompts' in phase4_data:
                prompts = phase4_data['prompts'].copy()
                st.success(f"✅ Загружено {len(prompts)} промптов из app_data")

        if not prompts:
            st.warning("⚠️ Не найдены промпты из фазы 4")
            return []

        # Добавляем ID к каждому промпту для идентификации
        for i, prompt in enumerate(prompts):
            if 'characteristic_id' in prompt:
                prompt_id = f"char_{prompt['characteristic_id']}_{prompt.get('value', '')}_{prompt.get('prompt_num', i)}"
            elif 'block_id' in prompt:
                prompt_id = f"block_{prompt['block_id']}_{prompt.get('prompt_num', i)}"
            else:
                prompt_id = f"prompt_{i}"

            prompt['phase5_id'] = prompt_id

            # Инициализируем результат для этого промпта, если его еще нет
            if prompt_id not in st.session_state.phase5['results']:
                st.session_state.phase5['results'][prompt_id] = {
                    'prompt_id': prompt_id,
                    'prompt': prompt.get('prompt', ''),
                    'ai_response': '',
                    'status': 'pending',
                    'model': '',
                    'provider': '',
                    'tokens_used': 0,
                    'generated_at': None,
                    'error_message': None,
                    'edited_text': '',
                    'characteristic_name': prompt.get('characteristic_name', ''),
                    'characteristic_value': prompt.get('value', ''),
                    'block_name': prompt.get('block_name', ''),
                    'prompt_num': prompt.get('prompt_num', 1),
                    'type': prompt.get('type', prompt.get('block_type', 'unknown'))
                }

        st.session_state.phase5_prompts = prompts.copy()

        # Обновляем статистику
        st.session_state.phase5['statistics']['total'] = len(prompts)
        st.session_state.phase5['statistics']['pending'] = len(prompts)
        st.session_state.phase5['statistics']['selected'] = 0

        # Устанавливаем флаг инициализации
        st.session_state.phase5['initialized'] = True

        return prompts

    def get_prompt_by_id(self, prompt_id):
        """Получить промпт по ID"""
        for prompt in st.session_state.phase5_prompts:
            if prompt.get('phase5_id') == prompt_id:
                return prompt
        return None

    def get_prompts_for_generation(self):
        """Получить промпты, выбранные для генерации"""
        selected_ids = st.session_state.phase5['selected_prompt_ids']
        return [p for p in st.session_state.phase5_prompts if p.get('phase5_id') in selected_ids]

    def update_result(self, prompt_id, result_data):
        """Обновить результат генерации для промпта"""
        if prompt_id in st.session_state.phase5['results']:
            current_result = st.session_state.phase5['results'][prompt_id]
            current_result.update(result_data)

            # Обновляем статистику
            self._update_statistics()

    def _update_statistics(self):
        """Обновить статистику на основе текущих результатов"""
        stats = {
            'success': 0,
            'error': 0,
            'pending': 0,
            'completed': 0
        }

        for result in st.session_state.phase5['results'].values():
            if result['status'] == 'success':
                stats['success'] += 1
            elif result['status'] == 'error':
                stats['error'] += 1
            elif result['status'] == 'pending':
                stats['pending'] += 1
            stats['completed'] = stats['success'] + stats['error']

        # Обновляем только статистические поля
        st.session_state.phase5['statistics'].update(stats)

    def reset_generation(self):
        """Сбросить результаты генерации"""
        for prompt_id in st.session_state.phase5['results']:
            st.session_state.phase5['results'][prompt_id].update({
                'ai_response': '',
                'status': 'pending',
                'model': '',
                'provider': '',
                'tokens_used': 0,
                'generated_at': None,
                'error_message': None,
                'edited_text': ''
            })

        st.session_state.phase5.update({
            'generation_status': 'idle',
            'selected_prompt_ids': [],
            'statistics': {
                'total': st.session_state.phase5['statistics']['total'],
                'selected': 0,
                'completed': 0,
                'success': 0,
                'error': 0,
                'pending': st.session_state.phase5['statistics']['total']
            },
            'current_batch': 0,
            'total_batches': 0,
            'generation_start_time': None,
            'generation_end_time': None
        })

    def select_all_prompts(self):
        """Выбрать все промпты"""
        all_ids = [p.get('phase5_id') for p in st.session_state.phase5_prompts]
        st.session_state.phase5['selected_prompt_ids'] = all_ids
        st.session_state.phase5['statistics']['selected'] = len(all_ids)

    def deselect_all_prompts(self):
        """Сбросить выбор всех промптов"""
        st.session_state.phase5['selected_prompt_ids'] = []
        st.session_state.phase5['statistics']['selected'] = 0

    def toggle_prompt_selection(self, prompt_id):
        """Переключить выбор конкретного промпта"""
        selected_ids = st.session_state.phase5['selected_prompt_ids']

        if prompt_id in selected_ids:
            selected_ids.remove(prompt_id)
        else:
            selected_ids.append(prompt_id)

        # Обновляем статистику
        st.session_state.phase5['statistics']['selected'] = len(selected_ids)
        # Сохраняем в session_state
        st.session_state.phase5['selected_prompt_ids'] = selected_ids

    def save_results_to_file(self, format='json'):
        """Сохранить результаты в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == 'json':
            # Получаем категорию из данных проекта
            category = "Не указана"
            if 'app_data' in st.session_state and 'category' in st.session_state.app_data:
                category = st.session_state.app_data['category']

            # Сохраняем как JSON
            results_data = {
                'generated_at': datetime.now().isoformat(),
                'category': category,  # Добавляем категорию
                'statistics': st.session_state.phase5['statistics'],
                'settings': st.session_state.phase5['generation_settings'],
                'results': list(st.session_state.phase5['results'].values())
            }

            filename = f"phase5_results_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2, default=str)

            return filename

        elif format == 'txt':
            # Получаем категорию из данных проекта
            category = "Не указана"
            if 'app_data' in st.session_state and 'category' in st.session_state.app_data:
                category = st.session_state.app_data['category']

            # Сохраняем как TXT (только тексты)
            filename = f"phase5_texts_{timestamp}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                # Добавляем информацию о категории в начало файла
                f.write(f"Категория: {category}\n")
                f.write(f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")

                for prompt_id, result in st.session_state.phase5['results'].items():
                    if result['status'] == 'success' and result['ai_response']:
                        prompt = self.get_prompt_by_id(prompt_id)
                        if prompt:
                            f.write(f"=== {prompt.get('characteristic_name', 'Блок')}: "
                                    f"{prompt.get('value', '')} (Промпт {prompt.get('prompt_num', 1)}) ===\n")
                            f.write(result['ai_response'])
                            f.write("\n\n" + "=" * 50 + "\n\n")

        elif format == 'excel':
            filename = f"phase5_results_{timestamp}.xlsx"

            rows = []
            for prompt_id, result in st.session_state.phase5['results'].items():
                prompt = self.get_prompt_by_id(prompt_id)
                if prompt:
                    row = {
                        'ID': prompt_id,
                        'Тип': prompt.get('type', prompt.get('block_type', 'unknown')),
                        'Характеристика/Блок': prompt.get('characteristic_name', prompt.get('block_name', '')),
                        'Значение': prompt.get('value', ''),
                        'Номер промпта': prompt.get('prompt_num', 1),
                        'Промпт': prompt.get('prompt', ''),
                        'Статус': result.get('status', ''),
                        'Сгенерированный текст': result.get('edited_text') or result.get('ai_response', ''),
                        'Модель': result.get('model', ''),
                        'Провайдер': result.get('provider', ''),
                        'Токены': result.get('tokens_used', 0),
                        'Время генерации': result.get('generated_at', ''),
                        'Ошибка': result.get('error_message', ''),
                    }
                    rows.append(row)

            df = pd.DataFrame(rows)
            df.to_excel(filename, index=False, engine='openpyxl')
            return filename

        return None

    def save_to_app_data(self):
        """Сохраняет данные фазы 5 в app_data для передачи в фазу 6"""
        # Сохраняем в формате, удобном для фазы 6
        phase5_data = {
            'results': {},  # Будем заполнять в формате словаря
            'statistics': st.session_state.phase5['statistics'].copy(),
            'generation_settings': st.session_state.phase5['generation_settings'].copy(),
            'phase_completed': True,
            'completed_at': datetime.now().isoformat(),
            'prompts_list': st.session_state.phase5_prompts.copy(),
            'category': st.session_state.app_data.get('category', '')
        }

        # Преобразуем results в словарь с ключами по prompt_id
        results_dict = {}
        for prompt_id, result in st.session_state.phase5['results'].items():
            if isinstance(result, dict):
                # Добавляем дополнительную информацию из prompts
                prompt_info = None
                for prompt in st.session_state.phase5_prompts:
                    if prompt.get('phase5_id') == prompt_id:
                        prompt_info = prompt
                        break

                if prompt_info:
                    result.update({
                        'characteristic_name': prompt_info.get('characteristic_name', ''),
                        'characteristic_value': prompt_info.get('value', ''),
                        'block_name': prompt_info.get('block_name', ''),
                        'type': prompt_info.get('type', prompt_info.get('block_type', 'unknown')),
                        'prompt_id': prompt_id
                    })

                results_dict[prompt_id] = result

        phase5_data['results'] = results_dict

        # Сохраняем в app_data
        if 'app_data' not in st.session_state:
            st.session_state.app_data = {}

        st.session_state.app_data['phase5'] = phase5_data

        # Также добавляем флаг, что можно переходить к фазе 6
        st.session_state.app_data['phase5_completed'] = True

        return True
    def complete_phase5_and_prepare_phase6(self):
        """Завершить фазу 5 и подготовить данные для фазы 6"""

        # Проверяем, что есть результаты генерации
        if self.phase5['statistics']['completed'] == 0:
            st.warning("Нет сгенерированных результатов!")
            return False

        # Собираем данные для передачи в фазу 6
        phase6_data = {
            'generation_results': self.phase5['results'],
            'generation_stats': self.phase5['statistics'],
            'generation_settings': self.phase5['generation_settings'],
            'prompts_data': st.session_state.phase5_prompts,
            'completed_at': datetime.now().isoformat(),
            'total_texts': self.phase5['statistics']['success']
        }

        # Сохраняем в app_data для передачи между фазами
        if 'app_data' in st.session_state:
            st.session_state.app_data['phase5'] = phase6_data

        # Также помечаем phase6 как готовую к приему данных
        # Это нужно, чтобы app.py увидел, что фаза 5 завершена
        if 'phase6' not in st.session_state.app_data:
            st.session_state.app_data['phase6'] = {
                'received_from_phase5': True,
                'ready_for_processing': True,
                'data_received_at': datetime.now().isoformat()
            }

        # Помечаем фазу 5 как завершенную в session_state
        self.phase5['phase_completed'] = True
        self.phase5['phase_completed_at'] = datetime.now().isoformat()

        st.success("✅ Фаза 5 завершена! Данные подготовлены для фазы 6.")
        return True


class GenerationManager:
    def __init__(self, data_manager: Phase5DataManager):
        self.data_manager = data_manager
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._worker_thread = None
        self._result_queue = queue.Queue()  # для безопасной передачи результатов в основной поток

    def start_generation(self, batch_size=10):
        if st.session_state.phase5.get('generation_status') in ['running', 'starting']:
            st.warning("Генерация уже запущена или запускается")
            return

        selected_prompts = self.data_manager.get_prompts_for_generation()
        if not selected_prompts:
            st.error("Не выбрано ни одного промпта для генерации!")
            return

        self._stop_event.clear()
        self._pause_event.clear()

        # ─── Подготавливаем всё, что нужно потоку, в ГЛАВНОМ потоке ───
        config_manager = st.session_state.get('ai_config_manager')
        if config_manager is None:
            st.error("ai_config_manager не инициализирован в session_state!")
            return

        ai_generator = AIGenerator(config_manager)  # создаём здесь, один раз

        worker_data = {
            "generation_queue": [p.get('phase5_id') for p in selected_prompts],
            "settings": st.session_state.phase5['generation_settings'].copy(),
            "prompts": {
                p.get('phase5_id'): {
                    'prompt': p.get('prompt', ''),
                    # добавь другие нужные поля промпта, если используются
                } for p in selected_prompts
            },
            "ai_generator": ai_generator,          # ← передаём готовый объект
        }

        st.session_state.phase5.update({
            'generation_status': 'running',
            'generation_start_time': datetime.now().isoformat(),
            'generation_queue': worker_data["generation_queue"].copy(),
            'current_index': 0,
            'generation_running': True,
            'current_batch': 0,
            'total_batches': len(selected_prompts),
            'error_message': None
        })

        self._worker_thread = threading.Thread(
            target=self._generation_worker,
            args=(worker_data,),
            daemon=True
        )
        self._worker_thread.start()

        st.success(f"🚀 Генерация запущена ({len(selected_prompts)} промптов)")
        st.rerun()

    # Полностью замени _generation_worker

    def _generation_worker(self, worker_data):
        queue_list    = worker_data["generation_queue"]
        settings      = worker_data["settings"]
        prompts       = worker_data["prompts"]
        ai_generator  = worker_data["ai_generator"]

        current_index = 0

        from concurrent.futures import ThreadPoolExecutor, TimeoutError   # ← добавь этот импорт вверху файла, если ещё нет

        while current_index < len(queue_list):
            if self._stop_event.is_set():
                return

            if self._pause_event.is_set():
                time.sleep(0.5)
                continue

            prompt_id = queue_list[current_index]
            prompt_data = prompts.get(prompt_id)

            if not prompt_data:
                current_index += 1
                continue

            success = False
            ai_response = None
            model_used = None
            tokens_used = 0
            error_message = None

            # ──────────────────────────────────────────────────────────────
            # Вот этот блок — основной цикл попыток с таймаутом
            for attempt in range(settings['retry_count']):
                if self._stop_event.is_set():
                    error_message = "Остановлено пользователем"
                    success = False
                    break

                if self._pause_event.is_set():
                    # Пауза: ждём, пока не снимут паузу
                    while self._pause_event.is_set() and not self._stop_event.is_set():
                        time.sleep(0.3)

                try:
                    results = ai_generator.generate_instruction( ... )  # синхронно
                    # обработка results
                    success = True
                    break
                except Exception as e:
                    error_message = str(e)
                    time.sleep(1.5)

            # ──────────────────────────────────────────────────────────────

            result_data = {
                'ai_response': self._clean_response(ai_response) if success else '',
                'status': 'success' if success else 'error',
                'model': model_used if success else '',
                'provider': settings['provider'],
                'tokens_used': tokens_used if success else 0,
                'generated_at': datetime.now().isoformat(),
                'error_message': error_message if not success else None,
                'edited_text': self._clean_response(ai_response) if success else ''
            }

            self._result_queue.put((prompt_id, result_data, current_index + 1))

            current_index += 1
            time.sleep(settings['delay_between_requests'])

        self._result_queue.put(("DONE", None, current_index))

    def pause_generation(self):
        self._pause_event.set()
        st.session_state.phase5['generation_status'] = 'paused'
        st.info("Пауза запрошена. Текущий промпт завершится, затем пауза.")
        st.rerun()

    def resume_generation(self):
        self._pause_event.clear()
        st.session_state.phase5['generation_status'] = 'running'
        st.success("Возобновлено")
        st.rerun()

    def stop_generation(self):
        self._stop_event.set()
        st.session_state.phase5['generation_status'] = 'stopping'
        st.warning("Остановка... ждём конца текущего запроса к модели")
        st.rerun()
    def get_generation_progress(self):
        phase5 = st.session_state.phase5
        if not phase5.get('generation_queue'):
            return 0
        return int((phase5['current_index'] / len(phase5['generation_queue'])) * 100)

    def check_and_process_results(self):
        updated = False
        phase5 = st.session_state.phase5

        while not self._result_queue.empty():
            item = self._result_queue.get()
            prompt_id, result_data, new_index = item

            if prompt_id == "DONE":
                phase5['generation_status'] = 'completed'
                phase5['generation_running'] = False
                phase5['generation_end_time'] = datetime.now().isoformat()
                updated = True
                continue

            self.data_manager.update_result(prompt_id, result_data)
            phase5['current_index'] = new_index
            phase5['current_batch'] = new_index
            updated = True

        return updated

    def _clean_response(self, text):
        if not text:
            return ""
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


# --- Компоненты интерфейса ---
class Phase5UIComponents:
    """Компоненты пользовательского интерфейса фазы 5"""

    @staticmethod
    def show_prompts_selection(data_manager: Phase5DataManager):
        """Показать таблицу выбора промптов"""
        st.header("📋 Выбор промптов для генерации")

        # Проверяем наличие промптов
        if 'phase5_prompts' not in st.session_state or not st.session_state.phase5_prompts:
            st.info("Нет загруженных промптов. Загрузите данные из фазы 4.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Загрузить промпты из фазы 4", key="load_prompts_btn"):
                    data_manager.load_prompts_from_phase4()
                    st.rerun()
            with col2:
                if st.button("🗑️ Сбросить все данные фазы 5", key="reset_all_data_btn"):
                    data_manager.reset_session_data()
                    st.rerun()
            return

        prompts = st.session_state.phase5_prompts

        # Быстрые действия




        # Фильтры
        st.subheader("Фильтры")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_type = st.selectbox(
                "Тип:",
                ["Все", "regular", "unique", "other"],
                key="filter_prompt_type_phase5"
            )

        with col_f2:
            # Собираем уникальные названия характеристик
            char_names = sorted(list(set(
                p.get('characteristic_name', '') for p in prompts
                if p.get('characteristic_name')
            )))
            filter_options = ["Все характеристики"] + char_names
            filter_characteristic = st.selectbox(
                "Характеристика:",
                filter_options,
                key="filter_characteristic_phase5"
            )

        with col_f3:
            filter_status = st.selectbox(
                "Статус генерации:",
                ["Все", "ожидает", "успешно", "ошибка"],
                key="filter_status_phase5"
            )

        # Применяем фильтры
        filtered_prompts = prompts

        if filter_type != "Все":
            filtered_prompts = [
                p for p in filtered_prompts
                if p.get('type') == filter_type or p.get('block_type') == filter_type
            ]

        if filter_characteristic != "Все характеристики":
            filtered_prompts = [
                p for p in filtered_prompts
                if p.get('characteristic_name') == filter_characteristic
            ]

        if filter_status != "Все":
            status_map = {
                "ожидает": "pending",
                "успешно": "success",
                "ошибка": "error"
            }
            target_status = status_map.get(filter_status)
            filtered_prompts = [
                p for p in filtered_prompts
                if st.session_state.phase5['results'].get(p.get('phase5_id'), {}).get('status') == target_status
            ]


        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            if st.button("✅ Выбрать все", key="select_all_prompts_btn"):
                # Получаем ID всех отфильтрованных промптов
                filtered_ids = [p.get('phase5_id') for p in filtered_prompts if p.get('phase5_id')]

                # Добавляем в выбранные
                for pid in filtered_ids:
                    if pid not in st.session_state.phase5['selected_prompt_ids']:
                        st.session_state.phase5['selected_prompt_ids'].append(pid)

                # Обновляем временные selections для data_editor
                for pid in filtered_ids:
                    st.session_state.temp_selections[pid] = True

                st.session_state.phase5['statistics']['selected'] = len(st.session_state.phase5['selected_prompt_ids'])
                st.rerun()

        with col2:
            if st.button("❌ Снять все", key="deselect_all_prompts_btn"):
                # Получаем ID всех отфильтрованных промптов
                filtered_ids = [p.get('phase5_id') for p in filtered_prompts if p.get('phase5_id')]

                # Удаляем из выбранных
                st.session_state.phase5['selected_prompt_ids'] = [
                    pid for pid in st.session_state.phase5['selected_prompt_ids']
                    if pid not in filtered_ids
                ]

                # Обновляем временные selections для data_editor
                for pid in filtered_ids:
                    st.session_state.temp_selections[pid] = False

                st.session_state.phase5['statistics']['selected'] = len(st.session_state.phase5['selected_prompt_ids'])
                st.rerun()



        with col3:
            if st.button("🗑️ Очистить всё", key="clear_selection_results_btn"):
                data_manager.reset_generation()
                # Очищаем временные selections
                st.session_state.temp_selections = {}
                st.rerun()

        with col4:
            selected_count = st.session_state.phase5['statistics']['selected']
            total_count = st.session_state.phase5['statistics']['total']
            filtered_count = len(filtered_prompts)
            selected_in_filter = sum(1 for p in filtered_prompts
                                     if p.get('phase5_id') in st.session_state.phase5['selected_prompt_ids'])
            st.metric("Выбрано", f"{selected_count}/{total_count}")
            st.caption(f"в фильтре: {selected_in_filter}/{filtered_count}")
        # Таблица промптов с редактируемыми чекбоксами
        if filtered_prompts:
        # Создаем временное хранилище в session_state, если его нет
            if 'temp_selections' not in st.session_state:
                st.session_state.temp_selections = {}

            # Очищаем временные выборы при изменении фильтров
            if st.session_state.get('last_filter_hash') != hash(str(filter_type) + filter_characteristic + filter_status):
                st.session_state.temp_selections = {}
                st.session_state.last_filter_hash = hash(str(filter_type) + filter_characteristic + filter_status)

            # Инициализируем временные выборы из реальных
            for prompt in filtered_prompts:
                prompt_id = prompt.get('phase5_id')
                if prompt_id not in st.session_state.temp_selections:
                    st.session_state.temp_selections[prompt_id] = prompt_id in st.session_state.phase5['selected_prompt_ids']
        # Быстрые действия - РАБОТАЕТ С ФИЛЬТРАМИ

            # Создаем DataFrame для data_editor
            table_data = []
            for prompt in filtered_prompts:
                prompt_id = prompt.get('phase5_id')
                result = st.session_state.phase5['results'].get(prompt_id, {})

                table_data.append({
                    "Выбрать": st.session_state.temp_selections.get(prompt_id, False),
                    "ID": prompt_id[:20] + "..." if len(prompt_id) > 20 else prompt_id,
                    "Тип": prompt.get('type', prompt.get('block_type', 'unknown')),
                    "Характеристика": prompt.get('characteristic_name', prompt.get('block_name', 'N/A')),
                    "Значение": prompt.get('value', 'N/A'),
                    "Промпт №": prompt.get('prompt_num', 1),
                    "Статус": result.get('status', 'pending'),
                    "Токенов": result.get('tokens_used', 0),
                    "prompt_id": prompt_id
                })

            df = pd.DataFrame(table_data)

            # Настраиваем колонки для редактора
            column_config = {
                "Выбрать": st.column_config.CheckboxColumn(
                    "Выбрать",
                    help="Включить в генерацию",
                    default=False,
                ),
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Тип": st.column_config.TextColumn("Тип", width="small"),
                "Характеристика": st.column_config.TextColumn("Характеристика", width="medium"),
                "Значение": st.column_config.TextColumn("Значение", width="medium"),
                "Промпт №": st.column_config.NumberColumn("Промпт №", width="small"),
                "Статус": st.column_config.TextColumn("Статус", width="small"),
                "Токенов": st.column_config.NumberColumn("Токенов", width="small"),
                "prompt_id": st.column_config.Column(disabled=True, width=None)  # Скрытая колонка
            }

            # Отображаем редактор таблицы
            edited_df = st.data_editor(
                df,
                column_config=column_config,
                hide_index=True,
                disabled=["ID", "Тип", "Характеристика", "Значение", "Промпт №", "Статус", "Токенов", "prompt_id"],
                key="prompts_selection_editor_phase5"
            )

            # Обрабатываем изменения чекбоксов
            for idx, row in edited_df.iterrows():
                prompt_id = row['prompt_id']
                is_selected = row['Выбрать']

                # Проверяем, изменилось ли состояние выбора
                if prompt_id:
                    currently_selected = prompt_id in st.session_state.phase5['selected_prompt_ids']
                    if is_selected != currently_selected:
                        data_manager.toggle_prompt_selection(prompt_id)

            # Показываем подсказку
            st.caption("💡 Кликните на чекбоксы в колонке 'Выбрать', чтобы включить/исключить промпты из генерации")

    @staticmethod
    def show_generation_settings():
        """Показать настройки генерации"""
        st.header("⚙️ Настройки генерации")

        with st.expander("Параметры AI", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                # Расширяем список провайдеров
                available_providers = ["openai", "deepseek", "genapi_gemini", "true_gemini"]
                provider_labels = {
                    "openai": "OpenAI / GenAPI (GPT модели)",
                    "deepseek": "DeepSeek",
                    "genapi_gemini": "Gemini через GenAPI.ru (Россия, без VPN)",
                    "true_gemini": "Настоящий Google Gemini (требует VPN)"
                }

                current_provider = st.session_state.phase5['generation_settings'].get('provider', 'deepseek')
                provider = st.selectbox(
                    "Провайдер AI:",
                    available_providers,
                    format_func=lambda x: provider_labels.get(x, x),
                    index=available_providers.index(current_provider) if current_provider in available_providers else 1,
                    key="ai_provider_select_phase5"
                )

                temperature = st.slider(
                    "Temperature:",
                    min_value=0.0,
                    max_value=2.0,
                    value=st.session_state.phase5['generation_settings'].get('temperature', 0.7),
                    step=0.1,
                    key="ai_temperature_phase5"
                )

            with col2:
                # Динамический max_tokens в зависимости от провайдера (Gemini поддерживают больше)
                max_tokens_default = 2000
                max_tokens_max = 16384 if "gemini" in provider else 8000
                max_tokens = st.number_input(
                    "Max Tokens:",
                    min_value=100,
                    max_value=max_tokens_max,
                    value=st.session_state.phase5['generation_settings'].get('max_tokens', max_tokens_default),
                    key="ai_max_tokens_phase5"
                )

                retry_count = st.number_input(
                    "Повторных попыток при ошибке:",
                    min_value=1,
                    max_value=10,
                    value=st.session_state.phase5['generation_settings'].get('retry_count', 3),
                    key="ai_retry_count_phase5"
                )

            # Общая задержка
            delay = st.slider(
                "Задержка между запросами (сек):",
                min_value=0.5,
                max_value=10.0,
                value=st.session_state.phase5['generation_settings'].get('delay_between_requests', 2.0),
                step=0.5,
                key="ai_delay_phase5"
            )

            # Дополнительные предупреждения / поля в зависимости от провайдера
            if provider == "true_gemini":
                st.warning("⚠️ True Gemini требует VPN или зарубежный IP из России. Без него запросы не пройдут.")
            elif provider == "genapi_gemini":
                st.info(
                    "ℹ️ GenAPI Gemini работает без VPN, оплата рублями. Поддерживает синхронный режим по умолчанию.")

            # Кнопка сохранения
            if st.button("💾 Сохранить настройки", key="save_settings_phase5_btn"):
                st.session_state.phase5['generation_settings'].update({
                    'provider': provider,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'retry_count': retry_count,
                    'delay_between_requests': delay
                })
                st.success("Настройки сохранены!")

    @staticmethod
    def show_generation_control(generation_manager: GenerationManager, data_manager: Phase5DataManager):
        """Показать панель управления генерацией"""
        st.header("🚀 Управление генерацией")

        status = st.session_state.phase5['generation_status']
        stats = st.session_state.phase5['statistics']

        # Статистика
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("Всего выбрано", stats['selected'])
        with col_s2:
            st.metric("Успешно", stats['success'])
        with col_s3:
            st.metric("Ошибки", stats['error'])
        with col_s4:
            st.metric("Ожидают", stats['pending'])

        # Прогресс-бар
        progress = generation_manager.get_generation_progress()
        st.progress(progress / 100)
        st.caption(f"Прогресс: {progress}% ({stats['completed']}/{stats['selected']})")

        # Время генерации
        if st.session_state.phase5['generation_start_time']:
            try:
                if isinstance(st.session_state.phase5['generation_start_time'], str):
                    start_time = datetime.fromisoformat(st.session_state.phase5['generation_start_time'])
                else:
                    start_time = st.session_state.phase5['generation_start_time']

                elapsed = datetime.now() - start_time
                st.caption(f"Время работы: {elapsed.seconds // 60}:{elapsed.seconds % 60:02d}")
            except:
                pass

        # Кнопки управления в зависимости от статуса
        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)

        with col_btn1:
            if status in ['idle', 'paused', 'stopped', 'completed', 'error']:
                if st.button("🚀 Начать генерацию", type="primary", key="start_generation_phase5_btn"):
                    generation_manager.start_generation()

        with col_btn2:
            if st.button("⏸️ Пауза", key="pause_generation_phase5_btn"):
                generation_manager.pause_generation()
                st.rerun()

        with col_btn3:
            if st.button("▶️ Продолжить", key="resume_generation_phase5_btn"):
                generation_manager.resume_generation()
                st.rerun()

        with col_btn4:
            if st.button("⏹️ Остановить", key="stop_generation_phase5_btn"):
                generation_manager.stop_generation()
                st.rerun()

        with col_btn5:
            if status in ['completed', 'stopped', 'error']:
                if st.button("🔄 Сбросить результаты", key="reset_generation_phase5_btn"):
                    data_manager.reset_generation()
                    st.rerun()

    @staticmethod
    def show_phase_completion(generation_manager, data_manager):
        """Показать панель завершения фазы 5"""
        st.header("✅ Завершение фазы 5")

        stats = st.session_state.phase5['statistics']

        # Проверяем условия для завершения
        completion_conditions = [
            (stats['selected'] > 0, f"Выбрано промптов: {stats['selected']}/{stats['total']}"),
            (stats['completed'] == stats['selected'], f"Сгенерировано: {stats['completed']}/{stats['selected']}"),
            (stats['error'] == 0 or st.checkbox("Завершить даже с ошибками"),
             f"Ошибки: {stats['error']} (можно игнорировать)")
        ]

        st.write("**Условия завершения:**")
        for condition, description in completion_conditions:
            status = "✅" if condition else "❌"
            st.write(f"{status} {description}")

        # Кнопка завершения
        can_complete = all([cond for cond, _ in completion_conditions[:-1]])  # игнорируем последнее если чекбокс

        if st.button("🏁 Завершить фазу 5 и перейти к фазе 6",
                     type="primary",
                     disabled=not can_complete,
                     key="complete_phase5_btn"):

            if data_manager.complete_phase5_and_prepare_phase6():
                # Меняем текущую фазу в основном приложении
                st.session_state.current_phase = 6
                st.rerun()

    @staticmethod
    def show_results(data_manager: Phase5DataManager):
        st.header("📊 Результаты генерации")
        results = st.session_state.phase5['results']
        stats = st.session_state.phase5['statistics']
        if stats['completed'] == 0:
            st.info("Результаты генерации появятся здесь после запуска генерации.")
            return

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            result_filter = st.selectbox("Фильтр по статусу:", ["Все", "Успешно", "Ошибки"], key="result_filter_phase5")
        with col_f2:
            group_by = st.selectbox("Группировать по:", ["Нет", "Характеристике", "Типу", "Статусу"],
                                    key="result_group_by_phase5")

        filtered_results = []
        for prompt_id, result in results.items():
            if not result.get('ai_response') and result.get('status') == 'pending':
                continue
            if result_filter == "Успешно" and result.get('status') != 'success':
                continue
            elif result_filter == "Ошибки" and result.get('status') != 'error':
                continue
            prompt = data_manager.get_prompt_by_id(prompt_id)
            filtered_results.append({'prompt_id': prompt_id, 'result': result, 'prompt': prompt})

        if group_by != "Нет":
            groups = {}
            for item in filtered_results:
                if group_by == "Характеристике":
                    key = item['prompt'].get('characteristic_name', item['prompt'].get('block_name', 'Другие'))
                elif group_by == "Типу":
                    key = item['prompt'].get('type', item['prompt'].get('block_type', 'unknown'))
                elif group_by == "Статусу":
                    key = item['result'].get('status', 'unknown')
                groups.setdefault(key, []).append(item)

            for group_name, group_items in groups.items():
                with st.expander(f"{group_name} ({len(group_items)} результатов)", expanded=False):
                    Phase5UIComponents._show_results_table(group_items, data_manager)
        else:
            Phase5UIComponents._show_results_table(filtered_results, data_manager)

        # ВЫЗОВ УДАЛЁН: Phase5UIComponents._show_export_options(data_manager)

    @staticmethod
    def _show_results_table(results_items, data_manager):
        """Показать таблицу результатов"""
        for idx, item in enumerate(results_items):  # Исправлено: добавлен idx
            result = item['result']
            prompt = item['prompt']

            # Карточка результата
            if result['status'] == 'success':
                card_class = "result-card"
                status_badge = "✅ Успешно"
            elif result['status'] == 'error':
                card_class = "error-card"
                status_badge = "❌ Ошибка"
            else:
                card_class = "pending-card"
                status_badge = "⏳ Ожидает"

            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                # Информация о промпте
                if prompt:
                    if 'characteristic_name' in prompt:
                        st.write(f"**{prompt['characteristic_name']}** = {prompt.get('value', '')}")
                    else:
                        st.write(f"**Блок:** {prompt.get('block_name', '')}")

                # Модель и токены
                st.caption(f"Модель: {result.get('model', 'N/A')} | "
                           f"Токенов: {result.get('tokens_used', 0)}")

            with col2:
                st.write(status_badge)

            with col3:
                # Кнопки действий
                if result['status'] == 'success':
                    if st.button("👁️ Просмотр", key=f"view_{item['prompt_id']}_{idx}",
                                 use_container_width=False):
                        st.session_state[f"show_preview_{item['prompt_id']}"] = True

                if result['status'] == 'error':
                    if st.button("🔄 Повторить", key=f"retry_{item['prompt_id']}_{idx}",
                                 use_container_width=False):
                        # Сбросить статус для повторной генерации
                        result.update({
                            'status': 'pending',
                            'error_message': None
                        })
                        data_manager._update_statistics()
                        st.rerun()

            # Превью текста (если открыто)
            if st.session_state.get(f"show_preview_{item['prompt_id']}", False):
                st.markdown("---")
                st.write("**Сгенерированный текст:**")

                # Редактируемое поле для текста
                edited_text = st.text_area(
                    "Текст (можно редактировать):",
                    value=result.get('edited_text') or result.get('ai_response', ''),
                    height=150,
                    key=f"edit_{item['prompt_id']}_{idx}"
                )

                # Сохранить изменения
                if edited_text != result.get('edited_text'):
                    result['edited_text'] = edited_text
                    st.success("Изменения сохранены!")

                col_save, col_close = st.columns(2)
                with col_close:
                    if st.button("Закрыть", key=f"close_{item['prompt_id']}_{idx}",
                                 use_container_width=False):
                        st.session_state[f"show_preview_{item['prompt_id']}"] = False
                        st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    @staticmethod
    def _show_export_options(data_manager):
        """Показать опции экспорта"""
        st.subheader("💾 Экспорт результатов")

        col1, col2, col3 = st.columns(3)

        with col1:
            export_format = st.selectbox(
                "Формат экспорта:",
                ["json", "txt", "excel"],  # ← добавлено "excel"
                key="export_format_select_phase5"
            )

        with col2:
            include_edited = st.checkbox(
                "Включить отредактированные тексты",
                value=True,
                key="include_edited_phase5"
            )

        with col3:
            if st.button("📥 Экспортировать результаты", type="primary",
                         key="export_results_phase5_btn"):
                with st.spinner("Экспорт..."):
                    filename = data_manager.save_results_to_file(export_format)
                    if filename:
                        st.success(f"✅ Результаты экспортированы в файл: {filename}")

                        # Предложить скачать
                        if export_format == 'json':
                            with open(filename, 'r', encoding='utf-8') as f:
                                data = f.read()
                            st.download_button(
                                label="Скачать JSON",
                                data=data,
                                file_name=filename,
                                mime="application/json",
                                key="download_json_phase5"
                            )
                        elif export_format == 'txt':
                            with open(filename, 'r', encoding='utf-8') as f:
                                data = f.read()
                            st.download_button(
                                label="Скачать TXT",
                                data=data,
                                file_name=filename,
                                mime="text/plain",
                                key="download_txt_phase5"
                            )
                        elif export_format == 'excel':  # ← новый блок
                            with open(filename, 'rb') as f:
                                data = f.read()
                            st.download_button(
                                label="Скачать Excel",
                                data=data,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_excel_phase5"
                            )

                    else:
                        st.error("Ошибка при экспорте")


# --- Главная функция фазы 5 ---
def main():
    if 'ai_config_manager' not in st.session_state:
        st.session_state.ai_config_manager = AIConfigManager()
    st.set_page_config(
        page_title="Data Harvester - Phase 5: Генерация текстов",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    local_css()
    data_manager = Phase5DataManager()

    # Инициализация менеджеров
    generation_manager = GenerationManager(data_manager)
    ui = Phase5UIComponents()

    # Синхронизируем данные из потока при каждом рендере
    # Обработка результатов из фонового потока
    if 'generation_manager' not in st.session_state:
        st.session_state.generation_manager = GenerationManager(data_manager)

    generation_manager = st.session_state.generation_manager

    # Обрабатываем накопившиеся результаты
    generation_manager.check_and_process_results()

    if generation_manager._worker_thread and generation_manager._worker_thread.is_alive():
        status = st.session_state.phase5.get('generation_status', 'idle')
        if status in ['running', 'paused', 'stopping']:
            st.caption("Генерация идёт в фоне... (кнопки управления активны)")
            time.sleep(0.5)  # было 0.8 → уменьшаем до 0.4–0.6
            st.rerun()

    st.title("🚀 Фаза 5: Генерация текстовых блоков")
    st.markdown("---")

    # Загрузка промптов из фазы 4 (только если еще не загружены)
    if not st.session_state.phase5_prompts:
        with st.spinner("Загрузка промптов из фазы 4..."):
            data_manager.load_prompts_from_phase4()

    # Создаем словарь для быстрого поиска промптов по ID
    if st.session_state.phase5_prompts:
        st.session_state.phase5_prompts_by_id = {
            p.get('phase5_id'): p for p in st.session_state.phase5_prompts
        }



    # Создаём вкладки вместо выпадающего списка
    nav_options = [
        "Выбор промптов",
        "Настройки генерации",
        "Управление генерацией",
        "Результаты",
        "Экспорт"
    ]

    tab1, tab2, tab3, tab4, tab5 = st.tabs(nav_options)

    with tab1:
        ui.show_prompts_selection(data_manager)

    with tab2:
        ui.show_generation_settings()

    with tab3:
        ui.show_generation_control(generation_manager, data_manager)

    with tab4:
        ui.show_results(data_manager)

    with tab5:
        # Раздел экспорта
        st.header("💾 Экспорт результатов")
        if st.session_state.phase5['statistics']['completed'] == 0:
            st.info("Нет данных для экспорта. Сначала сгенерируйте тексты.")
        else:
            Phase5UIComponents._show_export_options(data_manager)

    # Боковая панель (оставляем без изменений)


    # Боковая панель с улучшенным отображением статуса
    with st.sidebar:
        st.header("📊 Статус фазы 5")

        # Информация о загруженных данных
        if st.session_state.phase5_prompts:


            # Статус генерации с цветовой индикацией
            status = st.session_state.phase5.get('generation_status', 'idle')
            status_colors = {
                'idle': '⚪',
                'running': '🟢',
                'paused': '🟡',
                'stopped': '🔴',
                'completed': '✅',
                'error': '❌'
            }
            status_icon = status_colors.get(status, '⚪')
            st.write(f"{status_icon} **Статус:** {status.upper()}")

            # Если есть ошибка, показываем её
            if status == 'error' and 'error_message' in st.session_state.phase5:
                st.error(f"Ошибка: {st.session_state.phase5['error_message']}")

            # Статистика по типам
            types_count = {}
            for p in st.session_state.phase5_prompts:
                t = p.get('type', p.get('block_type', 'unknown'))
                types_count[t] = types_count.get(t, 0) + 1

            with st.expander("Статистика по типам"):
                for t, count in types_count.items():
                    st.write(f"• {t}: {count}")
        else:
            st.warning("⚠️ Промпты не загружены")

        st.divider()

        # Управление данными
        st.header("🗂️ Управление данными")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Загрузить из фазы 4", key="sidebar_load_prompts_btn"):
                data_manager.load_prompts_from_phase4()
                st.rerun()

        with col2:
            if st.button("🗑️ Сбросить все", key="sidebar_reset_all_btn"):
                data_manager.reset_session_data()
                st.rerun()

        st.divider()

        # Быстрая навигация

        # AI настройки


        st.divider()

        # Информация о проекте
        if 'app_data' in st.session_state:
            app_data = st.session_state.app_data
            st.header("📁 Инфо")
            st.write(f"**Категория:** {app_data.get('category', 'Не указана')}")

            if 'phase4' in app_data:
                st.write(f"**Промптов из фазы 4:** {len(app_data['phase4'].get('prompts', []))}")

        # Кнопка принудительного обновления
        st.divider()
        if st.button("🔄 Принудительно обновить статус", key="force_refresh_status"):
            data_manager._update_statistics()
            st.rerun()

    # Основной контент
    st.markdown("---")
    data_manager._update_statistics()
    stats = st.session_state.phase5['statistics']

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Всего промптов", stats['total'])
    with col2:
        st.metric("Выбрано", stats['selected'])
    with col3:
        st.metric("Успешно", stats['success'])
    with col4:
        st.metric("Ошибки", stats['error'])
    with col5:
        st.metric("Ожидают", stats['pending'])

    # Переход к фазе 6
    st.markdown("---")
    st.header("🚀 Переход к фазе 6")

    col1, col2, col3 = st.columns(3)

    with col1:
        can_proceed = stats['selected'] > 0 and stats['completed'] == stats['selected']
        status_text = "✅ Готово к переходу" if can_proceed else "⏳ Завершите генерацию"
        st.write(f"**Статус:** {status_text}")

    with col2:
        if st.button("💾 Сохранить данные для фазы 6",
                     disabled=not can_proceed,
                     key="save_for_phase6_btn"):
            if data_manager.save_to_app_data():
                st.success("Данные сохранены! Теперь можно переходить к фазе 6.")
                st.rerun()

    with col3:
        if st.button("➡️ Перейти к фазе 6",
                     type="primary",
                     disabled=not (can_proceed and 'phase5' in st.session_state.get('app_data', {})),
                     key="goto_phase6_btn"):
            if 'phase5' not in st.session_state.get('app_data', {}):
                st.warning("Сначала сохраните данные кнопкой выше!")
            else:
                st.session_state.current_phase = 6
                st.rerun()

    # Автоматическое сохранение для фазы 6 (если есть результаты)
    if stats['completed'] > 0:
        if 'app_data' not in st.session_state:
            st.session_state.app_data = {}
        st.session_state.app_data['phase5'] = {
            'results': list(st.session_state.phase5['results'].values()),
            'statistics': st.session_state.phase5['statistics'],
            'generation_settings': st.session_state.phase5['generation_settings'],
            'phase_completed': True,
            'completed_at': datetime.now().isoformat(),
            'prompts_count': len(st.session_state.phase5_prompts)

        }

if __name__ == "__main__":
    main()