import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { dashboardAPI } from '../services/api';
import StatCard from '../components/StatCard';
import Badge from '../components/Badge';
import styles from './DashboardPage.module.css';

function formatDeadline(deadline) {
  if (!deadline) return 'No deadline';
  const d = new Date(deadline);
  const now = new Date();
  const diff = d - now;
  if (diff < 0) return 'Overdue';
  const hours = Math.floor(diff / 3600000);
  if (hours < 24) return `${hours}h left`;
  const days = Math.floor(hours / 24);
  return `${days}d left`;
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    dashboardAPI
      .get()
      .then(({ data: d }) => setData(d))
      .catch(() => setError('Could not load dashboard. Backend may be offline.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className={styles.loading}>Loading dashboard...</div>;

  if (error || !data) {
    return (
      <div className={styles.page}>
        <div className={styles.empty}>
          <p>{error || 'No data available'}</p>
          <p style={{ marginTop: 8, fontSize: 13 }}>
            Start the backend with <code>uvicorn app.main:app --reload</code> and create tasks.
          </p>
          <Link to="/tasks" style={{ marginTop: 16, display: 'inline-block' }}>Go to Tasks →</Link>
        </div>
      </div>
    );
  }

  const maxScore = Math.max(...(data.productivity_graph?.map((p) => p.score) || [1]), 1);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Dashboard</h1>
          <p className={styles.subtitle}>Your productivity command center</p>
        </div>
      </div>

      <div className={styles.statsGrid}>
        <StatCard title="Life Score" value={Math.round(data.life_score)} subtext="Overall productivity" icon="💫" />
        <StatCard title="XP" value={data.xp.toLocaleString()} subtext={`Level ${data.level}`} icon="⚡" />
        <StatCard title="Streak" value={`${data.streak} days`} subtext="Keep it going!" icon="🔥" />
        <StatCard
          title="At Risk"
          value={data.high_risk_tasks?.length || 0}
          subtext="Tasks needing attention"
          icon="⚠️"
        />
      </div>

      <div className={styles.grid2}>
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Today's Tasks</h2>
          <div className={styles.taskList}>
            {data.todays_tasks?.length ? (
              data.todays_tasks.map((task) => (
                <div key={task.id} className={styles.taskItem}>
                  <div className={styles.taskInfo}>
                    <span className={styles.taskTitle}>{task.title}</span>
                    <span className={styles.taskMeta}>
                      <span>{formatDeadline(task.deadline)}</span>
                      <span>{task.category}</span>
                    </span>
                  </div>
                  <div className={styles.taskBadges}>
                    <Badge label={task.priority.priority_level} />
                    <Badge label={`${Math.round(task.risk.risk_percentage)}%`} variant={task.risk.risk_level} />
                  </div>
                </div>
              ))
            ) : (
              <div className={styles.empty}>No tasks due today</div>
            )}
          </div>
        </div>

        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Upcoming Deadlines</h2>
          <div className={styles.taskList}>
            {data.upcoming_deadlines?.length ? (
              data.upcoming_deadlines.map((task) => (
                <div key={task.id} className={styles.taskItem}>
                  <div className={styles.taskInfo}>
                    <span className={styles.taskTitle}>{task.title}</span>
                    <span className={styles.taskMeta}>{formatDeadline(task.deadline)}</span>
                  </div>
                  <Badge label={task.risk.risk_level} />
                </div>
              ))
            ) : (
              <div className={styles.empty}>No upcoming deadlines</div>
            )}
          </div>
        </div>
      </div>

      {data.productivity_graph?.length > 0 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Productivity Trend</h2>
          <div className={styles.chart}>
            <div className={styles.chartBars}>
              {data.productivity_graph.slice(-14).map((point, i) => (
                <div
                  key={i}
                  className={styles.bar}
                  style={{ height: `${(point.score / maxScore) * 100}%` }}
                  title={`${point.date}: ${point.score}`}
                >
                  <span className={styles.barLabel}>
                    {new Date(point.date).getDate()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
