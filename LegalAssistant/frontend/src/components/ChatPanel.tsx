import { FormEvent, useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

import { Citation, ChatMessage, sendQuestion } from "../api";

interface AssistantTurn {
  answer: string;
  citations: Citation[];
}

function getRelevanceLabel(score: number): string {
  if (score >= 0.65) {
    return "高相关";
  }

  if (score >= 0.35) {
    return "较相关";
  }

  return "可参考";
}

export function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [responses, setResponses] = useState<AssistantTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const chatShellRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when messages update
  useEffect(() => {
    if (chatShellRef.current) {
      chatShellRef.current.scrollTop = chatShellRef.current.scrollHeight;
    }
  }, [responses, history, loading]);

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    if (event) {
      event.preventDefault();
    }
    const trimmed = question.trim();
    if (!trimmed || loading) {
      return;
    }

    const nextHistory = [...history, { role: "user" as const, content: trimmed }];
    setHistory(nextHistory);
    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const response = await sendQuestion(trimmed, history);
      setHistory((current) => [...current, { role: "assistant", content: response.answer }]);
      setResponses((current) => [...current, { answer: response.answer, citations: response.citations }]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <div className="logo-container">
          <div className="icon-badge">
            <svg className="logo-icon" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>
              <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>
              <path d="M7 21h10"/>
              <path d="M12 3v18"/>
              <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>
            </svg>
          </div>
          <div className="title-wrapper">
            <p className="eyebrow">Labor Law Assistant</p>
            <h1>劳动法规咨询助手</h1>
          </div>
        </div>
      </div>

      <div className="chat-shell" ref={chatShellRef}>
        {responses.length === 0 && !loading && history.length === 0 ? (
          <div className="empty-state">
            <p>遇到工作上的问题？试试这样问我：</p>
            <ul>
              <li>公司不发年终奖合法吗？</li>
              <li>试用期被辞退有哪些赔偿？</li>
              <li>每天义务加班怎么维权？</li>
            </ul>
          </div>
        ) : (
          history.map((message, index) => {
            if (message.role === 'user') {
              return (
                <div className="bubble bubble-user" key={`user-${index}`}>
                  {message.content}
                </div>
              );
            } else {
              // message.role === 'assistant', find corresponding response for citations
              const responseIdx = Math.floor((index - 1) / 2);
              const response = responses[responseIdx];
              return (
                <div className="assistant-group" key={`assistant-${index}`}>
                  <div className="bubble bubble-assistant">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                  {response?.citations && response.citations.length > 0 && (
                    <div className="citations">
                      <h2>参考依据</h2>
                      {response.citations.map((citation, cIdx) => (
                        <div className="citation-card" key={`cit-${index}-${cIdx}`}>
                          <div className="citation-meta">
                            <strong>{citation.title}</strong>
                            <span>{getRelevanceLabel(citation.score)}</span>
                          </div>
                          <p>{citation.content}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            }
          })
        )}
        
        {loading && (
          <div className="loading-dots">
            <span></span><span></span><span></span>
          </div>
        )}

        {error ? <div className="error-banner">{error}</div> : null}
      </div>

      <div className="composer-container">
        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            placeholder="输入咨询内容..."
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button type="submit" disabled={loading || !question.trim()}>
            <svg viewBox="0 0 24 24">
              <path d="M12 4L12 20M12 4L5 11M12 4L19 11" />
            </svg>
          </button>
        </form>
      </div>
    </section>
  );
}
