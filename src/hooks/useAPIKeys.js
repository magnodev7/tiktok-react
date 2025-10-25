import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';

export function useAPIKeys() {
  const queryClient = useQueryClient();

  // Fetch API Keys
  const { data: apiKeys, isLoading, error } = useQuery({
    queryKey: ['apiKeys'],
    queryFn: async () => {
      const response = await api.get('/auth/api-keys');
      return response.data ?? [];
    },
  });

  // Create API Key
  const createAPIKey = useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/auth/api-keys', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
    },
  });

  // Delete API Key
  const deleteAPIKey = useMutation({
    mutationFn: async (keyId) => {
      const response = await api.delete(`/auth/api-keys/${keyId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
    },
  });

  // Toggle API Key Status
  const toggleAPIKey = useMutation({
    mutationFn: async ({ keyId, isActive }) => {
      const response = await api.patch(`/auth/api-keys/${keyId}/status`, {
        is_active: isActive,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
    },
  });

  return {
    apiKeys,
    isLoading,
    error,
    createAPIKey,
    deleteAPIKey,
    toggleAPIKey,
  };
}
