import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import styles from './LoginPage.module.css';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await authAPI.login();
      window.location.href = data.authorization_url;
    } catch {
      setError('Could not connect to server. Use demo mode or check backend is running.');
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await authAPI.demo();
      login(data.access_token, data.user);
      navigate('/');
    } catch {
      setError('Could not start demo mode. Make sure the backend is running.');
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.logo}>⏳</div>
        <h1 className={styles.title}>Chronos AI</h1>
        <p className={styles.subtitle}>
          Your autonomous AI productivity companion. Understands tasks, predicts risks,
          plans work, and keeps you motivated.
        </p>

        <button className={styles.loginBtn} onClick={handleGoogleLogin} disabled={loading}>
          {loading ? 'Connecting...' : 'Continue with Google'}
        </button>

        <button className={styles.demoBtn} onClick={handleDemoLogin}>
          Try Demo Mode
        </button>

        {error && <p className={styles.error}>{error}</p>}

        <div className={styles.features}>
          <div className={styles.feature}>
            <span className={styles.featureIcon}>🎯</span>
            <div className={styles.featureText}>
              <strong>Smart Task Intake</strong>
              Describe tasks in natural language — AI extracts deadlines, priority, and plans
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureIcon}>⚠️</span>
            <div className={styles.featureText}>
              <strong>Risk Prediction</strong>
              Predicts failure probability and triggers rescue plans automatically
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureIcon}>🏆</span>
            <div className={styles.featureText}>
              <strong>Gamification</strong>
              Earn XP, maintain streaks, and track your Life Score
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
