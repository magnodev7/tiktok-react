import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';

export function useAccountMetrics(accountName) {
  return useQuery({
    queryKey: ['accountMetrics', accountName],
    queryFn: async () => {
      if (!accountName) return null;
      const { data, meta } = await apiClient.get(`/api/analytics/accounts/${accountName}/metrics`);
      if (!data && meta?.message) {
        console.info('[useAccountMetrics] Nenhuma métrica registrada ainda:', meta.message);
      }
      return data;
    },
    enabled: Boolean(accountName),
    staleTime: 60 * 1000,
    retry: 1,
    onError: (error) => {
      console.error('[useAccountMetrics] Erro ao buscar métricas da conta:', error);
    },
  });
}

export function useAccountMetricsHistory(accountName, { days = null, limit = 90 } = {}) {
  return useQuery({
    queryKey: ['accountMetricsHistory', accountName, days, limit],
    queryFn: async () => {
      if (!accountName) return [];
      const params = { limit };
      if (days) {
        params.days = days;
      }
      const { data } = await apiClient.get(`/api/analytics/accounts/${accountName}/metrics/history`, { params });
      return Array.isArray(data) ? data : [];
    },
    enabled: Boolean(accountName),
    staleTime: 5 * 60 * 1000,
    retry: 1,
    onError: (error) => {
      console.error('[useAccountMetricsHistory] Erro ao buscar histórico de métricas:', error);
    },
  });
}
