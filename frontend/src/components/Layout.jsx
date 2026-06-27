import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './Layout.module.css';

const NAV_ITEMS = [
  { to: '/', icon: '⏱', label: 'Dashboard' },
  { to: '/tasks', icon: '✦', label: 'Tasks' },
  { to: '/chat', icon: '💬', label: 'AI Chat' },
];

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>⏳</div>
          <span className={styles.logoText}>Chronos AI</span>
        </div>

        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`
              }
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className={styles.userSection}>
          <div className={styles.userInfo}>
            <div className={styles.avatar}>
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div>
              <div className={styles.userName}>{user?.name || 'User'}</div>
              <div className={styles.userLevel}>
                Level {user?.stats?.level || 1} · {user?.stats?.total_xp || 0} XP
              </div>
            </div>
          </div>
          <button className={styles.logoutBtn} onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
