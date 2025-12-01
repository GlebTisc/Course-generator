// CourseViewer.js
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import 'katex/dist/katex.min.css';
import katex from "katex";
import { InlineMath, BlockMath } from 'react-katex';
import { Book, FileText, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react';
import './CourseViewer.css';

const CourseViewer = ({ course, onAskTutor }) => {
  const [expandedChapters, setExpandedChapters] = useState({});
  const [activeTab, setActiveTab] = useState('content');
  const [selectedAnswers, setSelectedAnswers] = useState({});

  const toggleChapter = (chapterIndex) => {
    setExpandedChapters(prev => ({ ...prev, [chapterIndex]: !prev[chapterIndex] }));
  };

  // --- Безопасный рендер inline ---
    const safeInline = (latex) => {
      try {
        // 1-я попытка
        return <InlineMath math={latex} />;
      } catch (e1) {
        try {
          // 2-я попытка (можно добавить cleanup)
          katex.renderToString(latex, { throwOnError: true });
          return <InlineMath math={latex} />;
        } catch (e2) {
          console.warn("LATEX inline parse failed:", latex);
          return null; // НЕ РЕНДЕРИМ
        }
      }
    };

    // --- Безопасный рендер block ---
    const safeBlock = (latex) => {
      try {
        return <BlockMath math={latex} />;
      } catch (e1) {
        try {
          katex.renderToString(latex, { throwOnError: true });
          return <BlockMath math={latex} />;
        } catch (e2) {
          console.warn("LATEX block parse failed:", latex);
          return null;
        }
      }
    };

    // -----------------------
    // УДАЛЕНИЕ MARKDOWN-ТАБЛИЦ
    // -----------------------
    const removeMarkdownTables = (text) => {
      if (typeof text !== "string") return text;

      // Удаляем блоки с таблицами вида:
      // | ... |
      // |---...---|
      // | ... |
      return text.replace(
        /(^\s*\|.*\|\s*\n\s*\|[-:\s|]+\|\s*(\n\s*\|.*\|\s*)*)/gm,
        ""
      );
    };

    function cleanKatexErrors(node: any): any {
        if (!node) return null;

        // Если элемент — объект с props.children → рекурсивно обрабатываем
        if (node.props?.children) {
            const cleaned = React.Children.toArray(node.props.children)
                .map(child => cleanKatexErrors(child))
                .filter(Boolean); // удаляем null
            return React.cloneElement(node, node.props, cleaned);
        }

        // Если элемент — span с ошибкой KaTeX → удаляем
        if (
            node.props &&
            typeof node.props.className === "string" &&
            node.props.className.includes("katex-error")
        ) {
            return null;
        }

        return node;
    }

  // -----------------------
  // Парсинг формул
  // -----------------------
  const parseMathParts = (text) => {
    if (text === undefined || text === null) return [{ type: 'text', content: '' }];

    // если пришёл React-элемент/массив — не парсим, вернём содержимое как строку
    if (typeof text !== 'string') {
      if (Array.isArray(text)) text = text.join('');
      else if (React.isValidElement(text)) {
        // если это KaTeX-HTML элемент — не трогаем его выше (см. проверку в processChildren)
        text = String(text.props?.children ?? '');
      } else {
        text = String(text);
      }
     }

    text = text.replace(/\\ce(?=\{)/g, '');
    const parts = [];
    const regex = /(\$\$[\s\S]+?\$\$)|(\$[^$\n][^\$]*\$)/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(text)) !== null) {
      const idx = match.index;
      if (idx > lastIndex) parts.push({ type: 'text', content: text.slice(lastIndex, idx) });
      const token = match[0];
      if (token.startsWith('$$')) parts.push({ type: 'block', content: token.slice(2, -2) });
      else parts.push({ type: 'inline', content: token.slice(1, -1) });
      lastIndex = idx + token.length;
    }
    if (lastIndex < text.length) parts.push({ type: 'text', content: text.slice(lastIndex) });
    return parts;
  };

  const renderMathPartsForString = (str, keyPrefix = '') => {
    const parts = parseMathParts(str);
    return parts.map((p, i) => {
      const key = `${keyPrefix}-${i}`;
      if (p.type === 'text') return <React.Fragment key={key}>{p.content}</React.Fragment>;
      if (p.type === "inline") return <React.Fragment key={key}>{safeInline(p.content)}</React.Fragment>;

      if (p.type === "block")
        return (
          <div key={key} style={{ margin: "0.75rem 0" }}>
            {safeBlock(p.content)}
          </div>
      );
      return null;
    });
  };

  const processChildren = (children, keyPrefix = '') => {
      if (children === undefined || children === null) return null;

      // Если массив — обрабатываем каждый элемент
      if (Array.isArray(children)) {
        return children.map((child, idx) => (
          <React.Fragment key={`${keyPrefix}-${idx}`}>
            {processChildren(child, `${keyPrefix}-${idx}`)}
          </React.Fragment>
        ));
      }

      // Если текст
      if (typeof children === 'string') {
        return renderMathPartsForString(children, keyPrefix);
      }

      // Если не React-элемент — вернуть как есть
      if (!React.isValidElement(children)) {
        return children;
      }

      // React-элемент — безопасно читаем props
      const childProps = children.props || {};
      const className = childProps.className || '';
      const dataTestId = childProps['data-testid'] || '';

      // Пропускаем KaTeX
      if (
        typeof children.type === 'string' &&
        (className.includes('katex') || dataTestId === 'react-katex')
      ) {
        return children;
      }

      // Рекурсивно обрабатываем вложенных детей
      const processed = processChildren(childProps.children, `${keyPrefix}-el`);

      return React.cloneElement(children, { ...childProps }, processed);
  };

  const wrapWithMath = (Tag, keyPrefix) => ({ children, ...props }) => {
    return <Tag {...props}>{processChildren(children, keyPrefix)}</Tag>;
  };

  const H1 = wrapWithMath('h1', 'h1');
  const H2 = wrapWithMath('h2', 'h2');
  const H3 = wrapWithMath('h3', 'h3');
  const H4 = wrapWithMath('h4', 'h4');
  const Strong = wrapWithMath('strong', 'strong');
  const Em = wrapWithMath('em', 'em');
  const Span = wrapWithMath('span', 'span');
  const P = wrapWithMath('div', 'p');

  const Li = ({ children, ...props }) => (
    <li {...props}><div>{processChildren(children, 'li')}</div></li>
  );
  const Th = ({ children, ...props }) => (
    <th {...props}><div>{processChildren(children, 'th')}</div></th>
  );
  const Td = ({ children, ...props }) => (
    <td {...props}><div>{processChildren(children, 'td')}</div></td>
  );

  const CodeRenderer = ({ inline, className, children, ...props }) => {
    const code = String(children).replace(/\n$/, '');
    const match = /language-(\w+)/.exec(className || '');
    if (!inline && match) return <SyntaxHighlighter style={atomDark} language={match[1]} PreTag="div" {...props}>{code}</SyntaxHighlighter>;
    return <code className={className} {...props}>{children}</code>;
  };

  const TableRenderer = ({ children }) => (
    <div className="table-container">
      <table className="styled-table">{children}</table>
    </div>
  );

  const MarkdownWithLatex = ({ content }) => {
    if (!content) return null;
    content = removeMarkdownTables(content);
    const parts = [];
    const tableRegex = /```table\n([\s\S]*?)\n```/g;
    let lastIndex = 0;
    let match;
    while ((match = tableRegex.exec(content)) !== null) {
      if (match.index > lastIndex) parts.push({ type: 'text', content: content.slice(lastIndex, match.index) });
      parts.push({ type: 'table', content: match[1] });
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < content.length) parts.push({ type: 'text', content: content.slice(lastIndex) });
    const rendered = parts.map((part, idx) => {
        if (part.type === 'table') {
          return (
            <div key={`table-${idx}`} className="table-block">
              <ReactMarkdown
                children={part.content}
                components={{
                  table: TableRenderer,
                  th: Th,
                  td: Td,
                  p: (props) => <FinalLatexCleanup>{props.children}</FinalLatexCleanup>,
                }}
              />
            </div>
          );
        } else {
          return (
            <ReactMarkdown
              key={`text-${idx}`}
              children={part.content}
              components={{
                code: CodeRenderer,
                table: TableRenderer,
                th: Th,
                td: Td,
                p: (props) => <P><FinalLatexCleanup>{props.children}</FinalLatexCleanup></P>,
                li: Li,
                h1: H1,
                h2: H2,
                h3: H3,
                h4: H4,
                strong: Strong,
                em: Em,
                span: Span,
              }}
            />
          );
        }
      });

      // Если массив пуст → возвращаем null
      if (!rendered || rendered.length === 0) return null;

      return <>{rendered}</>;
  };

  const handleAnswerSelect = (lessonIndex, qIndex, option) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [lessonIndex]: { ...prev[lessonIndex], [qIndex]: option }
    }));
  };

  if (!course) return null;

  // -----------------------
  // ВАЛИДАЦИЯ ЛАТЕХ ПОСЛЕ МАРКДАУНА
  // -----------------------
  const containsUnparsedLatex = (text) => {
    if (!text) return false;

    return (
      /\$\$[^$]+?\$\$/g.test(text) ||     // $$...$$
      /\$[^$]+?\$/g.test(text) ||        // $...$
      /\\\([^)]*\\\)/g.test(text) ||     // \( ... \)
      /\\\[([^]*?)\\\]/g.test(text)      // \[ ... \]
    );
  };

  const FinalLatexCleanup = ({ children }) => {
      if (!children) return null;

      // Если это строка с LaTeX → разбиваем на блоки
      if (typeof children === 'string') {
        if (!containsUnparsedLatex(children)) return children;
        const mathParts = renderMathPartsForString(children);
        return Array.isArray(mathParts) ? <>{mathParts}</> : mathParts;
      }

      // Если это массив элементов → рекурсивно обрабатываем
      if (Array.isArray(children)) {
        const processed = children.map((child, i) => <React.Fragment key={i}>{FinalLatexCleanup({ children: child })}</React.Fragment>);
        return <>{processed}</>;
      }

      // Если это React-элемент → чистим KaTeX ошибки рекурсивно
      if (React.isValidElement(children)) {
        const cleaned = cleanKatexErrors(children);
        return cleaned;
      }

      // Всё остальное → возвращаем как есть
      return children;
    };

  return (
    <div className="course-viewer">
      <div className="course-header">
        <Book className="course-icon" size={32} />
        <div>
          <h1>{course.skeleton.title}</h1>
          <p className="course-description">{course.skeleton.description}</p>
          {course.topic && <p className="course-topic">Тема: {course.topic}</p>}
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${activeTab === 'content' ? 'active' : ''}`} onClick={() => setActiveTab('content')}>
          <FileText size={18} /> Содержание курса
        </button>
        <button className={`tab ${activeTab === 'quizzes' ? 'active' : ''}`} onClick={() => setActiveTab('quizzes')}>
          <CheckCircle size={18} /> Тесты
        </button>
      </div>

      {activeTab === 'content' && (
        <div className="chapters-list">
          {course.content.map((lesson, index) => (
            <div key={index} className="chapter-card">
              <div className="chapter-header" onClick={() => toggleChapter(index)} role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') toggleChapter(index); }}>
                <div className="chapter-title">
                  {expandedChapters[index] ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                  <span>{lesson.chapter_title.toLowerCase().startsWith('глава') ? lesson.chapter_title : `Глава ${index + 1}: ${lesson.chapter_title}`}</span>
                </div>
                <button className="ask-button" onClick={e => { e.stopPropagation(); onAskTutor(lesson); }}>Спросить репетитора</button>
              </div>
              {expandedChapters[index] && (
                <div className="chapter-content">
                  <div className="lesson-content">
                    <h4>Теоретический материал:</h4>
                    <div className="content-text"><MarkdownWithLatex content={lesson.content} /></div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'quizzes' && (
        <div className="chapters-list">
          {course.quizzes.map((quiz, lessonIndex) => (
            <div key={lessonIndex} className="quiz-card">
              <div className="chapter-title">
                <CheckCircle size={20} /> <span>Глава {lessonIndex + 1}: {quiz.chapter_title}</span>
              </div>
              {quiz.questions.map((q, qIndex) => {
                const selected = selectedAnswers?.[lessonIndex]?.[qIndex];
                const normalize = str => str?.toString().trim().toLowerCase();
                const isCorrect = normalize(selected) === normalize(q.correct_answer);

                return (
                  <div key={qIndex} className="question">
                    <h4>{renderMathPartsForString(q.question, `q-${lessonIndex}-${qIndex}`)}</h4>
                    <ul className="options">
                      {q.options.map((opt, i) => {
                        let optionClass = "option";
                        if (selected) {
                          if (opt === q.correct_answer) optionClass += " correct";
                          else if (opt === selected && !isCorrect) optionClass += " wrong";
                        }
                        return (
                          <li key={i} className={optionClass} onClick={() => { if (!selected) handleAnswerSelect(lessonIndex, qIndex, opt); }}>
                            {renderMathPartsForString(opt, `opt-${lessonIndex}-${qIndex}-${i}`)}
                          </li>
                        );
                      })}
                    </ul>
                    {selected && (
                      <div className={`explanation ${isCorrect ? 'correct' : 'wrong'}`}>
                        <strong>Правильный ответ:</strong> {renderMathPartsForString(q.correct_answer, `ans-${lessonIndex}-${qIndex}`)}
                        {q.explanation && <div>{renderMathPartsForString(q.explanation, `exp-${lessonIndex}-${qIndex}`)}</div>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CourseViewer;
