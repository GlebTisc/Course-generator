import traceback

import openai
import json
import logging
import re
import os
from datetime import datetime

from app.config import Config
from app.models import LessonContent, Chapter
from app.agents.content_formatter import ContentFormatter

logger = logging.getLogger(__name__)

client = openai.OpenAI(
    base_url=Config.OPENROUTER_BASE_URL,
    api_key=Config.OPENROUTER_API_KEY
)


class ContentGenerator:

    # ================================================================
    # PUBLIC API
    # ================================================================
    @staticmethod
    def generate_lesson_content(chapter: Chapter, max_retries: int = 3) -> LessonContent:
        """
        Генерирует учебный материал.
        1) Получает JSON с неотформатированным контентом.
        2) Отправляет контент в ContentFormatter.
        3) Проверяет качество форматирования.
        4) Перезапрашивает форматирование до идеального результата.
        """

        logger.info(f"📘 Генерация контента для главы: {chapter.title}")

        raw_json = ContentGenerator._generate_json_with_retries(chapter, max_retries)

        logger.info("🎨 Форматируем контент…")
        formatted_content = ContentGenerator._format_until_valid(
            raw_json["content"],
            chapter_title=chapter.title
        )

        return LessonContent(
            chapter_title=raw_json["chapter_title"],
            content=formatted_content,
            key_points=[],
        )

    # ================================================================
    # STEP 1 — НАДЁЖНАЯ ГЕНЕРАЦИЯ JSON
    # ================================================================
    @staticmethod
    def _generate_json_with_retries(chapter: Chapter, max_retries: int) -> dict:
        for attempt in range(max_retries + 1):
            try:
                prompt = ContentGenerator._create_prompt(chapter)

                response = client.chat.completions.create(
                    model=Config.MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an AI that generates educational content. "
                                "Output must be STRICTLY VALID JSON. "
                                "Absolutely NO text outside the JSON object. "
                                "Follow all instructions exactly."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2 if attempt == 0 else 0.1,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content
                ContentGenerator._save_raw("json", content, chapter.title, attempt)

                data = json.loads(content)
                ContentGenerator._validate_json_structure(data)

                return data

            except Exception as e:
                logger.error(f"❌ Ошибка генерации JSON (попытка {attempt}): {e}")
                if attempt == max_retries:
                    break

        logger.warning("⚠ JSON так и не удалось сгенерировать корректно → fallback")
        return ContentGenerator._fallback_json(chapter)

    # ================================================================
    # STEP 2 — МНОГОКРАТНОЕ ФОРМАТИРОВАНИЕ ПОКА НЕ БУДЕТ КАЧЕСТВЕННО
    # ================================================================
    @staticmethod
    def _format_until_valid(text: str, chapter_title: str, passes: int = 10) -> str:
        """
        Форматирует контент до идеального состояния.
        Логирует все причины повторного форматирования.
        """
        for attempt in range(passes):
            try:
                formatted = ContentFormatter.format_content(text, chapter_title).formatted_content

                logger.info(f"🎨 Попытка {attempt + 1} форматирования ({chapter_title})")
                logger.info(f"Длина текста: {len(formatted)} символов")
                logger.debug(f"Первые 500 символов:\n{formatted[:500]}")

                if ContentGenerator._is_content_valid(formatted):
                    logger.info("✅ Контент идеально отформатирован")
                    return formatted

                logger.warning(f"⚠ Контент невалидный на попытке {attempt + 1}")
                issues = ContentGenerator._describe_issues(formatted)
                logger.warning(f"Проблемы:\n{issues}")

                # повторно форматируем текст
                text = formatted

            except Exception as e:
                logger.error(f"❌ Ошибка форматирования на попытке {attempt + 1}: {e}")
                logger.error(traceback.format_exc())
                logger.debug(f"Текст, вызвавший ошибку:\n{text[:500]}")

        logger.error("❌ Контент так и не удалось идеально отформатировать → отдаём последний вариант")
        return text

    # ================================================================
    # VALIDATION
    # ================================================================
    @staticmethod
    def _validate_json_structure(data: dict):
        required = ["chapter_title", "content"]  # key_points больше не обязательно
        for key in required:
            if key not in data:
                raise ValueError(f"В JSON отсутствует поле: {key}")

        # Если key_points есть, проверяем что это список
        if "key_points" in data and not isinstance(data["key_points"], list):
            raise ValueError("key_points должен быть списком")

        # Если key_points нет, добавляем пустой список для совместимости
        if "key_points" not in data:
            data["key_points"] = []

    # ================================================================
    # VALIDATION — исправленная версия
    # ================================================================
    @staticmethod
    def _is_content_valid(text: str) -> bool:
        """
        Проверка форматирования без таблиц вне блоков кода и LaTeX.
        Возвращает True если валидно, иначе False.
        """
        try:
            # Убираем все LaTeX блоки
            cleaned = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
            cleaned = re.sub(r"\$.*?\$", "", cleaned, flags=re.DOTALL)

            # Убираем все код-блоки ```...```
            cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)

            # Проверка на символы | (таблицы)
            if "|" in cleaned:
                logger.debug("❌ Найдены запрещённые символы | вне блоков → таблица не допускается")
                return False

            # Проверка LaTeX
            if ContentGenerator._latex_has_errors(text):
                logger.debug("❌ Некорректные LaTeX формулы")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки контента: {e}")
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def _latex_has_errors(text: str) -> bool:
        """
        Простейшая проверка LaTeX: в блоках display или inline должны быть \
        Можно расширять проверку позже.
        """
        try:
            latex_blocks = re.findall(r"\${1,2}(.+?)\${1,2}", text, flags=re.DOTALL)
            for block in latex_blocks:
                # хотя бы базовая проверка — есть ли обратный слеш
                if "\\" not in block:
                    logger.debug(f"⚠ Блок LaTeX без обратного слеша: {block[:50]}...")
                    # не считаем критической ошибкой, просто предупреждаем
            return False  # не блокируем текст из-за этого
        except Exception as e:
            logger.error(f"❌ Ошибка проверки LaTeX: {e}")
            logger.error(traceback.format_exc())
            return True

    @staticmethod
    def _describe_issues(text: str) -> str:
        """
        Возвращает строку с причинами, по которым контент может быть невалидным.
        """
        issues = []

        # Проверка на |
        cleaned = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
        cleaned = re.sub(r"\$.*?\$", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
        if "|" in cleaned:
            issues.append("Найдены символы | вне блоков → таблица не допускается")

        # Проверка длины LaTeX блоков
        latex_blocks = re.findall(r"\${1,2}(.+?)\${1,2}", text, flags=re.DOTALL)
        for block in latex_blocks:
            if len(block.strip()) == 0:
                issues.append("Пустой LaTeX блок")

        return "\n".join(issues) if issues else "Не выявлено явных проблем"

    # ================================================================
    # FALLBACK
    # ================================================================
    @staticmethod
    def _fallback_json(chapter: Chapter) -> dict:
        return {
            "chapter_title": chapter.title,
            "content": f"# {chapter.title}\n\n{chapter.description}\n\nМатериал временно недоступен.",
            "key_points": [
                "Основные понятия",
                "Важные элементы",
                "Практическое применение"
            ]
        }

    # ================================================================
    # PROMPT
    # ================================================================
    @staticmethod
    def _create_prompt(chapter: Chapter) -> str:
        return f"""
    Generate educational content in STRICTLY VALID JSON format.

    IMPORTANT: The response MUST be a VALID JSON object.

    JSON FORMAT:
    {{
      "chapter_title": "{chapter.title}",
      "content": "Markdown text (structured, detailed, WITHOUT tables)"
    }}

    CONTENT REQUIREMENTS:
    - Only use Markdown.
    - Absolutely NO tables.
    - Formulas should use LaTeX syntax: $...$ for inline, $$...$$ for block.
    - The content must be detailed, well-structured, and written in RUSSIAN.
    - Include lists, headers, and formatting as appropriate.
    - The content Must Be written in Russian

    RESPONSE:
    - Only JSON. No extra text or explanations outside JSON.
        """

    # ================================================================
    # LOGGING
    # ================================================================
    @staticmethod
    def _save_raw(prefix: str, content: str, chapter: str, attempt: int):
        try:
            base = "content_logs"
            os.makedirs(base, exist_ok=True)

            safe = re.sub(r'[^\w\-_.]', '_', chapter)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            path = os.path.join(base, f"{prefix}_{safe}_attempt{attempt}_{ts}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            logger.error(f"Ошибка сохранения лога: {e}")
