import { Link, useLocation } from 'react-router-dom';
import { Home, Calendar, Users, BarChart3, Settings, FileText, ChevronLeft, ChevronRight, TrendingUp, Wrench } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import logomarca from '@/assets/logomarca.png';
import { getProfilePictureUrl } from '@/utils/staticFiles';

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard', shortcut: '⌘1' },
  { path: '/schedules', icon: Calendar, label: 'Agendamentos', shortcut: '⌘2' },
  { path: '/accounts', icon: Users, label: 'Contas TikTok', shortcut: '⌘3' },
  { path: '/growth', icon: TrendingUp, label: 'Crescimento', shortcut: '⌘4' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics', shortcut: '⌘5' },
  { path: '/logs', icon: FileText, label: 'Logs', shortcut: '⌘6' },
  { path: '/maintenance', icon: Wrench, label: 'Manutenção', shortcut: '⌘M', adminOnly: true },
  { path: '/settings', icon: Settings, label: 'Configurações', shortcut: '⌘,' },
];

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuth();

  const avatarUrl = getProfilePictureUrl(user?.profile_picture);
  const initials =
    user?.full_name?.charAt(0).toUpperCase() ||
    user?.username?.charAt(0).toUpperCase() ||
    'U';

  return (
    <aside className={`
      fixed left-0 top-0 h-screen bg-background-subtle border-r border-border
      transition-all duration-300 z-40 flex flex-col
      ${isCollapsed ? 'w-16' : 'w-60'}
    `}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
        {!isCollapsed ? (
          <div className="flex items-center gap-3 flex-1">
            <img
              src={logomarca}
              alt="Logo"
              className="w-10 h-10 object-contain filter brightness-0 invert"
            />
            <span className="font-semibold text-text-primary">Autegra Monetiza</span>
          </div>
        ) : (
          <img
            src={logomarca}
            alt="Logo"
            className="w-8 h-8 object-contain filter brightness-0 invert mx-auto"
          />
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 hover:bg-white/5 rounded-lg transition-colors flex-shrink-0"
        >
          {isCollapsed ? (
            <ChevronRight className="w-5 h-5 text-text-secondary" />
          ) : (
            <ChevronLeft className="w-5 h-5 text-text-secondary" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {navItems
          .filter(item => !item.adminOnly || user?.is_admin)
          .map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg
                transition-all duration-200 group relative
                ${isActive 
                  ? 'bg-accent-subtle text-accent border-l-2 border-accent' 
                  : 'text-text-secondary hover:bg-white/5 hover:text-text-primary'
                }
                ${isCollapsed ? 'justify-center' : ''}
              `}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && (
                <>
                  <span className="flex-1 font-medium">{item.label}</span>
                  <span className="text-xs text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity">
                    {item.shortcut}
                  </span>
                </>
              )}
              
              {/* Tooltip for collapsed state */}
              {isCollapsed && (
                <div className="
                  absolute left-full ml-2 px-2 py-1 bg-background-elevated
                  text-sm text-text-primary rounded-lg shadow-lg
                  opacity-0 group-hover:opacity-100 pointer-events-none
                  transition-opacity whitespace-nowrap z-50
                ">
                  {item.label}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="p-3 border-t border-border flex-shrink-0">
        <div className={`
          flex items-center gap-3 p-2 rounded-lg
          ${isCollapsed ? 'justify-center' : ''}
        `}>
          <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden bg-accent text-white">
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
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {user?.full_name || user?.username || 'Usuário'}
              </p>
              <button
                onClick={logout}
                className="text-xs text-text-tertiary hover:text-accent transition-colors text-left"
              >
                Sair
              </button>
            </div>
          )}

          {/* Tooltip for collapsed state */}
          {isCollapsed && (
            <div className="
              absolute left-full ml-2 px-3 py-2 bg-background-elevated
              text-sm rounded-lg shadow-lg border border-border
              opacity-0 hover:opacity-100 pointer-events-none
              transition-opacity whitespace-nowrap z-50
            ">
              <p className="text-text-primary font-medium">{user?.full_name || user?.username || 'Usuário'}</p>
              <button
                onClick={logout}
                className="text-xs text-text-tertiary hover:text-accent transition-colors mt-1 block"
              >
                Sair
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
