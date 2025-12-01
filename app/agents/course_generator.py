import openai
from app.config import Config
from app.models import CourseSkeleton, Chapter
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = openai.OpenAI(
    base_url=Config.OPENROUTER_BASE_URL,
    api_key=Config.OPENROUTER_API_KEY
)


class CourseGenerator:
    @staticmethod
    def generate_skeleton(topic: str) -> CourseSkeleton:
        logger.info(f"🔄 Начинаем генерацию структуры курса для темы: {topic}")

        prompt = f"""
        Создай структуру курса по теме: "{topic}".

        Верни ответ в формате JSON:
        {{
            "title": "Название курса",
            "description": "Описание курса",
            "chapters": [
                {{
                    "title": "Название главы",
                    "description": "Описание главы"
                }}
            ]
        }}

        Создай 5-7 глав, которые логически переходят от основ к продвинутым темам.
        """

        try:
            logger.info(f"📨 Отправляем запрос к API OpenRouter с моделью: {Config.MODEL_NAME}")
            logger.debug(f"Промпт: {prompt}")

            response = client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            logger.info("✅ Получен ответ от API")
            content = response.choices[0].message.content
            logger.debug(f"Сырой ответ от API: {content}")

            # Извлекаем JSON из ответа
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                logger.warning("❌ Не удалось найти JSON в ответе, используем fallback")
                raise ValueError("JSON not found in response")

            json_str = content[json_start:json_end]
            logger.debug(f"Извлеченный JSON: {json_str}")

            data = json.loads(json_str)
            logger.info(f"📚 Успешно распарсен JSON, глав: {len(data['chapters'])}")

            chapters = [
                Chapter(title=chap["title"], description=chap["description"])
                for chap in data["chapters"]
            ]

            result = CourseSkeleton(
                title=data["title"],
                description=data["description"],
                chapters=chapters
            )

            logger.info(f"✅ Структура курса создана: {result.title}")
            logger.debug(f"Детали курса: {result}")

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации структуры курса: {str(e)}")
            logger.exception(e)

            # Fallback структура
            fallback = CourseSkeleton(
                title=f"Курс по {topic}",
                description=f"Изучение основных аспектов {topic}",
                chapters=[
                    Chapter(title="Введение", description="Основные понятия и принципы"),
                    Chapter(title="Базовые концепции", description="Фундаментальные идеи"),
                    Chapter(title="Практическое применение", description="Реальные примеры"),
                    Chapter(title="Продвинутые темы", description="Углубленное изучение"),
                    Chapter(title="Заключение", description="Итоги и дальнейшие шаги")
                ]
            )

            logger.info("🔄 Используем fallback структуру курса")
            return fallback