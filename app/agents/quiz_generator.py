import openai
from app.config import Config
from app.models import Question, Quiz, LessonContent
import json
import logging
import time

logger = logging.getLogger(__name__)

client = openai.OpenAI(
    base_url=Config.OPENROUTER_BASE_URL,
    api_key=Config.OPENROUTER_API_KEY
)


class QuizGenerator:
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # секунды между попытками

    @staticmethod
    def generate_quiz(lesson_content: LessonContent) -> Quiz:
        logger.info(f"🎯 Генерируем тест для главы: {lesson_content.chapter_title}")

        prompt_template = (
            "На основе учебного материала создай тест из 3 вопросов для студентов.\n"
            "Вопросы должны проверять понимание материала, включая формулы, определения и ключевые моменты.\n"
            "Используй LaTeX для всех формул (например, $\\lim_{x \\to a} f(x) = L$ или $\\varepsilon$).\n\n"
            f"Глава: {lesson_content.chapter_title}\n"
            f"Материал: {lesson_content.content[:500]}...\n"
            f"Ключевые моменты: {', '.join(lesson_content.key_points)}\n\n"
            "Верни только валидный JSON, без объяснений или текста вокруг. Все строки и ключи должны быть в двойных кавычках.\n"
            '{'
            f'"chapter_title": "{lesson_content.chapter_title}",'
            '"questions": [' 
            '{'
            '"question": "Текст вопроса",'
            '"options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],'
            '"correct_answer": "Правильный вариант",'
            '"explanation": "Объяснение правильного ответа, включая формулы, если нужно"'
            '}'
            ']'
            '}'
        )

        for attempt in range(QuizGenerator.MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=Config.MODEL_NAME,
                    messages=[{"role": "user", "content": prompt_template}],
                    temperature=0.7
                )

                content = response.choices[0].message.content
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start == -1 or json_end == 0:
                    raise ValueError("JSON not found in quiz response")

                data = json.loads(content[json_start:json_end])

                questions = []
                for q in data.get('questions', []):
                    if all(k in q for k in ['question', 'options', 'correct_answer', 'explanation']):
                        questions.append(Question(
                            question=q["question"],
                            options=q["options"],
                            correct_answer=q["correct_answer"],
                            explanation=q["explanation"]
                        ))

                if not questions:
                    raise ValueError("No valid questions created")

                return Quiz(chapter_title=data["chapter_title"], questions=questions)

            except Exception as e:
                logger.error(f"❌ Ошибка генерации JSON (попытка {attempt + 1}): {str(e)}")
                if attempt < QuizGenerator.MAX_RETRIES - 1:
                    logger.info(f"🔄 Повторная попытка через {QuizGenerator.RETRY_DELAY} сек...")
                    time.sleep(QuizGenerator.RETRY_DELAY)
                else:
                    logger.warning("⚠️ Максимальное число попыток исчерпано. Возвращаем fallback-тест.")

        # fallback quiz, если все попытки неудачны
        fallback = Quiz(
            chapter_title=lesson_content.chapter_title,
            questions=[Question(
                question=f"Основная тема главы '{lesson_content.chapter_title}'?",
                options=["Тема A", "Тема B", "Тема C", "Тема D"],
                correct_answer="Тема A",
                explanation="Эта тема является основной для данной главы"
            )]
        )
        return fallback
