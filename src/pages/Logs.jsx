import { FileText, Search, RefreshCw, Info, AlertTriangle, XCircle, Pause, Play, Clock, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';
import { useLogs } from '@/hooks/useLogs';
import { useAccounts } from '@/hooks/useAccounts';
import Spinner from '@/components/common/Spinner';
import apiClient from '@/api/client';

const ALL_TAB_KEY = '__all__';
const NO_ACCOUNT_KEY = '__unassigned__';
const NO_ACCOUNT_LABEL = 'Sistema';

export default function Logs() {
  const [limit, setLimit] = useState(50);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [levelFilter, setLevelFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [accountCounts, setAccountCounts] = useState({});

  const queryClient = useQueryClient();
  const { data: logs, isLoading, refetch, dataUpdatedAt } = useLogs(limit, selectedAccount, !isPaused);
  const { data: accounts } = useAccounts();

  const clearLogsMutation = useMutation({
    mutationFn: async ({ account }) => {
      const params = new URLSearchParams();
      if (account) {
        params.append('account', account);
      }
      const url = params.toString() ? `/api/logs?${params}` : '/api/logs';
      await apiClient.delete(url);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logs'], exact: false });
    },
  });

  const filteredLogs = useMemo(() => {
    if (!logs) return [];
    return logs
      .filter((log) => {
        if (levelFilter !== 'all' && log.level?.toLowerCase() !== levelFilter) {
          return false;
        }
        if (searchTerm) {
          const searchLower = searchTerm.toLowerCase();
          return (
            log.message?.toLowerCase().includes(searchLower) ||
            log.account_name?.toLowerCase().includes(searchLower) ||
            log.module?.toLowerCase().includes(searchLower)
          );
        }
        return true;
      })
      .sort((a, b) => {
        const dateA = new Date(a.created_at || 0);
        const dateB = new Date(b.created_at || 0);
        return dateB - dateA;
      });
  }, [logs, levelFilter, searchTerm]);

  useEffect(() => {
    if (!filteredLogs.length && selectedAccount) {
      setAccountCounts((prev) => {
        if (prev[selectedAccount] === 0) {
          return prev;
        }
        return { ...prev, [selectedAccount]: 0 };
      });
      return;
    }

    if (!filteredLogs.length) {
      setAccountCounts((prev) => {
        if (prev[ALL_TAB_KEY] === 0) {
          return prev;
        }
        return { ...prev, [ALL_TAB_KEY]: 0 };
      });
      return;
    }

    setAccountCounts((prev) => {
      const next = { ...prev };
      let changed = false;

      if (!selectedAccount) {
        const counts = {};
        filteredLogs.forEach((log) => {
          if (log.account_name) {
            counts[log.account_name] = (counts[log.account_name] || 0) + 1;
          }
        });
        counts[ALL_TAB_KEY] = filteredLogs.length;
        Object.entries(counts).forEach(([key, value]) => {
          if (next[key] !== value) {
            next[key] = value;
            changed = true;
          }
        });
      } else if (next[selectedAccount] !== filteredLogs.length) {
        next[selectedAccount] = filteredLogs.length;
        changed = true;
      }

      return changed ? next : prev;
    });
  }, [filteredLogs, selectedAccount]);

  const accountTabs = useMemo(() => {
    const seen = new Set();
    const names = [];

    if (accounts?.length) {
      accounts
        .map((acc) => acc.account_name)
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b))
        .forEach((name) => {
          if (!seen.has(name)) {
            seen.add(name);
            names.push(name);
          }
        });
    }

    if (filteredLogs.length) {
      filteredLogs
        .map((log) => log.account_name)
        .filter(Boolean)
        .forEach((name) => {
          if (!seen.has(name)) {
            seen.add(name);
            names.push(name);
          }
        });
    }

    if (selectedAccount && !seen.has(selectedAccount)) {
      seen.add(selectedAccount);
      names.push(selectedAccount);
    }

    return [
      {
        value: null,
        label: 'Todas',
        count: accountCounts[ALL_TAB_KEY] ?? filteredLogs.length ?? 0,
      },
      ...names.map((name) => ({
        value: name,
        label: name,
        count: accountCounts[name],
      })),
    ];
  }, [accounts, filteredLogs, selectedAccount, accountCounts]);

  const groupedLogs = useMemo(() => {
    if (!filteredLogs.length) return {};
    const grouped = {};
    filteredLogs.forEach((log) => {
      const key = log.account_name || NO_ACCOUNT_KEY;
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(log);
    });
    return grouped;
  }, [filteredLogs]);

  const accountOrder = useMemo(() => {
    const base = accounts?.map((acc) => acc.account_name).filter(Boolean) ?? [];
    const extras = Object.keys(groupedLogs).filter((name) => {
      if (!name) {
        return false;
      }
      if (name === NO_ACCOUNT_KEY) {
        return false;
      }
      return !base.includes(name);
    }).sort((a, b) => a.localeCompare(b));

    const order = [...base, ...extras];
    if (groupedLogs[NO_ACCOUNT_KEY]) {
      order.push(NO_ACCOUNT_KEY);
    }
    return order;
  }, [accounts, groupedLogs]);

  const groupedEntries = useMemo(() => {
    const entries = Object.entries(groupedLogs);
    if (!entries.length) {
      return [];
    }
    const orderMap = new Map(accountOrder.map((name, idx) => [name, idx]));
    const defaultIndex = accountOrder.length;
    return entries.sort(([nameA], [nameB]) => {
      const idxA = orderMap.has(nameA) ? orderMap.get(nameA) : defaultIndex;
      const idxB = orderMap.has(nameB) ? orderMap.get(nameB) : defaultIndex;
      if (idxA !== idxB) {
        return idxA - idxB;
      }
      return nameA.localeCompare(nameB);
    });
  }, [groupedLogs, accountOrder]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const handleClearLogs = async () => {
    const scope = selectedAccount ? `da conta ${selectedAccount}` : 'todos os logs';
    if (!window.confirm(`Tem certeza que deseja limpar ${scope}?`)) {
      return;
    }
    try {
      await clearLogsMutation.mutateAsync({ account: selectedAccount });
    } catch (error) {
      console.error('Erro ao limpar logs:', error);
      const apiMessage = error?.response?.data?.message || error?.message || 'Não foi possível limpar os logs.';
      window.alert(apiMessage);
    }
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

  const levelCounts = logs?.reduce((acc, log) => {
    const level = log.level?.toLowerCase() || 'debug';
    acc[level] = (acc[level] || 0) + 1;
    return acc;
  }, {}) || {};

  const renderLogItem = (log, index, { hideAccountTag = false } = {}) => {
    const key = log.id || `${log.account_name || 'log'}-${log.created_at || index}-${index}`;
    const isRecent = log.created_at && (new Date() - new Date(log.created_at)) < 10000;
    const isCritical = log.level?.toLowerCase() === 'error' || log.level?.toLowerCase() === 'critical';
    return (
      <div
        key={key}
        className={`flex items-start gap-3 p-4 rounded-lg transition-all duration-300 ${
          isCritical
            ? 'bg-red-500/10 border border-red-500/30 hover:bg-red-500/15'
            : 'bg-background hover:bg-background-elevated border border-border/40'
        } ${isRecent ? 'animate-fade-in' : ''}`}
      >
        <div className="flex-shrink-0 mt-1">
          {getLevelIcon(log.level)}
        </div>
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
            <span className="flex items-center gap-1.5 text-text-tertiary font-medium">
              <Clock className="w-3 h-3" />
              {getRelativeTime(log.created_at)}
            </span>
            {!hideAccountTag && log.account_name && (
              <span className="flex items-center gap-1.5 text-accent">
                <span className="w-1 h-1 rounded-full bg-accent"></span>
                @{log.account_name}
              </span>
            )}
            {log.module && (
              <span className="flex items-center gap-1.5 text-text-secondary bg-background-elevated px-2 py-0.5 rounded">
                <span className="w-1 h-1 rounded-full bg-text-secondary"></span>
                {log.module}
              </span>
            )}
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
  };

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

      {/* Account Tabs */}
      <Card>
        <div className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm text-text-secondary">Visualizar por conta</p>
              <p className="text-lg font-semibold text-text-primary">Navegue pelas contas em abas</p>
            </div>
            <span className="text-xs text-text-tertiary">
              {selectedAccount ? `Mostrando @${selectedAccount}` : 'Exibindo todas as contas'}
            </span>
          </div>
          <div className="-mx-2 overflow-x-auto px-2">
            <div className="flex gap-2 min-w-full">
              {accountTabs.map((tab) => {
                const isActive = tab.value === selectedAccount;
                const countLabel = typeof tab.count === 'number' ? tab.count : '—';
                return (
                  <button
                    type="button"
                    key={tab.label}
                    onClick={() => setSelectedAccount(tab.value)}
                    aria-pressed={isActive}
                    className={`
                      flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all
                      whitespace-nowrap
                      ${isActive
                        ? 'bg-accent/15 text-text-primary border-accent/40 font-semibold'
                        : 'bg-background-subtle text-text-primary border-border hover:border-accent/60 hover:text-accent'}
                    `}
                  >
                    <span className="truncate">{tab.label}</span>
                    <Badge variant={isActive ? 'info' : 'neutral'} dot>
                      {countLabel}
                    </Badge>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Card>

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

          {/* Clear logs */}
          <button
            onClick={handleClearLogs}
            disabled={clearLogsMutation.isLoading}
            className="h-10 px-4 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className={`w-4 h-4 ${clearLogsMutation.isLoading ? 'animate-spin' : ''}`} />
            {clearLogsMutation.isLoading ? 'Limpando...' : 'Limpar logs'}
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
          selectedAccount ? (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
              {filteredLogs.map((log, index) => renderLogItem(log, index))}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {groupedEntries.map(([accountName, accountLogs]) => (
                <div
                  key={accountName}
                  className="bg-background-subtle border border-border rounded-xl p-4 flex flex-col max-h-[600px]"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="text-xs text-text-tertiary uppercase tracking-wide">Conta</p>
                      <p className="text-lg font-semibold text-text-primary">
                        {accountName === NO_ACCOUNT_KEY ? NO_ACCOUNT_LABEL : `@${accountName}`}
                      </p>
                    </div>
                    <Badge variant="info" dot>{accountLogs.length}</Badge>
                  </div>
                  <div className="space-y-2 overflow-y-auto pr-1">
                    {accountLogs.slice(0, 10).map((log, index) =>
                      renderLogItem(log, index, { hideAccountTag: true })
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
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
