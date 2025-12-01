import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const courseAPI = {
  generateCourse: async (topic) => {
    const response = await api.post('/generate-course', { topic });
    return response.data;
  },

  askTutor: async (question, courseContent) => {
    const response = await api.post('/ask-tutor', {
      question,
      course_content: courseContent
    });
    return response.data;
  }
};

export default api;