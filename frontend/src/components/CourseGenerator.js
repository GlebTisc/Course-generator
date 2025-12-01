import React, { useState } from 'react';
import { BookOpen, Sparkles } from 'lucide-react';
import './CourseGenerator.css';

const CourseGenerator = ({ onCourseGenerated, isLoading }) => {
  const [topic, setTopic] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (topic.trim()) {
      onCourseGenerated(topic.trim());
    }
  };

  return (
    <div className="course-generator">
      <div className="generator-header">
        <BookOpen className="header-icon" size={48} />
        <h1>Генератор учебных курсов</h1>
        <p>Создайте персонализированный курс по любой теме с встроенным репетитором</p>
      </div>

      <form onSubmit={handleSubmit} className="generator-form">
        <div className="input-group">
          <label htmlFor="topic">Введите тему курса:</label>
          <input
            id="topic"
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Например: Машинное обучение, Веб-разработка, Финансы..."
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          className="generate-button"
          disabled={!topic.trim() || isLoading}
        >
          <Sparkles size={20} />
          {isLoading ? 'Генерируем...' : 'Создать курс'}
        </button>
      </form>

      <div className="features">
        <div className="feature">
          <div className="feature-icon">📚</div>
          <h3>Структурированный курс</h3>
          <p>Логические главы от основ к продвинутым темам</p>
        </div>
        <div className="feature">
          <div className="feature-icon">📝</div>
          <h3>Теоретический материал</h3>
          <p>Подробные объяснения и примеры для каждой темы</p>
        </div>
        <div className="feature">
          <div className="feature-icon">🎯</div>
          <h3>Проверка знаний</h3>
          <p>Тесты и вопросы для закрепления материала</p>
        </div>
        <div className="feature">
          <div className="feature-icon">🤖</div>
          <h3>AI-репетитор</h3>
          <p>Ответы на вопросы по материалам курса</p>
        </div>
      </div>
    </div>
  );
};

export default CourseGenerator;