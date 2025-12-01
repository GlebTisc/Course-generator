import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { InlineMath, BlockMath } from 'react-katex';
import { Send, Bot, User, X } from 'lucide-react';
import { courseAPI } from '../services/api';
import './TutorChat.css';

// Декодируем HTML сущности
const decodeHtml = (html) => {
  const txt = document.createElement("textarea");
  txt.innerHTML = html;
  return txt.value;
};

const TutorChat = ({ isOpen, onClose, courseContext }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // -------------------------
  // Разбор текста на inline и block формулы
  // -------------------------
  const parseMathParts = (text) => {
      if (text === undefined || text === null) return [{ type: 'text', content: '' }];

      if (typeof text !== 'string') {
        if (Array.isArray(text)) return text.flatMap(parseMathParts);
        if (React.isValidElement(text)) return parseMathParts(text.props.children);
        // на всякий случай приводим к строке
        return [{ type: 'text', content: String(text) }];
      }

      // убираем \ce
      text = text.replace(/\\ce(?=\{)/g, '');

      const parts = [];
      const regex = /(\$\$[\s\S]+?\$\$)|(\$[^$\n][^\$]*\$)/g;
      let lastIndex = 0;
      let match;

      while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIndex) parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });

        const token = match[0];
        if (token.startsWith('$$')) parts.push({ type: 'block', content: token.slice(2, -2) });
        else parts.push({ type: 'inline', content: token.slice(1, -1) });

        lastIndex = match.index + token.length;
      }

      if (lastIndex < text.length) parts.push({ type: 'text', content: text.slice(lastIndex) });

      return parts;
    };

    const renderMathParts = (text) => {
      if (text === undefined || text === null) return null;
      return parseMathParts(text).map((p, i) => {
        if (p.type === 'text') return <React.Fragment key={i}>{p.content}</React.Fragment>;
        if (p.type === 'inline') return <InlineMath key={i} math={p.content} />;
        if (p.type === 'block') return <div key={i} style={{ margin: '0.75rem 0' }}><BlockMath math={p.content} /></div>;
        return null;
      });
    };


  const renderMarkdownWithMath = (text) => {
    if (!text) return null;
    const decoded = decodeHtml(text);

    if (decoded.includes('class="katex"') || decoded.includes('<math')) {
      return <div dangerouslySetInnerHTML={{ __html: decoded }} />;
    }

    return (
        <ReactMarkdown
          components={{
            p: ({ children }) => <div style={{ marginBottom: '1em' }}>{renderMathParts(children)}</div>,
            li: ({ children }) => <li>{renderMathParts(children)}</li>,
            h1: ({ children }) => <h1>{renderMathParts(children)}</h1>,
            h2: ({ children }) => <h2>{renderMathParts(children)}</h2>,
            h3: ({ children }) => <h3>{renderMathParts(children)}</h3>,
            h4: ({ children }) => <h4>{renderMathParts(children)}</h4>,
            strong: ({ children }) => <strong>{renderMathParts(children)}</strong>,
            em: ({ children }) => <em>{renderMathParts(children)}</em>,
            code: ({ inline, children }) => {
              const str = String(children);
              if (inline && str.startsWith('$') && str.endsWith('$')) {
                return <InlineMath math={str.slice(1, -1)} />;
              }
              if (!inline && str.startsWith('$$') && str.endsWith('$$')) {
                return <BlockMath math={str.slice(2, -2)} />;
              }
              return <code>{children}</code>;
            },
          }}
        >
          {decoded}
        </ReactMarkdown>
      );
    };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setMessages((prev) => [...prev, { type: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await courseAPI.askTutor(userMessage, courseContext);
      setMessages((prev) => [
        ...prev,
        {
          type: 'assistant',
          content: response.answer,
          sources: response.sources,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          type: 'assistant',
          content: 'Извините, произошла ошибка. Попробуйте еще раз.',
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="tutor-chat-overlay">
      <div className="tutor-chat">
        <div className="chat-header">
          <div className="chat-title">
            <Bot size={24} />
            <h3>AI-репетитор</h3>
          </div>
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <Bot size={48} className="welcome-icon" />
              <h4>Привет! Я ваш AI-репетитор</h4>
              <div>Задавайте вопросы по материалам курса, и я помогу вам разобраться в теме</div>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`message ${message.type} ${message.isError ? 'error' : ''}`}>
              <div className="message-avatar">
                {message.type === 'user' ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className="message-content">
                <div className="message-text">{renderMarkdownWithMath(message.content)}</div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="message assistant">
              <div className="message-avatar"><Bot size={16} /></div>
              <div className="message-content">
                <div className="typing-indicator"><span></span><span></span><span></span></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} className="chat-input">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Задайте вопрос по курсу..."
            disabled={isLoading}
          />
          <button type="submit" disabled={!inputMessage.trim() || isLoading}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default TutorChat;
