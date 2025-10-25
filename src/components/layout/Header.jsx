import { Search, Bell, Settings, LogOut, UserCircle, Clock, CheckCheck } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useNotifications } from '@/hooks/useNotifications';
import { getProfilePictureUrl } from '@/utils/staticFiles';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8082/').replace(/\/$/, '');

export default function Header() {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const notificationsRef = useRef(null);
  const profileRef = useRef(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  // Sistema real de notificações
  const {
    notifications,
    loading: notificationsLoading,
    unreadCount,
    markRead,
    markAllRead,
    refresh: refreshNotifications,
  } = useNotifications({
    pollingInterval: 30000, // Atualiza a cada 30 segundos
    limit: 15,
    autoStart: true,
  });

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) {
        setNotificationsOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const avatarUrl = getProfilePictureUrl(user?.profile_picture);
  const initials =
    user?.full_name?.charAt(0).toUpperCase() ||
    user?.username?.charAt(0).toUpperCase() ||
    'U';

  return (
    <header className="fixed top-0 right-0 left-60 h-16 bg-background-elevated/80 backdrop-blur-md border-b border-border z-30">
      <div className="flex items-center justify-between h-full px-6">
        {/* Breadcrumb / Page Title */}
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-semibold text-text-primary">Dashboard</h1>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-4">
          {/* Search */}
          <button className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border rounded-lg hover:border-accent transition-colors">
            <Search className="w-4 h-4 text-text-tertiary" />
            <span className="text-sm text-text-tertiary">Buscar...</span>
            <kbd className="px-1.5 py-0.5 text-xs bg-background-subtle rounded border border-border">
              ⌘K
            </kbd>
          </button>

          {/* Notifications */}
          <div className="relative" ref={notificationsRef}>
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="relative p-2 hover:bg-white/5 rounded-lg transition-colors"
            >
              <Bell className="w-5 h-5 text-text-secondary" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-5 h-5 bg-accent rounded-full flex items-center justify-center text-xs text-white font-medium">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notifications Dropdown */}
            {notificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-background-elevated border border-border rounded-lg shadow-xl overflow-hidden">
                <div className="p-4 border-b border-border flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-text-primary">Notificações</h3>
                    {unreadCount > 0 && (
                      <p className="text-xs text-text-tertiary mt-1">
                        {unreadCount} {unreadCount === 1 ? 'nova' : 'novas'}
                      </p>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-xs text-accent hover:underline flex items-center gap-1"
                      title="Marcar todas como lidas"
                    >
                      <CheckCheck className="w-3 h-3" />
                      Marcar lidas
                    </button>
                  )}
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {notificationsLoading && notifications.length === 0 ? (
                    <div className="p-8 text-center text-text-tertiary">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto mb-2"></div>
                      <p>Carregando...</p>
                    </div>
                  ) : notifications.length === 0 ? (
                    <div className="p-8 text-center text-text-tertiary">
                      <Bell className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>Nenhuma notificação</p>
                    </div>
                  ) : (
                    notifications.map((notification) => (
                      <div
                        key={notification.id}
                        onClick={() => !notification.read && markRead(notification.id)}
                        className={`p-4 border-b border-border hover:bg-white/5 cursor-pointer transition-colors ${
                          !notification.read ? 'bg-accent/5 border-l-2 border-l-accent' : ''
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <Clock className="w-4 h-4 text-accent mt-1 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-text-primary mb-1">
                              {notification.title}
                            </p>
                            <p className="text-xs text-text-secondary mb-1 line-clamp-2">
                              {notification.message}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <p className="text-xs text-text-tertiary">{notification.time}</p>
                              {notification.account && (
                                <span className="text-xs text-text-tertiary">• {notification.account}</span>
                              )}
                            </div>
                          </div>
                          {!notification.read && (
                            <div className="w-2 h-2 bg-accent rounded-full flex-shrink-0 mt-1"></div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <div className="p-3 border-t border-border flex items-center justify-between">
                  <button
                    onClick={refreshNotifications}
                    className="text-sm text-accent hover:underline"
                  >
                    Atualizar
                  </button>
                  <button
                    onClick={() => setNotificationsOpen(false)}
                    className="text-sm text-text-tertiary hover:text-text-primary"
                  >
                    Fechar
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Profile */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 p-1.5 hover:bg-white/5 rounded-lg transition-colors"
            >
              <div className="w-8 h-8 rounded-full flex items-center justify-center overflow-hidden bg-accent text-white">
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={user?.full_name || user?.username || 'Avatar'}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="font-medium text-sm">{initials}</span>
                )}
              </div>
            </button>

            {/* Profile Dropdown */}
            {profileOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-background-elevated border border-border rounded-lg shadow-xl overflow-hidden">
                {/* User Info */}
                <div className="p-4 border-b border-border">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full flex items-center justify-center overflow-hidden bg-accent text-white">
                      {avatarUrl ? (
                        <img
                          src={avatarUrl}
                          alt={user?.full_name || user?.username || 'Avatar'}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <span className="font-medium">{initials}</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-text-primary truncate">
                        {user?.full_name || user?.username || 'Usuário'}
                      </p>
                      <p className="text-xs text-text-tertiary truncate">
                        {user?.email || 'email@exemplo.com'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="py-2">
                  <button
                    onClick={() => {
                      setProfileOpen(false);
                      navigate('/settings');
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <UserCircle className="w-4 h-4" />
                    <span className="text-sm">Meu Perfil</span>
                  </button>
                  <button
                    onClick={() => {
                      setProfileOpen(false);
                      navigate('/settings');
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    <span className="text-sm">Configurações</span>
                  </button>
                </div>

                {/* Logout */}
                <div className="border-t border-border p-2">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-red-500/10 text-red-500 rounded-lg transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    <span className="text-sm font-medium">Sair</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
