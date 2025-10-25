import { useMemo, useState } from 'react';
import { TrendingUp, Users, Heart, Video, RefreshCw, Activity, LinkIcon } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';
import Spinner from '@/components/common/Spinner';
import SimpleBarChart from '@/components/charts/SimpleBarChart';
import { useAccounts } from '@/hooks/useAccounts';
import { useSelectedAccount } from '@/contexts/SelectedAccountContext';
import { useAccountMetrics, useAccountMetricsHistory } from '@/hooks/useAccountMetrics';
import { useToast } from '@/components/common/ToastContainer';
import apiClient from '@/api/client';

const TIME_RANGES = [7, 30, 90];

const formatNumber = (value) => {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('pt-BR').format(value);
};

const formatDelta = (value) => {
  if (value === null || value === undefined) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${formatNumber(value)}`;
};

const formatDateTime = (isoString) => {
  if (!isoString) return '—';
  try {
    return new Date(isoString).toLocaleString('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  } catch (error) {
    console.error('[AccountGrowth] Erro ao formatar data:', error);
    return isoString;
  }
};

export default function AccountGrowth() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [timeRange, setTimeRange] = useState(30);

  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();

  const selectedAccount = accounts?.find((acc) => acc.id === parseInt(selectedAccountId));
  const accountName = selectedAccount?.account_name || null;

  const {
    data: latestMetrics,
    isLoading: metricsLoading,
    isFetching: metricsFetching,
  } = useAccountMetrics(accountName);

  const {
    data: history = [],
    isLoading: historyLoading,
    isFetching: historyFetching,
  } = useAccountMetricsHistory(accountName, { days: timeRange, limit: 120 });

  const previousSnapshot = history?.[1];

  const deltas = useMemo(() => {
    if (!latestMetrics || !previousSnapshot) {
      return {
        followers: null,
        likes: null,
        videos: null,
      };
    }

    return {
      followers: (latestMetrics.followers ?? 0) - (previousSnapshot.followers ?? 0),
      likes: (latestMetrics.likes ?? 0) - (previousSnapshot.likes ?? 0),
      videos: (latestMetrics.videos ?? 0) - (previousSnapshot.videos ?? 0),
    };
  }, [latestMetrics, previousSnapshot]);

  const followersSeries = useMemo(() => {
    if (!history?.length) return [];
    const reversed = [...history].reverse();
    return reversed.map((entry) => ({
      label: new Date(entry.captured_at).toLocaleDateString('pt-BR', { month: 'short', day: '2-digit' }),
      value: entry.followers ?? 0,
    }));
  }, [history]);

  const refreshMutation = useMutation({
    mutationFn: async () => {
      if (!accountName) {
        throw new Error('Selecione uma conta para atualizar as métricas.');
      }
      const { data } = await apiClient.post(`/api/analytics/accounts/${accountName}/metrics/refresh`);
      return data;
    },
    onSuccess: () => {
      toast.success('Métricas atualizadas com sucesso!');
      queryClient.invalidateQueries(['accountMetrics', accountName]);
      queryClient.invalidateQueries(['accountMetricsHistory', accountName]);
    },
    onError: (error) => {
      console.error('[AccountGrowth] Erro ao atualizar métricas:', error);
      toast.error(error?.message || 'Não foi possível atualizar as métricas agora.');
    },
  });

  const isLoadingState = accountsLoading || metricsLoading || historyLoading;
  const isFetchingState = metricsFetching || historyFetching;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary mb-2">Crescimento da Conta</h1>
          <p className="text-text-secondary">Acompanhe seguidores, engajamento e detalhes dos últimos agendamentos.</p>
        </div>
        <div className="flex flex-wrap gap-3 items-center">
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Selecione uma conta</option>
            {accounts?.map((account) => (
              <option key={account.id} value={account.id}>
                @{account.account_name}
              </option>
            ))}
          </select>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(parseInt(e.target.value))}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {TIME_RANGES.map((range) => (
              <option key={range} value={range}>
                Últimos {range} dias
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => refreshMutation.mutate()}
            disabled={!accountName || refreshMutation.isLoading}
            className="inline-flex items-center gap-2 h-10 px-4 rounded-lg bg-accent text-white hover:bg-accent/90 transition disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${refreshMutation.isLoading ? 'animate-spin' : ''}`} />
            Atualizar agora
          </button>
        </div>
      </div>

      {isLoadingState ? (
        <div className="flex items-center justify-center min-h-[40vh]">
          <Spinner size="lg" />
        </div>
      ) : !accountName ? (
        <Card className="p-6 text-center">
          <p className="text-text-secondary">Selecione uma conta TikTok para visualizar as métricas de crescimento.</p>
        </Card>
      ) : (
        <>
          <div className="flex items-center gap-3 text-sm text-text-tertiary">
            <Activity className={`w-4 h-4 ${isFetchingState ? 'animate-pulse' : ''}`} />
            <span>Última captura: {latestMetrics ? formatDateTime(latestMetrics.captured_at) : '—'}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-accent" />
                <p className="text-sm text-text-secondary">Seguidores</p>
              </div>
              <p className="text-2xl font-bold text-text-primary">{formatNumber(latestMetrics?.followers)}</p>
              <p className="text-xs text-text-tertiary">Variação: {formatDelta(deltas.followers)}</p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <Heart className="w-4 h-4 text-rose-500" />
                <p className="text-sm text-text-secondary">Curtidas</p>
              </div>
              <p className="text-2xl font-bold text-rose-500">{formatNumber(latestMetrics?.likes)}</p>
              <p className="text-xs text-text-tertiary">Variação: {formatDelta(deltas.likes)}</p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <Video className="w-4 h-4 text-blue-500" />
                <p className="text-sm text-text-secondary">Vídeos</p>
              </div>
              <p className="text-2xl font-bold text-blue-500">{formatNumber(latestMetrics?.videos)}</p>
              <p className="text-xs text-text-tertiary">Variação: {formatDelta(deltas.videos)}</p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                <p className="text-sm text-text-secondary">Conta</p>
              </div>
              <div className="space-y-1 text-sm">
                <p className="text-text-primary font-semibold">{latestMetrics?.nickname || accountName}</p>
                <div className="flex items-center gap-2">
                  <Badge variant={latestMetrics?.verified ? 'success' : 'neutral'}>
                    {latestMetrics?.verified ? 'Verificada' : 'Sem selo'}
                  </Badge>
                  {latestMetrics?.private_account && (
                    <Badge variant="warning">Conta privada</Badge>
                  )}
                </div>
                <p className="text-text-tertiary">Região: {latestMetrics?.region || 'não informada'}</p>
              </div>
            </Card>
          </div>

          {followersSeries.length > 0 && (
            <Card>
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-accent" />
                Evolução de seguidores
              </h3>
              <SimpleBarChart data={followersSeries} maxHeight={240} />
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <h3 className="text-lg font-semibold text-text-primary mb-4">Histórico recente</h3>
              {history && history.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="text-left text-text-secondary border-b border-border/60">
                        <th className="py-2 pr-4">Capturado em</th>
                        <th className="py-2 pr-4">Seguidores</th>
                        <th className="py-2 pr-4">Curtidas</th>
                        <th className="py-2">Vídeos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.slice(0, 15).map((entry) => (
                        <tr key={entry.captured_at} className="border-b border-border/40 last:border-none">
                          <td className="py-2 pr-4 text-text-primary whitespace-nowrap">{formatDateTime(entry.captured_at)}</td>
                          <td className="py-2 pr-4 text-text-secondary">{formatNumber(entry.followers)}</td>
                          <td className="py-2 pr-4 text-text-secondary">{formatNumber(entry.likes)}</td>
                          <td className="py-2 text-text-secondary">{formatNumber(entry.videos)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-text-secondary">Ainda não há histórico suficiente para exibir.</p>
              )}
            </Card>

            <Card>
              <h3 className="text-lg font-semibold text-text-primary mb-4">Bio & links sociais</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-text-tertiary uppercase text-xs mb-1">Bio</p>
                  <p className="whitespace-pre-line text-text-secondary bg-background-subtle p-3 rounded-lg border border-border/40">
                    {latestMetrics?.signature || '—'}
                  </p>
                </div>
                <div>
                  <p className="text-text-tertiary uppercase text-xs mb-1">Links detectados</p>
                  {latestMetrics?.social_links?.length ? (
                    <ul className="space-y-2">
                      {latestMetrics.social_links.map((link) => (
                        <li key={link} className="text-text-secondary flex items-center gap-2">
                          <LinkIcon className="w-4 h-4 text-accent" />
                          <span>{link}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-text-secondary">Nenhum link identificado.</p>
                  )}
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
