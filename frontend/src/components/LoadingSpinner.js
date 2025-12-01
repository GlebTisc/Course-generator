import React from 'react';
import { Loader } from 'lucide-react';
import './LoadingSpinner.css';

const LoadingSpinner = ({ message = "Генерируем курс..." }) => {
  return (
    <div className="loading-spinner">
      <Loader className="spinner-icon" size={48} />
      <p className="loading-message">{message}</p>
    </div>
  );
};

export default LoadingSpinner;