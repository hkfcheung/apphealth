/**
 * Format a date to a relative time string
 */
export function formatRelativeTime(dateString) {
  if (!dateString) return 'Never';

  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

  return date.toLocaleDateString();
}

/**
 * Format a date to a full datetime string
 */
export function formatDateTime(dateString) {
  if (!dateString) return 'N/A';

  const date = new Date(dateString);
  return date.toLocaleString();
}

/**
 * Calculate seconds remaining until next poll
 */
export function getSecondsUntilNextPoll(nextPollAt) {
  if (!nextPollAt) return null;

  const next = new Date(nextPollAt);
  const now = new Date();
  const seconds = Math.floor((next - now) / 1000);

  return Math.max(0, seconds);
}

/**
 * Format seconds to mm:ss
 */
export function formatCountdown(seconds) {
  if (seconds === null || seconds === undefined) return '--:--';

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;

  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Get status color class
 */
export function getStatusColor(status) {
  const colors = {
    operational: 'bg-operational text-white',
    recently_resolved: 'bg-recently-resolved text-white',
    degraded: 'bg-degraded text-white',
    incident: 'bg-incident text-white',
    maintenance: 'bg-maintenance text-white',
    unknown: 'bg-unknown text-white',
  };

  return colors[status] || colors.unknown;
}

/**
 * Get status display name
 */
export function getStatusDisplayName(status) {
  const names = {
    operational: 'Operational',
    recently_resolved: '🔄 Recently Resolved',
    degraded: 'Degraded',
    incident: 'Incident',
    maintenance: 'Maintenance',
    unknown: 'Unknown',
  };

  return names[status] || 'Unknown';
}
