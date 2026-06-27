import styles from './Badge.module.css';

export default function Badge({ label, variant }) {
  const key = (variant || label || 'medium').toLowerCase().replace(/[ -]/g, '_');
  return <span className={`${styles.badge} ${styles[key] || styles.medium}`}>{label || variant}</span>;
}
