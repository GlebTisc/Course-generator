from pydantic import BaseModel
from typing import List, Dict, Optional

class CourseRequest(BaseModel):
    topic: str

class Chapter(BaseModel):
    title: str
    description: str

class CourseSkeleton(BaseModel):
    title: str
    description: str
    chapters: List[Chapter]

class LessonContent(BaseModel):
    chapter_title: str
    content: str
    key_points: List[str]

class Question(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str

class Quiz(BaseModel):
    chapter_title: str
    questions: List[Question]

class TutorQuestion(BaseModel):
    question: str
    course_content: dict

class TutorResponse(BaseModel):
    answer: str
    sources: List[str]

class FormatRequest(BaseModel):
    content: str

class FormatResponse(BaseModel):
    formatted_content: str

class FullCourse(BaseModel):
    topic: str
    skeleton: CourseSkeleton
    content: List[LessonContent]
    quizzes: List[Quiz]