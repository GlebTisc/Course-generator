import os
from datetime import datetime
import openai
import logging
import re

from app.config import Config
from app.models import FormatResponse

logger = logging.getLogger(__name__)

client = openai.OpenAI(
    base_url=Config.OPENROUTER_BASE_URL,
    api_key=Config.OPENROUTER_API_KEY
)


class ContentFormatter:
    """
    Агент форматирования. Делает ТОЛЬКО одно:
    → принимает сырой текст
    → превращает в чистый Markdown с таблицами в ```table
    → не изменяет сам смысл
    → не ломает LaTeX
    """

    # ================================================================
    # PUBLIC
    # ================================================================
    @staticmethod
    def format_content(content: str, chapter_title: str = "unknown") -> FormatResponse:

        logger.info(f"🎨 Форматирование контента: {chapter_title}")

        prompt = ContentFormatter._build_prompt(content)

        try:
            response = client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are an editor of educational materials."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            formatted = response.choices[0].message.content.strip()

            # Save logs
            ContentFormatter._save_log(chapter_title, content, formatted)

            # Post-process: safe, minimal
            formatted = ContentFormatter._postprocess(formatted)

            return FormatResponse(formatted_content=formatted)

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования: {e}")
            ContentFormatter._save_error(chapter_title, content, str(e))
            return FormatResponse(formatted_content=content)

    # ================================================================
    # PROMPT BUILDER
    # ================================================================
    @staticmethod
    def _build_prompt(content: str) -> str:
        prompt = (
            "You are a strict Markdown cleaning assistant for educational content.\n"
            "Your job is to:\n"
            "1) Convert the input into clean, well-structured Markdown.\n"
            "2) KEEP all valid LaTeX formulas unchanged.\n"
            "3) FIX or REMOVE only invalid LaTeX (parsing errors, incomplete blocks, missing delimiters, KaTeX errors).\n"
            "4) Remove ALL HTML tags.\n"
            "5) Do NOT change the meaning of the text.\n"
            "6) NEVER put LaTeX formulas inside code blocks. LaTeX must always be outside ```...```.\n"
            "7) Check that code blocks have matching triple backticks. If LaTeX is inside, move it outside.\n"
            "8) Check that LaTeX $$…$$ and $…$ blocks are correctly opened and closed.\n"
            "9) REMOVE all tables from the output. Do not include any tables. Tables in input must be deleted.\n"
            "10) NEVER escape or duplicate backslashes inside LaTeX.\n"
            "11) Output only clean Markdown, NO HTML, NO commentary, NO explanations.\n\n"

            "Valid LaTeX examples (must remain exactly the same):\n"
            "  Inline: $a^2 + b^2$\n"
            "  Block:\n"
            "$$\n"
            "\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}\n"
            "$$\n\n"

            "Invalid LaTeX examples (must be FIXED or REMOVED):\n"
            "  - KaTeX parse errors\n"
            "  - Blocks missing a closing $ or $$\n"
            "  - Blocks missing required braces { }\n"
            "  - HTML-wrapped LaTeX with <span>…</span>\n"
            "  - LaTeX inside code blocks\n\n"

            "When fixing invalid LaTeX:\n"
            "  - If the formula is recoverable → fix it.\n"
            "  - If it is partially broken, truncated, or unclear → remove it completely.\n"
            "  - NEVER generate new mathematical content.\n"
            "  - NEVER guess missing mathematical expressions.\n\n"

            "===== TEXT =====\n"
            f"{content}\n"
            "===== END =====\n"
        )
        return prompt

    # ================================================================
    # POSTPROCESSING — максимально аккуратный, безопасный
    # ================================================================
    @staticmethod
    def _postprocess(md: str) -> str:
        # Удаляем HTML
        md = re.sub(r"<[^>]+>", "", md)

        # Убираем тройные пустые строки
        md = re.sub(r"\n\s*\n\s*\n+", "\n\n", md)

        # Удаляем таблицы | ... |
        md = re.sub(r"^\s*\|.*\|\s*$", "", md, flags=re.MULTILINE)

        return md.strip()

    # ================================================================
    # TABLE WRAPPING — исправленная версия
    # ================================================================
    @staticmethod
    def _wrap_raw_tables(md: str) -> str:
        """
        Оборачиваем только реальные таблицы |...| вне LaTeX и блоков кода.
        """
        lines = md.splitlines()
        result = []
        buffer = []

        def is_table_row(line: str) -> bool:
            line_strip = line.strip()
            return line_strip.startswith("|") and line_strip.endswith("|")

        inside_code = False
        inside_latex = False

        for line in lines:
            # Определяем начало/конец код-блока
            if line.strip().startswith("```"):
                inside_code = not inside_code

            # Определяем начало/конец display LaTeX $$…$$
            if "$$" in line:
                inside_latex = not inside_latex

            if not inside_code and not inside_latex and is_table_row(line):
                buffer.append(line)
            else:
                if buffer:
                    result.append("```table")
                    result.extend(buffer)
                    result.append("```")
                    buffer = []
                result.append(line)

        # На случай, если таблица в конце
        if buffer:
            result.append("```table")
            result.extend(buffer)
            result.append("```")

        return "\n".join(result)

    # ================================================================
    # LOGGING
    # ================================================================
    @staticmethod
    def _save_log(chapter: str, original: str, formatted: str):
        directory = "content_logs/formatter"
        os.makedirs(directory, exist_ok=True)

        safe = re.sub(r'[^\w\-_.]', "_", chapter)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        path = f"{directory}/{safe}_{ts}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("=== ORIGINAL ===\n")
            f.write(original)
            f.write("\n\n=== FORMATTED ===\n")
            f.write(formatted)

    @staticmethod
    def _save_error(chapter: str, content: str, error: str):
        directory = "content_logs/errors"
        os.makedirs(directory, exist_ok=True)

        safe = re.sub(r'[^\w\-_.]', "_", chapter)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        path = f"{directory}/error_{safe}_{ts}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"ERROR: {error}\n\n")
            f.write(content)
