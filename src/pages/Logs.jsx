import { FileText, Search, RefreshCw, Filter, AlertCircle, Info, AlertTriangle, XCircle, Pause, Play, Clock } from 'lucide-react';
import { useState } from 'react';
import Card from '@/components/common/Card';
import Input from '@/components/common/Input';
import Badge from '@/components/common/Badge';
import { useLogs } from '@/hooks/useLogs';
import { useAccounts } from '@/hooks/useAccounts';
import Spinner from '@/components/common/Spinner';

export default function Logs() {
  const [limit, setLimit] = useState(50);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [levelFilter, setLevelFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { data: logs, isLoading, refetch, dataUpdatedAt } = useLogs(limit, selectedAccount, !isPaused);
  const { data: accounts } = useAccounts();

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  // Formatar tempo relativo
  const getRelativeTime = (timestamp) => {
    if (!timestamp) return 'Data não disponível';

    const now = new Date();
    const date = new Date(timestamp);
    const diffInSeconds = Math.floor((now - date) / 1000);

    if (diffInSeconds < 60) return 'agora mesmo';
    if (diffInSeconds < 3600) return `há ${Math.floor(diffInSeconds / 60)} min`;
    if (diffInSeconds < 86400) return `há ${Math.floor(diffInSeconds / 3600)} h`;
    if (diffInSeconds < 604800) return `há ${Math.floor(diffInSeconds / 86400)} dias`;

    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getLevelIcon = (level) => {
    switch (level?.toLowerCase()) {
      case 'error':
      case 'critical':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'info':
        return <Info className="w-4 h-4 text-blue-500" />;
      default:
        return <FileText className="w-4 h-4 text-text-tertiary" />;
    }
  };

  const getLevelBadgeVariant = (level) => {
    switch (level?.toLowerCase()) {
      case 'error':
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'secondary';
    }
  };

  const filteredLogs = logs?.filter(log => {
    // Filtro por nível
    if (levelFilter !== 'all' && log.level?.toLowerCase() !== levelFilter) {
      return false;
    }

    // Filtro por busca
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      return (
        log.message?.toLowerCase().includes(searchLower) ||
        log.account_name?.toLowerCase().includes(searchLower) ||
        log.module?.toLowerCase().includes(searchLower)
      );
    }

    return true;
  })?.sort((a, b) => {
    // Ordena do mais recente (topo) para o mais antigo (baixo)
    const dateA = new Date(a.created_at || 0);
    const dateB = new Date(b.created_at || 0);
    return dateB - dateA;
  });

  const levelCounts = logs?.reduce((acc, log) => {
    const level = log.level?.toLowerCase() || 'debug';
    acc[level] = (acc[level] || 0) + 1;
    return acc;
  }, {}) || {};

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-text-primary">Logs do Sistema</h1>
          <div className="flex items-center gap-3">
            {/* Indicador de atualização em tempo real */}
            <div className="flex items-center gap-2 text-sm">
              {!isPaused && (
                <div className="flex items-center gap-2 text-green-500">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                  <span>Ao vivo</span>
                </div>
              )}
              {isPaused && (
                <div className="flex items-center gap-2 text-yellow-500">
                  <Pause className="w-4 h-4" />
                  <span>Pausado</span>
                </div>
              )}
            </div>
            {/* Última atualização */}
            <span className="text-xs text-text-tertiary flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(dataUpdatedAt).toLocaleTimeString('pt-BR')}
            </span>
          </div>
        </div>
        <p className="text-text-secondary">Acompanhe os eventos e atividades em tempo real</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <p className="text-sm text-text-secondary mb-1">Total de Logs</p>
          <p className="text-2xl font-bold text-text-primary">{logs?.length || 0}</p>
        </Card>
        <Card>
          <p className="text-sm text-text-secondary mb-1 flex items-center gap-1">
            <XCircle className="w-4 h-4 text-red-500" /> Erros
          </p>
          <p className="text-2xl font-bold text-red-500">{levelCounts.error || 0}</p>
        </Card>
        <Card>
          <p className="text-sm text-text-secondary mb-1 flex items-center gap-1">
            <AlertTriangle className="w-4 h-4 text-yellow-500" /> Avisos
          </p>
          <p className="text-2xl font-bold text-yellow-500">{levelCounts.warning || 0}</p>
        </Card>
        <Card>
          <p className="text-sm text-text-secondary mb-1 flex items-center gap-1">
            <Info className="w-4 h-4 text-blue-500" /> Info
          </p>
          <p className="text-2xl font-bold text-blue-500">{levelCounts.info || 0}</p>
        </Card>
        <Card>
          <p className="text-sm text-text-secondary mb-1">Debug</p>
          <p className="text-2xl font-bold text-text-primary">{levelCounts.debug || 0}</p>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
              <input
                type="text"
                placeholder="Buscar logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-10 pl-10 pr-4 bg-background border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
          </div>

          {/* Account Filter */}
          <select
            value={selectedAccount || ''}
            onChange={(e) => setSelectedAccount(e.target.value || null)}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Todas as contas</option>
            {accounts?.map((account) => (
              <option key={account.id} value={account.account_name}>
                {account.account_name}
              </option>
            ))}
          </select>

          {/* Level Filter */}
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="all">Todos os níveis</option>
            <option value="error">Erros</option>
            <option value="warning">Avisos</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>

          {/* Limit */}
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value={50}>50 logs</option>
            <option value={100}>100 logs</option>
            <option value={200}>200 logs</option>
            <option value={500}>500 logs</option>
          </select>

          {/* Pause/Resume */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`h-10 px-4 rounded-lg transition-colors flex items-center gap-2 ${
              isPaused
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-yellow-500 hover:bg-yellow-600 text-white'
            }`}
          >
            {isPaused ? (
              <>
                <Play className="w-4 h-4" />
                Retomar
              </>
            ) : (
              <>
                <Pause className="w-4 h-4" />
                Pausar
              </>
            )}
          </button>

          {/* Refresh */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="h-10 px-4 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Atualizando...' : 'Atualizar'}
          </button>
        </div>
      </Card>

      {/* Logs List */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">
            Logs Recentes ({filteredLogs?.length || 0})
          </h3>
          <span className="text-xs text-text-tertiary">
            Os logs mais recentes aparecem no topo
          </span>
        </div>

        {filteredLogs && filteredLogs.length > 0 ? (
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
            {filteredLogs.map((log, index) => {
              const isRecent = log.created_at && (new Date() - new Date(log.created_at)) < 10000; // últimos 10s
              const isCritical = log.level?.toLowerCase() === 'error' || log.level?.toLowerCase() === 'critical';

              return (
                <div
                  key={log.id || index}
                  className={`flex items-start gap-3 p-4 rounded-lg transition-all duration-300 ${
                    isCritical
                      ? 'bg-red-500/10 border border-red-500/30 hover:bg-red-500/15'
                      : 'bg-background hover:bg-background-elevated'
                  } ${isRecent ? 'animate-fade-in' : ''}`}
                >
                  {/* Icon */}
                  <div className="flex-shrink-0 mt-1">
                    {getLevelIcon(log.level)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <p className={`text-sm font-medium break-words ${
                        isCritical ? 'text-red-400' : 'text-text-primary'
                      }`}>
                        {log.message}
                      </p>
                      <Badge variant={getLevelBadgeVariant(log.level)} className="flex-shrink-0">
                        {log.level || 'DEBUG'}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs">
                      {/* Timestamp relativo */}
                      <span className="flex items-center gap-1.5 text-text-tertiary font-medium">
                        <Clock className="w-3 h-3" />
                        {getRelativeTime(log.created_at)}
                      </span>

                      {/* Conta */}
                      {log.account_name && (
                        <span className="flex items-center gap-1.5 text-accent">
                          <span className="w-1 h-1 rounded-full bg-accent"></span>
                          @{log.account_name}
                        </span>
                      )}

                      {/* Módulo */}
                      {log.module && (
                        <span className="flex items-center gap-1.5 text-text-secondary bg-background-elevated px-2 py-0.5 rounded">
                          <span className="w-1 h-1 rounded-full bg-text-secondary"></span>
                          {log.module}
                        </span>
                      )}

                      {/* Timestamp exato (tooltip) */}
                      <span className="text-text-tertiary/60 ml-auto" title="Data e hora exata">
                        {log.created_at
                          ? new Date(log.created_at).toLocaleString('pt-BR', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit'
                            })
                          : '---'
                        }
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12 text-text-tertiary">
            <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p>Nenhum log encontrado</p>
          </div>
        )}
      </Card>
    </div>
  );
}
