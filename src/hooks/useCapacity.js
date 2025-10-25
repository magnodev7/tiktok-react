import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';

/**
 * Hook para buscar capacidade de agendamento de uma conta
 * @param {number} accountId - ID da conta TikTok
 * @param {number} days - Número de dias para análise (padrão: 30)
 */
export function useAccountCapacity(accountId, days = 30) {
  return useQuery({
    queryKey: ['capacity', accountId, days],
    queryFn: async () => {
      if (!accountId) return null;

      const { data } = await apiClient.get(`/api/posting-schedules/${accountId}/capacity`, {
        params: { days }
      });

      return data ?? null;
    },
    enabled: !!accountId,
    staleTime: 30 * 1000, // 30 segundos cache
    retry: 1,
  });
}

/**
 * Hook para buscar alertas de capacidade de uma conta
 * @param {number} accountId - ID da conta TikTok
 * @param {number} days - Número de dias para análise (padrão: 7)
 */
export function useCapacityAlerts(accountId, days = 7) {
  return useQuery({
    queryKey: ['capacity-alerts', accountId, days],
    queryFn: async () => {
      if (!accountId) return [];

      const { data } = await apiClient.get(`/api/posting-schedules/${accountId}/alerts`, {
        params: { days }
      });

      return data || [];
    },
    enabled: !!accountId,
    staleTime: 60 * 1000, // 1 minuto cache
    retry: 1,
  });
}
