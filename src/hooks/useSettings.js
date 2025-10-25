import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';

// Hook para atualizar perfil do usuário
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (profileData) => {
      const { data } = await apiClient.put('/auth/me', profileData);
      return data;
    },
    onSuccess: () => {
      // Invalida cache do usuário atual
      queryClient.invalidateQueries(['auth', 'me']);
    },
  });
}

// Hook para alterar senha
export function useChangePassword() {
  return useMutation({
    mutationFn: async ({ oldPassword, newPassword }) => {
      const { data } = await apiClient.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      });
      return data;
    },
  });
}

// Hook para gerenciar preferências do usuário (com backend)
export function useUserPreferences() {
  const queryClient = useQueryClient();

  // Query para buscar preferências
  const { data: preferences, isLoading } = useQuery({
    queryKey: ['auth', 'preferences'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/auth/preferences');
        return data;
      } catch (error) {
        // Se falhar, retorna preferências padrão
        return {
          theme: 'dark',
          accent_color: '#0ea5e9',
          notifications: {
            videoPublished: true,
            publicationFailed: true,
            highCapacity: true,
          },
          timezone: 'America/Sao_Paulo',
        };
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutos cache
  });

  // Mutation para atualizar preferências
  const updateMutation = useMutation({
    mutationFn: async (newPreferences) => {
      const { data } = await apiClient.put('/auth/preferences', newPreferences);
      return data;
    },
    onSuccess: (data) => {
      // Atualiza cache local
      queryClient.setQueryData(['auth', 'preferences'], data);

      // Aplica tema imediatamente
      if (data.theme) {
        applyTheme(data.theme);
      }

      // Aplica cor de destaque imediatamente
      if (data.accent_color) {
        applyAccentColor(data.accent_color);
      }
    },
  });

  const applyTheme = (theme) => {
    if (theme === 'light') {
      document.documentElement.classList.remove('dark');
    } else if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else if (theme === 'system') {
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.classList.toggle('dark', isDark);
    }
  };

  const applyAccentColor = (color) => {
    document.documentElement.style.setProperty('--color-accent', color);
  };

  // Inicializa tema e cor ao carregar
  const initPreferences = () => {
    if (preferences) {
      applyTheme(preferences.theme);
      applyAccentColor(preferences.accent_color);
    }
  };

  return {
    preferences,
    isLoading,
    updatePreferences: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    initPreferences,
    applyTheme,
    applyAccentColor,
  };
}
