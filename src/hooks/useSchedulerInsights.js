import { useEffect, useMemo, useState } from 'react';
import useSchedulerActivity from './useSchedulerActivity';

function formatCountdown(seconds) {
  if (seconds == null) return null;
  const clamped = Math.max(0, seconds);
  const hours = Math.floor(clamped / 3600);
  const minutes = Math.floor((clamped % 3600) / 60);
  const secs = clamped % 60;

  if (hours > 0) {
    return `${hours}h ${minutes.toString().padStart(2, '0')}min`;
  }
  if (minutes > 0) {
    return `${minutes}min ${secs.toString().padStart(2, '0')}s`;
  }
  return `${secs}s`;
}

/**
 * Expõe estado do scheduler com contagem regressiva e intervalos recomendados.
 */
export function useSchedulerInsights(accountName = null) {
  const queryResult = useSchedulerActivity(accountName);

  const status = useMemo(() => {
    const raw = queryResult.data;
    if (!raw) {
      return null;
    }
    if (accountName) {
      return Array.isArray(raw) ? null : raw;
    }
    if (Array.isArray(raw)) {
      return raw
        .filter((entry) => entry?.next_due_at)
        .sort((a, b) => new Date(a.next_due_at).getTime() - new Date(b.next_due_at).getTime())[0] || null;
    }
    return raw;
  }, [queryResult.data, accountName]);

  const [secondsRemaining, setSecondsRemaining] = useState(null);
  const nextDueDate = status?.next_due_at ? new Date(status.next_due_at) : null;

  useEffect(() => {
    if (!status?.next_due_at || status.status === 'processing') {
      setSecondsRemaining(null);
      return undefined;
    }

    const target = new Date(status.next_due_at).getTime();
    if (Number.isNaN(target)) {
      setSecondsRemaining(null);
      return undefined;
    }

    const updateCountdown = () => {
      const diffSeconds = Math.round((target - Date.now()) / 1000);
      setSecondsRemaining(diffSeconds);
    };

    updateCountdown();
    const timer = window.setInterval(updateCountdown, 1000);
    return () => window.clearInterval(timer);
  }, [status?.next_due_at, status?.status]);

  const countdownLabel = useMemo(
    () => formatCountdown(secondsRemaining),
    [secondsRemaining]
  );

  const autoRefreshInterval = useMemo(() => {
    if (!status) {
      return 60_000;
    }
    if (status.status === 'processing') {
      return 5_000;
    }
    if (secondsRemaining == null) {
      return 5 * 60_000;
    }
    if (secondsRemaining <= 0) {
      return 5_000;
    }
    if (secondsRemaining <= 120) {
      return 5_000;
    }
    if (secondsRemaining <= 600) {
      return 15_000;
    }
    if (secondsRemaining <= 900) {
      return 60_000;
    }
    if (secondsRemaining <= 3600) {
      return 5 * 60_000;
    }
    return 15 * 60_000;
  }, [status, secondsRemaining]);

  return {
    ...queryResult,
    status,
    secondsRemaining,
    countdownLabel,
    autoRefreshInterval,
    nextDueDate,
  };
}

export default useSchedulerInsights;
