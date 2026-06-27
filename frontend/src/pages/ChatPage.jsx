import { useState, useRef, useEffect } from 'react';
import { chatAPI } from '../services/api';
import styles from './ChatPage.module.css';

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [suggestions, setSuggestions] = useState([
    'What should I focus on today?',
    'Am I at risk of missing any deadlines?',
    'Help me plan my week',
  ]);
  const messagesEnd = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    if (!text.trim() || sending) return;

    const userMsg = { role: 'user', content: text.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setSending(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const { data } = await chatAPI.send(text.trim(), history);
      setMessages([...newMessages, { role: 'assistant', content: data.reply }]);
      if (data.suggestions?.length) setSuggestions(data.suggestions);
    } catch {
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: "I'm having trouble connecting right now. Make sure the backend is running and try again.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>AI Chat</h1>
        <p className={styles.subtitle}>Talk to your Chronos AI productivity companion</p>
      </div>

      <div className={styles.chatContainer}>
        <div className={styles.messages}>
          {messages.length === 0 ? (
            <div className={styles.welcome}>
              <div className={styles.welcomeIcon}>⏳</div>
              <div className={styles.welcomeTitle}>How can I help you today?</div>
              <p>Ask about your tasks, deadlines, productivity, or get planning advice.</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                {msg.content}
              </div>
            ))
          )}
          {sending && <div className={styles.typing}>Chronos is thinking...</div>}
          <div ref={messagesEnd} />
        </div>

        {suggestions.length > 0 && messages.length === 0 && (
          <div className={styles.suggestions}>
            {suggestions.map((s) => (
              <button key={s} className={styles.suggestion} onClick={() => sendMessage(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        <div className={styles.inputArea}>
          <input
            className={styles.input}
            placeholder="Ask Chronos anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
            disabled={sending}
          />
          <button className={styles.sendBtn} onClick={() => sendMessage(input)} disabled={sending || !input.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
