import { useEffect, useState } from "react";
import {
  ArrowRight, BrainCircuit, Check, ChevronLeft, CircleHelp, Clock3,
  FileText, Flame, GraduationCap, History, Home, LoaderCircle, Menu,
  Moon, RotateCcw, Sparkles, Target, Trophy, Upload, X, Zap,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

type Question = {
  question: string;
  options: string[];
  answer: number;
  explanation?: string;
};
type Quiz = { title?: string; topic?: string; source?: string; questions: Question[] };
type HistoryItem = {
  title?: string; topic?: string; score?: number; total?: number;
  percentage?: number; percent?: number; created_at?: string; date?: string;
};

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(10);
  const [difficulty, setDifficulty] = useState("Medium");
  const [language, setLanguage] = useState("English");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [quizStartedAt, setQuizStartedAt] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ score: number; total: number; percentage: number } | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => { void loadHistory(); }, []);

  useEffect(() => {
    if (!quiz || result || !quizStartedAt || timeLeft <= 0) return;
    const timer = window.setTimeout(() => setTimeLeft((previous) => Math.max(0, previous - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [quiz, result, quizStartedAt, timeLeft]);

  useEffect(() => {
    if (quiz && !result && quizStartedAt && timeLeft === 0) void submitQuiz(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft]);

  async function loadHistory() {
    try {
      const response = await fetch(`${API_BASE}/api/history`);
      if (!response.ok) return;
      const data = await response.json();
      setHistory(Array.isArray(data) ? data : Array.isArray(data.history) ? data.history : []);
    } catch { /* The app remains usable if the backend is unavailable. */ }
  }

  async function generateQuiz() {
    if (!topic.trim()) { setError("Please enter a topic first."); return; }
    setLoading(true); setError(""); setResult(null); setQuiz(null); setAnswers({});
    try {
      const response = await fetch(`${API_BASE}/api/generate-quiz`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim(), count, difficulty, language }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to generate the quiz.");
      if (!Array.isArray(data.questions) || !data.questions.length) throw new Error("The AI did not return any questions. Try another topic.");
      const questions: Question[] = data.questions.map((q: any) => ({
        question: String(q.question ?? ""),
        options: Array.isArray(q.options) ? q.options.map(String) : [],
        answer: Number(q.answer ?? q.answer_index ?? 0),
        explanation: String(q.explanation ?? ""),
      })).filter((q: Question) => q.question && q.options.length >= 2);
      if (!questions.length) throw new Error("The generated questions were not in a usable format.");
      setQuiz({ title: data.title || `${topic} Quiz`, topic: data.topic || topic.trim(), source: data.source || "AI", questions });
      setTimeLeft(questions.length * 60); setQuizStartedAt(Date.now()); setCurrentQuestion(0); setActivePage("Quiz");
    } catch (err) {
      setError(err instanceof Error ? `${err.message} Check that your FastAPI backend is running.` : "Could not connect to the backend.");
    } finally { setLoading(false); }
  }

  function chooseAnswer(optionIndex: number) {
    setAnswers((previous) => ({ ...previous, [currentQuestion]: optionIndex }));
  }

  async function submitQuiz(autoSubmit = false) {
    if (!quiz || result) return;
    const score = quiz.questions.reduce((sum, question, index) => sum + (answers[index] === question.answer ? 1 : 0), 0);
    const total = quiz.questions.length;
    const percentage = Math.round((score / total) * 100);
    setResult({ score, total, percentage }); setQuizStartedAt(0); setActivePage("Results");
    try {
      const response = await fetch(`${API_BASE}/api/submit-quiz`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: quiz.title || `${quiz.topic || topic} Quiz`,
          topic: quiz.topic || topic,
          questions: quiz.questions.map((question) => ({
            question: question.question, options: question.options,
            answer_index: question.answer, explanation: question.explanation || "",
          })),
          answers: quiz.questions.map((_, index) => answers[index] ?? -1),
          elapsed: Math.max(0, Math.round((Date.now() - (quizStartedAt || Date.now())) / 1000)),
          auto_submitted: autoSubmit,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(data.detail || "Your result is shown, but it could not be saved to history.");
      }
    } catch {
      setError("Your result is shown, but history could not be saved. Check that the backend is running.");
    } finally { await loadHistory(); }
  }

  function resetQuiz() {
    setQuiz(null); setResult(null); setAnswers({}); setCurrentQuestion(0);
    setTimeLeft(0); setQuizStartedAt(0); setError(""); setActivePage("Dashboard");
  }
  function formatTime(seconds: number) {
    return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  }
  async function uploadMaterial(file?: File) {
    if (!file) return;
    const formData = new FormData(); formData.append("file", file);
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/upload-material`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "File upload failed.");
      setTopic((previous) => previous || file.name.replace(/\.[^.]+$/, ""));
      setError(`Uploaded ${data.filename || file.name}. ${data.words ?? ""} words extracted. Enter a topic and generate your quiz.`);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to upload the file."); }
    finally { setLoading(false); }
  }

  const navigation = [{ label: "Dashboard", icon: Home }, { label: "Generate Quiz", icon: Sparkles }, { label: "History", icon: History }];
  const completedCount = Object.keys(answers).length;
  const activeQuestion = quiz?.questions[currentQuestion];
  const answeredCorrectly = result && quiz ? quiz.questions.filter((q, i) => answers[i] === q.answer).length : 0;
  const getTopic = (item: HistoryItem) => item.topic || item.title || "Practice quiz";
  const getPercent = (item: HistoryItem) => {
    const value = item.percentage ?? item.percent;
    return value !== undefined ? `${value}%` : "Completed";
  };
  const getDate = (item: HistoryItem, includeTime = false) => {
    const value = item.created_at || item.date;
    if (!value) return "Saved attempt";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : includeTime ? date.toLocaleString() : date.toLocaleDateString();
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon"><BrainCircuit size={25} /></div>
          <div><h2>Quizora<span>AI</span></h2><p>INTELLIGENCE, REIMAGINED</p></div>
          <button className="icon-button sidebar-close" onClick={() => setMobileMenu(false)} aria-label="Close navigation"><X size={19} /></button>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="sidebar-nav">
          {navigation.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${activePage === label ? "nav-active" : ""}`} onClick={() => { setActivePage(label); setMobileMenu(false); setError(""); if (label === "History") void loadHistory(); }}>
            <Icon size={19} /><span>{label}</span>{label === "Generate Quiz" && <span className="nav-new">AI</span>}
          </button>)}
        </nav>
        <div className="sidebar-divider" /><div className="workspace-label">YOUR PROGRESS</div>
        <div className="sidebar-stat"><div className="stat-icon orange-icon"><Flame size={18} /></div><div><strong>{history.length}</strong><span>Quizzes attempted</span></div></div>
        <div className="sidebar-stat"><div className="stat-icon purple-icon"><Trophy size={18} /></div><div><strong>Keep going!</strong><span>Every quiz counts</span></div></div>
        <div className="sidebar-bottom">
          <div className="upgrade-card"><div className="upgrade-spark"><Sparkles size={20} /></div><h3>Your next big win.</h3><p>Learn smarter, one question at a time.</p><button onClick={() => setActivePage("Generate Quiz")}>Start learning <ArrowRight size={15} /></button></div>
          <div className="profile-row"><div className="avatar">K</div><div className="profile-info"><strong>Learner</strong><span>Free workspace</span></div><span className="online-dot" /></div>
        </div>
      </aside>
      {mobileMenu && <button className="mobile-backdrop" onClick={() => setMobileMenu(false)} aria-label="Close menu" />}
      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left"><button className="icon-button mobile-menu-button" onClick={() => setMobileMenu(true)} aria-label="Open navigation"><Menu size={21} /></button><div className="breadcrumb">Workspace <span>/</span> <strong>{activePage}</strong></div></div>
          <div className="topbar-right"><div className="system-status"><span /> AI systems online</div><button className="icon-button theme-button" aria-label="Appearance"><Moon size={19} /></button><div className="top-avatar">K</div></div>
        </header>
        <div className="page-content">
          {error && <motion.div className={`notice ${error.startsWith("Uploaded") ? "notice-success" : ""}`} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}><CircleHelp size={18} /><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss message"><X size={17} /></button></motion.div>}
          <AnimatePresence mode="wait">
            {activePage === "Quiz" && quiz && activeQuestion ? (
              <motion.section key="quiz" className="quiz-page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                <button className="back-link" onClick={() => setActivePage("Dashboard")}><ChevronLeft size={17} /> Dashboard</button>
                <div className="quiz-topline"><div><span className="eyebrow">YOUR KNOWLEDGE CHECK</span><h1>{quiz.title}</h1><p>{quiz.topic} · {quiz.source}</p></div><div className={`timer-pill ${timeLeft < 60 ? "timer-warning" : ""}`}><Clock3 size={18} /><span>{formatTime(timeLeft)}</span></div></div>
                <div className="quiz-progress-row"><span>Question {currentQuestion + 1} <span className="muted">of {quiz.questions.length}</span></span><span>{Math.round(((currentQuestion + 1) / quiz.questions.length) * 100)}% complete</span></div>
                <div className="progress-track"><motion.div className="progress-fill" animate={{ width: `${((currentQuestion + 1) / quiz.questions.length) * 100}%` }} /></div>
                <div className="quiz-layout">
                  <div className="question-card"><div className="question-meta"><span>QUESTION {String(currentQuestion + 1).padStart(2, "0")}</span><span className="difficulty-badge">{difficulty}</span></div><h2>{activeQuestion.question}</h2>
                    <div className="answer-list">{activeQuestion.options.map((option, index) => <button key={index} className={`answer-option ${answers[currentQuestion] === index ? "answer-selected" : ""}`} onClick={() => chooseAnswer(index)}><span className="option-letter">{String.fromCharCode(65 + index)}</span><span>{option}</span>{answers[currentQuestion] === index && <Check className="answer-check" size={19} />}</button>)}</div>
                    <div className="question-footer"><button className="secondary-button" disabled={currentQuestion === 0} onClick={() => setCurrentQuestion((n) => n - 1)}><ChevronLeft size={17} /> Previous</button>{currentQuestion < quiz.questions.length - 1 ? <button className="primary-button" onClick={() => setCurrentQuestion((n) => n + 1)}>Next question <ArrowRight size={17} /></button> : <button className="primary-button" onClick={() => void submitQuiz()}><Check size={17} /> Finish quiz</button>}</div>
                  </div>
                  <aside className="question-sidebar">
                    <div className="mini-card"><div className="mini-card-heading">QUESTION MAP</div><div className="question-map">{quiz.questions.map((_, index) => <button key={index} className={`map-dot ${index === currentQuestion ? "map-current" : ""} ${answers[index] !== undefined ? "map-answered" : ""}`} onClick={() => setCurrentQuestion(index)}>{index + 1}</button>)}</div><div className="map-legend"><span><i className="legend-current" /> Current</span><span><i className="legend-answered" /> Answered</span></div></div>
                    <div className="mini-card completion-card"><div className="completion-icon"><Target size={21} /></div><h3>Your progress</h3><strong>{completedCount}<span> / {quiz.questions.length}</span></strong><p>Questions answered</p><div className="progress-track small-track"><div className="progress-fill" style={{ width: `${completedCount / quiz.questions.length * 100}%` }} /></div></div>
                  </aside>
                </div>
              </motion.section>
            ) : activePage === "Results" && result && quiz ? (
              <motion.section key="results" className="results-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <div className="results-hero"><div className="result-trophy"><Trophy size={34} /></div><span className="eyebrow">QUIZ COMPLETED</span><h1>{result.percentage >= 80 ? "Outstanding work!" : result.percentage >= 50 ? "You're making progress!" : "Every attempt makes you better."}</h1><p>You completed the {quiz.topic} quiz. Here's how you did.</p><div className="score-ring" style={{ "--score": `${result.percentage}%` } as React.CSSProperties}><div><strong>{result.percentage}%</strong><span>YOUR SCORE</span></div></div></div>
                <div className="result-stats"><div className="result-stat"><Check size={20} /><span>Correct answers</span><strong>{answeredCorrectly}</strong></div><div className="result-stat"><X size={20} /><span>Incorrect answers</span><strong>{result.total - answeredCorrectly}</strong></div><div className="result-stat"><CircleHelp size={20} /><span>Total questions</span><strong>{result.total}</strong></div></div>
                <div className="review-heading"><div><span className="eyebrow">LEARN FROM EVERY ANSWER</span><h2>Answer review</h2></div><button className="secondary-button" onClick={resetQuiz}><RotateCcw size={16} /> New quiz</button></div>
                <div className="review-list">{quiz.questions.map((question, index) => { const correct = answers[index] === question.answer; return <div className="review-card" key={index}><div className={`review-status ${correct ? "review-correct" : "review-incorrect"}`}>{correct ? <Check size={17} /> : <X size={17} />}</div><div className="review-body"><span className="eyebrow">QUESTION {index + 1}</span><h3>{question.question}</h3><p>Your answer: <strong>{answers[index] === undefined ? "Not answered" : question.options[answers[index]]}</strong></p><p>Correct answer: <strong className="correct-text">{question.options[question.answer]}</strong></p>{question.explanation && <div className="explanation"><Sparkles size={16} /><span>{question.explanation}</span></div>}</div></div>; })}</div>
              </motion.section>
            ) : activePage === "History" ? (
              <motion.section key="history" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
                <div className="page-heading"><div><span className="eyebrow">YOUR LEARNING JOURNEY</span><h1>Quiz history<span className="heading-period">.</span></h1><p>Every attempt is a step forward. Review your progress.</p></div><button className="primary-button" onClick={() => setActivePage("Generate Quiz")}><Sparkles size={17} /> New quiz</button></div>
                <div className="history-card"><div className="history-head"><h3><History size={19} /> Recent attempts</h3><span>{history.length} records</span></div>{history.length ? history.map((item, index) => <div className="history-row" key={`${getTopic(item)}-${item.created_at || item.date || index}`}><div className="history-icon"><GraduationCap size={20} /></div><div className="history-topic"><strong>{getTopic(item)}</strong><span>{getDate(item, true)}</span></div><div className="history-score">{item.score ?? "—"}<span> / {item.total ?? "—"}</span></div><div className="history-percent">{getPercent(item)}</div></div>) : <div className="empty-state"><History size={31} /><h3>Your story starts here</h3><p>Generate your first quiz to see your attempts here.</p><button className="primary-button" onClick={() => setActivePage("Generate Quiz")}>Create a quiz <ArrowRight size={16} /></button></div>}</div>
              </motion.section>
            ) : (
              <motion.section key="dashboard" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <div className="welcome-row"><div><div className="welcome-label"><span className="welcome-dot" /> YOUR PERSONAL AI LEARNING SPACE</div><h1>Think smarter.<br /><span>Learn faster.</span></h1><p>Your AI-powered study partner is ready. What will you master today?</p></div><div className="hero-graphic"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="hero-core"><BrainCircuit size={48} /></div><div className="float-chip chip-one"><Sparkles size={16} /></div><div className="float-chip chip-two"><Zap size={17} /></div><div className="float-chip chip-three"><Target size={16} /></div></div></div>
                <div className="stats-grid">
                  <div className="stat-card"><div className="stat-top"><span>QUIZZES TAKEN</span><div className="stat-icon orange-icon"><FileText size={18} /></div></div><div className="stat-number">{history.length}<span className="stat-unit"> total</span></div><div className="stat-foot">Your learning journey so far</div></div>
                  <div className="stat-card"><div className="stat-top"><span>AI-POWERED</span><div className="stat-icon purple-icon"><BrainCircuit size={18} /></div></div><div className="stat-number">24<span className="stat-unit">/7</span></div><div className="stat-foot"><span className="positive-dot" /> Ready whenever you are</div></div>
                  <div className="stat-card"><div className="stat-top"><span>LEARNING MODE</span><div className="stat-icon green-icon"><Target size={18} /></div></div><div className="stat-number">Active</div><div className="stat-foot">Small steps. Big progress.</div></div>
                </div>
                <div className="section-heading"><div><span className="eyebrow">LET'S GET STARTED</span><h2>Create your next quiz<span className="heading-period">.</span></h2><p>Personalized questions, generated just for you.</p></div><div className="ai-badge"><Sparkles size={15} /> Powered by AI</div></div>
                <div className="generator-layout">
                  <div className="generator-card">
                    <div className="card-heading"><div className="card-heading-icon"><Sparkles size={20} /></div><div><h3>Quiz studio</h3><p>Make learning feel effortless.</p></div><span className="live-badge"><span /> LIVE</span></div>
                    <label className="field-label" htmlFor="topic">WHAT DO YOU WANT TO LEARN?</label>
                    <div className="topic-input-wrap"><BrainCircuit size={19} /><input id="topic" value={topic} onChange={(event) => setTopic(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void generateQuiz(); }} placeholder="e.g. Python, cloud computing, biology..." /><span className="input-ai"><Sparkles size={14} /> AI</span></div>
                    <div className="field-label upload-label">OR USE YOUR STUDY MATERIAL</div>
                    <label className={`upload-box ${dragging ? "upload-dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); void uploadMaterial(event.dataTransfer.files[0]); }}>
                      <input type="file" accept=".pdf,.docx,.txt" onChange={(event) => void uploadMaterial(event.target.files?.[0])} /><div className="upload-icon"><Upload size={21} /></div><div className="upload-copy"><strong>Drop your file here, or <span>browse</span></strong><p>PDF, DOCX or TXT · Max 10 MB</p></div><FileText className="upload-file-icon" size={22} />
                    </label>
                    <div className="form-divider" /><div className="field-row">
                      <div className="field-group"><label className="field-label" htmlFor="question-count">QUESTIONS</label><select id="question-count" value={count} onChange={(event) => setCount(Number(event.target.value))}><option value={5}>5 questions</option><option value={10}>10 questions</option><option value={15}>15 questions</option><option value={20}>20 questions</option></select></div>
                      <div className="field-group"><label className="field-label" htmlFor="difficulty">DIFFICULTY</label><select id="difficulty" value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option>Easy</option><option>Medium</option><option>Hard</option></select></div>
                    </div>
                    <div className="field-group language-group"><label className="field-label" htmlFor="language">QUIZ LANGUAGE</label><select id="language" value={language} onChange={(event) => setLanguage(event.target.value)}><option>English</option><option>Hindi</option><option>Marathi</option><option>Spanish</option><option>French</option></select></div>
                    <button className="generate-button" onClick={() => void generateQuiz()} disabled={loading}>{loading ? <><LoaderCircle className="spin" size={20} /> Creating your quiz...</> : <><Sparkles size={19} /> Generate my quiz <ArrowRight size={18} /></>}</button>
                    <div className="secure-note"><span className="secure-dot" /> Your learning experience, powered by AI.</div>
                  </div>
                  <div className="generator-aside">
                    <div className="feature-card feature-highlight"><div className="feature-glow" /><div className="feature-icon"><BrainCircuit size={23} /></div><span className="eyebrow">YOUR AI STUDY PARTNER</span><h3>Not just a quiz.<br /><span>A smarter you.</span></h3><p>Turn any topic into a focused learning session with AI-generated questions and instant feedback.</p><div className="feature-points"><span><Check size={15} /> Personalized questions</span><span><Check size={15} /> Instant results</span><span><Check size={15} /> Detailed explanations</span></div><div className="feature-bottom"><span>INTELLIGENCE, REIMAGINED</span><Sparkles size={18} /></div></div>
                    <div className="quick-tip"><div className="tip-icon"><Zap size={19} /></div><div><strong>Pro tip</strong><p>Be specific! Try “Python list comprehensions” instead of just “Python” for a more focused quiz.</p></div></div>
                  </div>
                </div>
                <div className="recent-section"><div className="recent-heading"><div><span className="eyebrow">PICK UP WHERE YOU LEFT OFF</span><h2>Recent activity<span className="heading-period">.</span></h2></div><button className="text-button" onClick={() => { setActivePage("History"); void loadHistory(); }}>View history <ArrowRight size={16} /></button></div><div className="recent-card">{history.length ? history.slice(0, 4).map((item, index) => <div className="history-row" key={`${getTopic(item)}-${item.created_at || item.date || index}`}><div className="history-icon"><GraduationCap size={20} /></div><div className="history-topic"><strong>{getTopic(item)}</strong><span>{getDate(item)}</span></div><div className="history-score">{item.score ?? "—"}<span> / {item.total ?? "—"}</span></div><div className="history-percent">{getPercent(item)}</div></div>) : <div className="recent-empty"><div className="recent-empty-icon"><History size={21} /></div><div><strong>No quizzes yet</strong><p>Your recent attempts will show up here.</p></div><button onClick={() => setActivePage("Generate Quiz")}>Get started <ArrowRight size={15} /></button></div>}</div></div>
                <footer className="page-footer"><span>QUIZORA AI <span className="footer-dot">•</span> BUILT FOR CURIOUS MINDS</span><span><span className="positive-dot" /> AI services operational</span></footer>
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
export default App;
