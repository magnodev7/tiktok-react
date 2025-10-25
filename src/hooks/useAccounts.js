import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/tiktok-accounts');
      return data ?? [];
    },
  });
}

export function useAddAccount() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (accountData) => {
      const { data, meta } = await apiClient.post('/api/tiktok-accounts', accountData);
      return { data, meta };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ accountId, accountData }) => {
      const { data, meta } = await apiClient.put(`/api/tiktok-accounts/${accountId}`, accountData);
      return { data, meta };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (accountId) => {
      const { data, meta } = await apiClient.delete(`/api/tiktok-accounts/${accountId}`);
      return { data, meta };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useActivateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (accountId) => {
      const { data, meta } = await apiClient.patch(`/api/tiktok-accounts/${accountId}/activate`);
      return { data, meta };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useDeactivateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (accountId) => {
      const { data, meta } = await apiClient.patch(`/api/tiktok-accounts/${accountId}/deactivate`);
      return { data, meta };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useUpdateCookies() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ accountId, cookies }) => {
      const { data, meta } = await apiClient.post(`/api/tiktok-accounts/${accountId}/update-cookies`, cookies);
      return { data, meta };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}
