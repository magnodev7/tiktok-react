import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';

// accountName: nome da conta TikTok (string) ou null para todas as contas
// days: número de dias para filtragem (default 30)
export function useAnalytics(accountName, days = 30) {
  return useQuery({
    queryKey: ['analytics', accountName, days],
    queryFn: async () => {
      // Constrói params - se accountName for null, não inclui o parâmetro account
      const params = { days_back: days };
      if (accountName) {
        params.account = accountName;
      }

      console.log('🔍 [useAnalytics] Chamando API com params:', params);

      const { data } = await apiClient.get('/api/analytics/summary', { params });

      console.log('✅ [useAnalytics] Resposta recebida:', JSON.stringify(data, null, 2));
      console.log('📊 [useAnalytics] Overview:', JSON.stringify(data?.overview, null, 2));
      console.log('🎯 [useAnalytics] Total de vídeos:', data?.overview?.total_videos);

      // Retorna os dados analíticos para o componente usar
      return data ?? {};
    },
    // Sempre habilitado, mesmo quando accountName é null (para ver todas as contas)
    enabled: true,
    staleTime: 60 * 1000, // 1 minuto cache
    retry: 1,
    onError: (error) => {
      console.error('❌ [useAnalytics] Erro ao buscar analytics:', error);
      console.error('❌ [useAnalytics] Response:', error.response?.data);
    },
  });
}
