import { useQuery } from '@tanstack/react-query';
import { getSchedulerStatus } from '@/services/api/scheduler';

/**
 * Hook para acompanhar o estado do scheduler de uma conta.
 * Ajusta dinamicamente o intervalo de atualização com base no status informado.
 */
export function useSchedulerActivity(accountName = null) {
  return useQuery({
    queryKey: ['schedulerStatus', accountName || 'all'],
    queryFn: async () => {
      const statuses = await getSchedulerStatus({ account: accountName || undefined });
      if (accountName) {
        return statuses.find(status => status.account_name === accountName) || null;
      }
      return statuses;
    },
    enabled: true,
    refetchIntervalInBackground: true,
    refetchInterval: (query) => {
      const status = query.state.data;
      if (!accountName || !status) {
        return 60 * 1000;
      }

      if (status.status === 'processing') {
        return 5 * 1000;
      }

      if (status.status === 'waiting' && status.next_due_at) {
        const diffMs = new Date(status.next_due_at).getTime() - Date.now();
        if (Number.isNaN(diffMs)) {
          return 60 * 1000;
        }
        if (diffMs <= 0) {
          return 5 * 1000;
        }
        if (diffMs <= 2 * 60 * 1000) {
          return 5 * 1000;
        }
        if (diffMs <= 10 * 60 * 1000) {
          return 15 * 1000;
        }
        if (diffMs <= 30 * 60 * 1000) {
          return 60 * 1000;
        }
        return 60 * 1000;
      }

      return 60 * 1000;
    },
  });
}

export default useSchedulerActivity;
