import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';

export function useLogs(limit = 50, accountName = null, enableAutoRefresh = true) {
  return useQuery({
    queryKey: ['logs', limit, accountName],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', limit);
      if (accountName) {
        params.append('account', accountName);
      }

      const { data } = await apiClient.get(`/api/logs?${params.toString()}`);
      return data?.logs || [];
    },
    refetchInterval: enableAutoRefresh ? 3000 : false, // Atualiza mais rápido quando ao vivo
  });
}
