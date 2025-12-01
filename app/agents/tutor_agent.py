import openai
from app.config import Config
from app.models import TutorResponse
import logging

logger = logging.getLogger(__name__)

client = openai.OpenAI(
    base_url=Config.OPENROUTER_BASE_URL,
    api_key=Config.OPENROUTER_API_KEY
)


class TutorAgent:
    @staticmethod
    def answer_question(question: str, course_content: dict) -> TutorResponse:
        logger.info(f"🤖 Репетитор получает вопрос: {question}")
        logger.debug(f"Контекст курса: {course_content.get('title', 'No title')}")

        # Создаем контекст из содержания курса
        context = f"Курс: {course_content.get('title', '')}\n"
        context += f"Описание: {course_content.get('description', '')}\n\n"

        if 'content' in course_content:
            context += "Содержание курса:\n"
            for i, lesson in enumerate(course_content['content']):
                context += f"\nГлава {i + 1}: {lesson['chapter_title']}\n"
                context += f"Ключевые моменты: {', '.join(lesson['key_points'])}\n"
                # Ограничиваем длину контента для промпта
                short_content = lesson['content'][:200] + "..." if len(lesson['content']) > 200 else lesson['content']
                context += f"Содержание: {short_content}\n"

        logger.debug(f"Длина контекста: {len(context)} символов")
        logger.debug(f"Количество глав в контексте: {len(course_content.get('content', []))}")

        prompt = f"""
        You are an experienced tutor. Your goal is to explain the topic to the student in a clear, structured and helpful way, based strictly on the course materials.

VERY IMPORTANT:
- ALWAYS answer in Russian.
- Use ONLY VALID LaTeX for all mathematical expressions.
  - Inline formulas: $…$
  - Block formulas: $$…$$
- Never use HTML.
- Never place LaTeX inside code blocks.
- Do NOT generate tables.
- Do NOT leave incomplete or cut-off text.
- Do NOT invent information that is not in the course context.
- Your answer MUST be a complete, but short and strict to the point explanation. Target length: 400–500 tokens.
Do not end the answer early. Do not leave any unfinished formulas, lists, or sections.
If you approach the token limit, summarize the remaining information and finish cleanly.

Your answer must have TWO parts:

1. **Полное понятное объяснение**  
   - Explain the concept clearly and step-by-step.  
   - If appropriate, include examples or simple derivations using LaTeX.  
   - Imagine you are teaching a student who wants to understand the topic deeply.

2. **Краткая ссылка на материалы курса**  
   - In one short sentence at the end:  
     “Эта тема рассматривается в главах X, Y.”  
   - Only list chapters that truly contain relevant material.

Course context:
{context}

Student question:
{question}

Now provide a full, helpful answer in Russian.
        """

        try:
            logger.info("📨 Отправляем вопрос репетитору в API")
            logger.debug(f"Длина промпта: {len(prompt)} символов")

            response = client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=750
            )

            logger.info("✅ Получен ответ от репетитора")
            answer = response.choices[0].message.content
            logger.debug(f"Ответ репетитора (первые 200 символов): {answer[:200]}...")

            # Извлекаем источники из ответа
            sources = []

            result = TutorResponse(
                answer=answer,
                sources=sources
            )

            logger.info(f"✅ Ответ репетитора готов, источников: {len(sources)}")
            logger.debug(f"Источники: {sources}")

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка при получении ответа от репетитора: {str(e)}")
            logger.exception(e)

            fallback = TutorResponse(
                answer="Извините, не могу ответить на вопрос в данный момент. Пожалуйста, попробуйте позже или переформулируйте вопрос.",
                sources=[]
            )

            logger.info("🔄 Используем fallback ответ репетитора")
            return fallback