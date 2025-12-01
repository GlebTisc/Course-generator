from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import CourseRequest, FullCourse, TutorQuestion, TutorResponse, FormatRequest, FormatResponse
from app.agents.course_generator import CourseGenerator
from app.agents.content_generator import ContentGenerator
from app.agents.quiz_generator import QuizGenerator
from app.agents.tutor_agent import TutorAgent
from app.agents.content_formatter import ContentFormatter
import logging
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Course Generator API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate-course", response_model=FullCourse)
async def generate_course(request: CourseRequest):
    start_time = time.time()
    logger.info(f"🚀 Начало генерации курса для темы: '{request.topic}'")

    try:
        # 1. Генерация структуры курса
        logger.info("📋 Этап 1: Генерация структуры курса")
        skeleton = CourseGenerator.generate_skeleton(request.topic)
        logger.info(f"✅ Структура создана: {skeleton.title}")

        # 2. Генерация контента для каждой главы
        logger.info(f"📖 Этап 2: Генерация контента для {len(skeleton.chapters)} глав")
        content = []
        for i, chapter in enumerate(skeleton.chapters):
            logger.info(f"🔹 Генерация контента для главы {i + 1}: {chapter.title}")
            lesson_content = ContentGenerator.generate_lesson_content(chapter)
            content.append(lesson_content)

        # 3. Генерация тестов для каждой главы
        logger.info("🎯 Этап 3: Генерация тестов")
        quizzes = []
        for i, lesson in enumerate(content):
            logger.info(f"🔹 Генерация теста для главы {i + 1}: {lesson.chapter_title}")
            quiz = QuizGenerator.generate_quiz(lesson)
            quizzes.append(quiz)

        result = FullCourse(
            topic=request.topic,
            skeleton=skeleton,
            content=content,
            quizzes=quizzes
        )

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"✅ Курс успешно создан за {duration:.2f} секунд")
        logger.info(f"📊 Итоги: {len(skeleton.chapters)} глав, {len(content)} уроков, {len(quizzes)} тестов")

        return result

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при генерации курса: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask-tutor", response_model=TutorResponse)
async def ask_tutor(question: TutorQuestion):
    logger.info(f"🤖 Запрос к репетитору: '{question.question}'")

    try:
        response = TutorAgent.answer_question(
            question.question,
            question.course_content
        )
        logger.info("✅ Ответ репетитора готов")
        return response
    except Exception as e:
        logger.error(f"❌ Ошибка при работе репетитора: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/format-content", response_model=FormatResponse)
async def format_content(request: FormatRequest):
    """
    Отдельный эндпоинт для форматирования контента
    Полезен для отладки и переформатирования существующего контента
    """
    logger.info("🎨 Запрос на форматирование контента")

    try:
        response = ContentFormatter.format_content(request.content)
        logger.info("✅ Контент отформатирован")
        return response
    except Exception as e:
        logger.error(f"❌ Ошибка при форматировании контента: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    logger.info("📡 Получен запрос к корневому эндпоинту")
    return {"message": "Course Generator API"}


@app.get("/health")
async def health_check():
    logger.debug("🔍 Health check")
    return {"status": "healthy", "service": "Course Generator API"}


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Запуск сервера Course Generator API")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")