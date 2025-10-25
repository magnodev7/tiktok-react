import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';

export function useScheduledVideos(accountName = null) {
  return useQuery({
    queryKey: ['videos', 'scheduled', accountName],
    queryFn: async () => {
      try {
        if (!accountName) return [];
        
        // ✅ Backend espera 'account' (string - account_name)
        const { data } = await apiClient.get('/api/scheduled', { 
          params: { account: accountName } 
        });

        return data?.scheduled_videos || [];
      } catch (error) {
        console.error('Erro ao buscar vídeos agendados:', error);
        return [];
      }
    },
    enabled: !!accountName, // Só executa se accountName existir
  });
}

export function useUploadVideo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (formData) => {
      const response = await apiClient.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    onSuccess: () => {
      // ✅ Invalida todas as queries de vídeos agendados
      queryClient.invalidateQueries({ queryKey: ['videos', 'scheduled'] });
      queryClient.invalidateQueries({ queryKey: ['videos'] });
    },
  });
}

export function useDeleteVideo() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ account, filename, mode = 'move' }) => {
      const { data, meta } = await apiClient.delete(`/api/videos/${account}/${filename}?mode=${mode}`);
      return { data, meta };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos', 'scheduled'] });
      queryClient.invalidateQueries({ queryKey: ['videos'] });
    },
  });
}
