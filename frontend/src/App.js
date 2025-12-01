import React, { useState } from 'react';
import CourseGenerator from './components/CourseGenerator';
import CourseViewer from './components/CourseViewer';
import TutorChat from './components/TutorChat';
import LoadingSpinner from './components/LoadingSpinner';
import { courseAPI } from './services/api';
import './App.css';

function App() {
  const [course, setCourse] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isTutorOpen, setIsTutorOpen] = useState(false);
  const [currentLesson, setCurrentLesson] = useState(null);

  const handleGenerateCourse = async (topic) => {
    setIsLoading(true);
    try {
      const generatedCourse = await courseAPI.generateCourse(topic);
      setCourse(generatedCourse);
    } catch (error) {
      alert('Ошибка при генерации курса. Попробуйте еще раз.');
      console.error('Error generating course:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAskTutor = (lesson) => {
    setCurrentLesson(lesson);
    setIsTutorOpen(true);
  };

  const getCourseContext = () => {
    if (!course) return {};

    return {
      title: course.skeleton.title,
      description: course.skeleton.description,
      content: course.content
    };
  };

  return (
    <div className="App">
      <div className="app-container">
        {!course && !isLoading && (
          <CourseGenerator
            onCourseGenerated={handleGenerateCourse}
            isLoading={isLoading}
          />
        )}

        {isLoading && (
          <LoadingSpinner message="Генерируем ваш курс... Это может занять несколько минут" />
        )}

        {course && !isLoading && (
          <CourseViewer
            course={course}
            onAskTutor={handleAskTutor}
          />
        )}

        <TutorChat
          isOpen={isTutorOpen}
          onClose={() => setIsTutorOpen(false)}
          courseContext={getCourseContext()}
        />

        {course && (
          <button
            className="floating-tutor-button"
            onClick={() => setIsTutorOpen(true)}
          >
            🤖 Репетитор
          </button>
        )}
      </div>
    </div>
  );
}

export default App;