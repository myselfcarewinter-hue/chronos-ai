import { useEffect, useState } from 'react';
import { tasksAPI } from '../services/api';
import Badge from '../components/Badge';
import styles from './TasksPage.module.css';

const EXAMPLES = [
  'I have an ML assignment due Friday night.',
  'Prepare quarterly report for the client meeting next Tuesday.',
  'Study for calculus exam — chapters 5 through 8, exam is in 3 days.',
];

function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function TasksPage() {
  const [tasks, setTasks] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [pipelineMsg, setPipelineMsg] = useState('');
  const [filter, setFilter] = useState('all');

  const loadTasks = async (status) => {
    setLoading(true);
    try {
      const params = status && status !== 'all' ? status : undefined;
      const { data } = await tasksAPI.list(params);
      setTasks(data.tasks || []);
    } catch {
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks(filter);
  }, [filter]);

  const handleCreate = async () => {
    if (!input.trim()) return;
    setCreating(true);
    setPipelineMsg('');
    try {
      const { data } = await tasksAPI.create(input.trim());
      setPipelineMsg(data.message);
      setInput('');
      await loadTasks(filter);
    } catch (err) {
      setPipelineMsg(err.response?.data?.error || 'Failed to create task. Is the backend running?');
    } finally {
      setCreating(false);
    }
  };

  const handleComplete = async (id) => {
    try {
      const { data } = await tasksAPI.complete(id);
      setPipelineMsg(data.message);
      await loadTasks(filter);
    } catch {
      setPipelineMsg('Failed to complete task.');
    }
  };

  const filters = [
    { key: 'all', label: 'All' },
    { key: 'in_progress', label: 'In Progress' },
    { key: 'pending', label: 'Pending' },
    { key: 'completed', label: 'Completed' },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Tasks</h1>
          <p className={styles.subtitle}>Describe what you need to do — AI handles the rest</p>
        </div>
        <div className={styles.filterBar}>
          {filters.map((f) => (
            <button
              key={f.key}
              className={`${styles.filterBtn} ${filter === f.key ? styles.filterBtnActive : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.createSection}>
        <h2 className={styles.createTitle}>Create Task with AI</h2>
        <div className={styles.inputGroup}>
          <textarea
            className={styles.textarea}
            placeholder='e.g. "I have an ML assignment due Friday night."'
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleCreate();
              }
            }}
            rows={2}
          />
          <button className={styles.createBtn} onClick={handleCreate} disabled={creating || !input.trim()}>
            {creating ? 'Planning...' : 'Create'}
          </button>
        </div>
        <div className={styles.example}>
          Try:
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => setInput(ex)}>{ex.slice(0, 40)}...</button>
          ))}
        </div>
      </div>

      {pipelineMsg && (
        <div className={styles.pipelineResult}>
          <div className={styles.pipelineTitle}>AI Pipeline Result</div>
          <div className={styles.pipelineMessage}>{pipelineMsg}</div>
        </div>
      )}

      {loading ? (
        <div className={styles.empty}>Loading tasks...</div>
      ) : tasks.length === 0 ? (
        <div className={styles.empty}>
          No tasks yet. Describe something you need to do above and let Chronos AI plan it for you.
        </div>
      ) : (
        <div className={styles.taskGrid}>
          {tasks.map((task) => (
            <div key={task.id} className={styles.taskCard}>
              <div className={styles.taskHeader}>
                <div>
                  <div className={styles.taskTitle}>{task.title}</div>
                  {task.description && (
                    <div className={styles.taskDescription}>{task.description}</div>
                  )}
                </div>
                <div className={styles.badges}>
                  <Badge label={task.priority.priority_level} />
                  <Badge label={task.risk.risk_level} />
                  <Badge label={task.status} />
                </div>
              </div>

              <div className={styles.meta}>
                <span>Deadline: {formatDate(task.deadline)}</span>
                <span>{task.estimated_hours}h estimated</span>
                <span>{task.category}</span>
                <span>Risk: {Math.round(task.risk.risk_percentage)}%</span>
              </div>

              {task.execution_plan && (
                <div className={styles.plan}>{task.execution_plan}</div>
              )}

              {task.subtasks?.length > 0 && (
                <div className={styles.subtasks}>
                  {task.subtasks.map((st) => (
                    <div
                      key={st.id}
                      className={`${styles.subtask} ${st.status === 'completed' ? styles.subtaskDone : ''}`}
                    >
                      <span className={styles.subtaskDot} />
                      {st.title} ({st.estimated_hours}h)
                    </div>
                  ))}
                </div>
              )}

              {task.status !== 'completed' && (
                <div className={styles.actions}>
                  <button className={styles.completeBtn} onClick={() => handleComplete(task.id)}>
                    Complete (+{task.xp_reward} XP)
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
