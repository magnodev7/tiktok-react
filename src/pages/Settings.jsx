import React, { useState, useEffect } from 'react';
import { User, Bell, Palette, Key } from 'lucide-react';
import AdminUsers from './AdminUsers.jsx';
import APIKeys from '@/components/APIKeys';
import Card from '@/components/common/Card';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import { useAuth } from '@/contexts/AuthContext';
import { useUpdateProfile, useChangePassword, useUserPreferences } from '@/hooks/useSettings';
import api from '@/api/client';
import { getProfilePictureUrl } from '@/utils/staticFiles';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8082/').replace(/\/$/, '');

export default function Settings() {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');

  // Profile state
  const [profileData, setProfileData] = useState({
    full_name: '',
    email: '',
  });

  // Password state
  const [passwordData, setPasswordData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  // Hooks
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const {
    preferences,
    isLoading: prefsLoading,
    updatePreferences,
    isUpdating,
    initPreferences,
  } = useUserPreferences();

  // Initialize profile data when user loads
  useEffect(() => {
    if (user) {
      setProfileData({
        full_name: user.full_name || '',
        email: user.email || '',
      });
    }
  }, [user]);

  // Initialize preferences on mount
  useEffect(() => {
    initPreferences();
  }, [preferences]);

  const handleProfileSave = () => {
    updateProfile.mutate(profileData, {
      onSuccess: async (data) => {
        await refreshUser();
        if (data?.full_name || data?.email) {
          setProfileData({
            full_name: data.full_name ?? profileData.full_name,
            email: data.email ?? profileData.email,
          });
        }
        alert('✅ Perfil atualizado com sucesso!');
      },
      onError: (error) => {
        const apiError = error.response?.data;
        alert('❌ ' + (apiError?.message || apiError?.detail || 'Erro ao atualizar perfil'));
      },
    });
  };

  const handlePasswordChange = () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      alert('❌ As senhas não conferem');
      return;
    }

    if (passwordData.newPassword.length < 6) {
      alert('❌ A senha deve ter pelo menos 6 caracteres');
      return;
    }

    changePassword.mutate(
      {
        oldPassword: passwordData.oldPassword,
        newPassword: passwordData.newPassword,
      },
      {
        onSuccess: () => {
          alert('✅ Senha alterada com sucesso!');
          setPasswordData({
            oldPassword: '',
            newPassword: '',
            confirmPassword: '',
          });
        },
        onError: (error) => {
          const apiError = error.response?.data;
          alert('❌ ' + (apiError?.message || apiError?.detail || 'Erro ao alterar senha'));
        },
      }
    );
  };

  const handleThemeChange = (theme) => {
    updatePreferences({ theme });
  };

  const handleAccentColorChange = (color) => {
    updatePreferences({ accent_color: color });
  };

  const handleNotificationToggle = (key, value) => {
    const newNotifications = {
      ...(preferences?.notifications || {}),
      [key]: value,
    };
    updatePreferences({ notifications: newNotifications });
  };

  const avatarUrl = getProfilePictureUrl(user?.profile_picture);

  const handleProfilePictureUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Valida tipo de arquivo
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      alert('Tipo de arquivo não permitido. Use JPG, PNG, GIF ou WebP');
      return;
    }

    // Valida tamanho (5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Arquivo muito grande. Tamanho máximo: 5MB');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/auth/me/profile-picture', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      await refreshUser();
      alert('Foto de perfil atualizada com sucesso!');
    } catch (error) {
      console.error('Erro ao fazer upload da foto:', error);
      const apiError = error.response?.data;
      alert(apiError?.message || apiError?.detail || 'Erro ao fazer upload da foto de perfil');
    }
  };

  const handleProfilePictureDelete = async () => {
    if (!window.confirm('Tem certeza que deseja remover sua foto de perfil?')) {
      return;
    }

    try {
      await api.delete('/auth/me/profile-picture');
      await refreshUser();
      alert('Foto de perfil removida com sucesso!');
    } catch (error) {
      console.error('Erro ao remover foto:', error);
      const apiError = error.response?.data;
      alert(apiError?.message || apiError?.detail || 'Erro ao remover foto de perfil');
    }
  };

  const tabs = [
    { id: 'profile', label: 'Perfil', icon: User },
    { id: 'notifications', label: 'Notificações', icon: Bell },
    { id: 'appearance', label: 'Aparência', icon: Palette },
    { id: 'api', label: 'API', icon: Key },
    ...(user?.is_admin ? [{ id: 'admin-users', label: 'Admin Usuários', icon: User }] : []),
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary mb-2">Configurações</h1>
        <p className="text-text-secondary">Gerencie suas preferências e configurações</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <Card className="lg:col-span-1 h-fit">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left
                    transition-colors
                    ${
                      activeTab === tab.id
                        ? 'bg-accent-subtle text-accent'
                        : 'text-text-secondary hover:bg-white/5 hover:text-text-primary'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </Card>

        {/* Content */}
        <div className="lg:col-span-3">
          {activeTab === 'profile' && (
            <Card>
              <h2 className="text-xl font-semibold text-text-primary mb-6">Perfil</h2>
              <div className="space-y-6">
                {/* Profile Info */}
                <div className="space-y-4">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="relative">
                      {avatarUrl ? (
                        <img
                          src={avatarUrl}
                          alt="Profile"
                          className="w-20 h-20 rounded-full object-cover border-2 border-accent"
                        />
                      ) : (
                        <div className="w-20 h-20 rounded-full bg-accent flex items-center justify-center">
                          <span className="text-3xl font-bold text-white">
                            {user?.full_name?.charAt(0).toUpperCase() || user?.username?.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      )}
                      <label
                        htmlFor="profile-picture-upload"
                        className="absolute bottom-0 right-0 bg-accent hover:bg-accent-hover text-white rounded-full p-2 cursor-pointer shadow-lg transition-colors"
                        title="Alterar foto de perfil"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      </label>
                      <input
                        id="profile-picture-upload"
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleProfilePictureUpload}
                      />
                    </div>
                    <div>
                      <p className="text-sm text-text-secondary">JPG, PNG ou GIF - Max 5MB</p>
                      {user?.profile_picture && (
                        <button
                          onClick={handleProfilePictureDelete}
                          className="text-sm text-red-400 hover:text-red-300 mt-1"
                        >
                          Remover foto
                        </button>
                      )}
                    </div>
                  </div>
                  <Input
                    label="Nome Completo"
                    value={profileData.full_name}
                    onChange={(value) => setProfileData({ ...profileData, full_name: value })}
                  />
                  <Input
                    label="Email"
                    type="email"
                    value={profileData.email}
                    onChange={(value) => setProfileData({ ...profileData, email: value })}
                  />
                  <Input
                    label="Usuário"
                    value={user?.username || ''}
                    disabled
                  />
                  <div className="flex gap-3 pt-4">
                    <Button
                      onClick={handleProfileSave}
                      disabled={updateProfile.isPending}
                    >
                      {updateProfile.isPending ? 'Salvando...' : 'Salvar Alterações'}
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setProfileData({
                          full_name: user?.full_name || '',
                          email: user?.email || '',
                        });
                      }}
                    >
                      Cancelar
                    </Button>
                  </div>
                </div>

                {/* Change Password */}
                <div className="pt-6 border-t border-border space-y-4">
                  <h3 className="text-lg font-semibold text-text-primary">Alterar Senha</h3>
                  <Input
                    label="Senha Atual"
                    type="password"
                    value={passwordData.oldPassword}
                    onChange={(value) => setPasswordData({ ...passwordData, oldPassword: value })}
                  />
                  <Input
                    label="Nova Senha"
                    type="password"
                    value={passwordData.newPassword}
                    onChange={(value) => setPasswordData({ ...passwordData, newPassword: value })}
                  />
                  <Input
                    label="Confirmar Nova Senha"
                    type="password"
                    value={passwordData.confirmPassword}
                    onChange={(value) => setPasswordData({ ...passwordData, confirmPassword: value })}
                  />
                  <Button
                    onClick={handlePasswordChange}
                    disabled={changePassword.isPending}
                  >
                    {changePassword.isPending ? 'Alterando...' : 'Alterar Senha'}
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'notifications' && (
            <Card>
              <h2 className="text-xl font-semibold text-text-primary mb-6">Notificações</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="font-medium text-text-primary">Vídeo publicado</p>
                    <p className="text-sm text-text-secondary">Notificar quando um vídeo for publicado</p>
                  </div>
                  <input
                    type="checkbox"
                    className="w-5 h-5 rounded"
                    checked={preferences?.notifications?.videoPublished ?? true}
                    onChange={(e) => handleNotificationToggle('videoPublished', e.target.checked)}
                  />
                </div>
                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="font-medium text-text-primary">Falha na publicação</p>
                    <p className="text-sm text-text-secondary">Notificar quando houver erro</p>
                  </div>
                  <input
                    type="checkbox"
                    className="w-5 h-5 rounded"
                    checked={preferences?.notifications?.publicationFailed ?? true}
                    onChange={(e) => handleNotificationToggle('publicationFailed', e.target.checked)}
                  />
                </div>
                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="font-medium text-text-primary">Capacidade alta</p>
                    <p className="text-sm text-text-secondary">Alertar quando capacidade {'>'} 90%</p>
                  </div>
                  <input
                    type="checkbox"
                    className="w-5 h-5 rounded"
                    checked={preferences?.notifications?.highCapacity ?? true}
                    onChange={(e) => handleNotificationToggle('highCapacity', e.target.checked)}
                  />
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'appearance' && (
            <Card>
              <h2 className="text-xl font-semibold text-text-primary mb-6">Aparência</h2>
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-3">Tema</label>
                  <div className="grid grid-cols-3 gap-3">
                    <button
                      onClick={() => handleThemeChange('dark')}
                      className={`p-4 bg-background rounded-lg transition-all ${
                        preferences?.theme === 'dark'
                          ? 'border-2 border-accent'
                          : 'border border-border hover:border-accent'
                      }`}
                    >
                      <div className="w-full h-20 bg-background-subtle rounded mb-2"></div>
                      <p className="text-sm font-medium text-text-primary">Escuro</p>
                    </button>
                    <button
                      onClick={() => handleThemeChange('light')}
                      className={`p-4 bg-background rounded-lg transition-all ${
                        preferences?.theme === 'light'
                          ? 'border-2 border-accent'
                          : 'border border-border hover:border-accent'
                      }`}
                    >
                      <div className="w-full h-20 bg-white rounded mb-2"></div>
                      <p className="text-sm font-medium text-text-primary">Claro</p>
                    </button>
                    <button
                      onClick={() => handleThemeChange('system')}
                      className={`p-4 bg-background rounded-lg transition-all ${
                        preferences?.theme === 'system'
                          ? 'border-2 border-accent'
                          : 'border border-border hover:border-accent'
                      }`}
                    >
                      <div className="w-full h-20 bg-gradient-to-br from-background-subtle to-white rounded mb-2"></div>
                      <p className="text-sm font-medium text-text-primary">Sistema</p>
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-3">
                    Cor de Destaque
                  </label>
                  <div className="flex gap-3">
                    {[
                      { color: '#0ea5e9', name: 'Azul' },
                      { color: '#3b82f6', name: 'Azul Escuro' },
                      { color: '#8b5cf6', name: 'Roxo' },
                      { color: '#10b981', name: 'Verde' },
                      { color: '#ef4444', name: 'Vermelho' },
                    ].map(({ color }) => (
                      <button
                        key={color}
                        onClick={() => handleAccentColorChange(color)}
                        className={`w-10 h-10 rounded-lg transition-all ${
                          preferences?.accent_color === color
                            ? 'ring-2 ring-offset-2 ring-offset-background'
                            : 'hover:ring-2 hover:ring-offset-2 hover:ring-offset-background'
                        }`}
                        style={{
                          backgroundColor: color,
                          ringColor: color,
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'api' && (
            <Card>
              <APIKeys />
            </Card>
          )}

          {activeTab === 'admin-users' && user?.is_admin && (
            <div className="mt-6">
              <AdminUsers />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
