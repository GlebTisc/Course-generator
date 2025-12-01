## Установка
1) Клонируйте репозиторий
2) Установите зависимости (frontend - npm install; app - pip install -r requirements.txt)
### Структура файла .env
OPENROUTER_API_KEY=ключ  
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1  
MODEL_NAME=модель (к примеру x-ai/grok-4.1-fast:free)  

## Запуск
1) app - python -m app.main
2) frontend - npm start
  
После удачного запуска в поле "Название курса" введите курс, который вы бы хотели почитать и нажмите на кнопку "Создать курс" (среднее время генерации курса - 10 минут).
