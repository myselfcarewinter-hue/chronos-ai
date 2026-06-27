import styles from './StatCard.module.css';

export default function StatCard({ title, value, subtext, icon }) {
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardTitle}>{title}</span>
        {icon && <span>{icon}</span>}
      </div>
      <div className={styles.cardValue}>{value}</div>
      {subtext && <div className={styles.cardSubtext}>{subtext}</div>}
    </div>
  );
}
