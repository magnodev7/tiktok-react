import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';

const queryKey = (accountName, limit) => ['recentVideos', accountName, limit];

export function useRecentVideos(accountName, limit = 3) {
  return useQuery({
    queryKey: queryKey(accountName, limit),
    queryFn: async () => {
      const { data } = await apiClient.get(`/api/analytics/accounts/${accountName}/recent-videos`, {
        params: { limit },
      });
      return data;
    },
    enabled: Boolean(accountName),
    staleTime: 60 * 1000,
  });
}

export function usePinRecentVideo(accountName, limit = 3) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (videoId) => {
      if (!accountName) {
        throw new Error('Selecione uma conta para fixar vídeos.');
      }
      const { data } = await apiClient.post(`/api/analytics/accounts/${accountName}/recent-videos/pin`, {
        video_id: videoId,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recentVideos', accountName], exact: false });
      queryClient.invalidateQueries({ queryKey: queryKey(accountName, limit) });
    },
  });
}

export function useUnpinRecentVideo(accountName, limit = 3) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (videoId) => {
      if (!accountName) {
        throw new Error('Selecione uma conta para gerenciar vídeos fixados.');
      }
      const { data } = await apiClient.delete(
        `/api/analytics/accounts/${accountName}/recent-videos/pin/${videoId}`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recentVideos', accountName], exact: false });
      queryClient.invalidateQueries({ queryKey: queryKey(accountName, limit) });
    },
  });
}
