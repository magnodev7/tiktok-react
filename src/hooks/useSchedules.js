import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';

export function useSchedules(accountId) {
  return useQuery({
    queryKey: ['schedules', accountId],
    queryFn: async () => {
      if (!accountId) return [];
      
      // ✅ Endpoint correto: GET /api/posting-schedules/{account_id}/active
      const { data } = await apiClient.get(`/api/posting-schedules/${accountId}/active`);
      return data || [];
    },
    enabled: !!accountId,
    retry: 1,
  });
}

export function useSaveSchedules() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ accountId, schedules }) => {
      // ✅ Endpoint correto: POST /api/posting-schedules/{account_id}/bulk
      const { data } = await apiClient.post(`/api/posting-schedules/${accountId}/bulk`, {
        time_slots: schedules,
      });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['schedules', variables.accountId] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useDeleteSchedules() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (accountId) => {
      // ✅ Endpoint correto: DELETE /api/posting-schedules/{account_id}/schedules
      const { data } = await apiClient.delete(`/api/posting-schedules/${accountId}/schedules`);
      return data;
    },
    onSuccess: (_, accountId) => {
      queryClient.invalidateQueries({ queryKey: ['schedules', accountId] });
    },
  });
}
