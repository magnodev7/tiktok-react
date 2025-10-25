import { BarChart3, TrendingUp, Calendar, AlertCircle, Zap, DollarSign } from 'lucide-react';
import { useState } from 'react';
import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';
import { useAccounts } from '@/hooks/useAccounts';
import { useSelectedAccount } from '@/contexts/SelectedAccountContext';
import { useAnalytics } from '@/hooks/useAnalytics';
import Spinner from '@/components/common/Spinner';
import DonutChart from '@/components/charts/DonutChart';
import SimpleBarChart from '@/components/charts/SimpleBarChart';
import ProgressBar from '@/components/common/ProgressBar';

export default function Analytics() {
  const [dateRange, setDateRange] = useState('30');
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();

  // Para a chamada correta do hook, precisamos do nome da conta (account_name)
  const selectedAccount = accounts?.find(acc => acc.id === parseInt(selectedAccountId));
  const accountName = selectedAccount?.account_name || null;

  const { data: analytics, isLoading: analyticsLoading } = useAnalytics(accountName, parseInt(dateRange));

  if (accountsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  const overview = analytics?.overview || {};
  const alerts = analytics?.alerts || [];
  const aiModels = analytics?.ai_models || {};
  const workflows = analytics?.workflows || {};
  const sources = analytics?.sources || {};

  // Preparar dados para gráfico de pizza (Status dos vídeos)
  const statusData = [
    { label: 'Postados', value: overview.posted || 0 },
    { label: 'Pendentes', value: overview.pending || 0 },
    { label: 'Falhados', value: overview.failed || 0 },
  ].filter(item => item.value > 0);

  // Preparar dados para gráfico de barras (Fontes)
  const sourcesChartData = Object.entries(sources).map(([source, stats]) => ({
    label: source.charAt(0).toUpperCase() + source.slice(1),
    value: stats.total_videos || 0
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary mb-2">Analytics</h1>
          <p className="text-text-secondary">Métricas e insights dos seus vídeos e agendamentos</p>
        </div>
        <div className="flex gap-3">
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Todas as contas</option>
            {accounts?.map((account) => (
              <option key={account.id} value={account.id}>
                @{account.account_name}
              </option>
            ))}
          </select>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="7">7 dias</option>
            <option value="30">30 dias</option>
            <option value="90">90 dias</option>
          </select>
        </div>
      </div>

      {analyticsLoading ? (
        <div className="flex items-center justify-center min-h-[40vh]">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-accent" />
                <p className="text-sm text-text-secondary">Total de Vídeos</p>
              </div>
              <p className="text-2xl font-bold text-text-primary">
                {overview.total_videos || 0}
              </p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                <p className="text-sm text-text-secondary">Postados</p>
              </div>
              <p className="text-2xl font-bold text-green-500">
                {overview.posted || 0}
              </p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="w-4 h-4 text-yellow-500" />
                <p className="text-sm text-text-secondary">Pendentes</p>
              </div>
              <p className="text-2xl font-bold text-yellow-500">
                {overview.pending || 0}
              </p>
              <p className="text-xs text-text-secondary">
                Em fila: {overview.pending_in_queue || 0}
              </p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-4 h-4 text-blue-500" />
                <p className="text-sm text-text-secondary">Taxa de Sucesso</p>
              </div>
              <p className="text-2xl font-bold text-blue-500">
                {overview.success_rate || 0}%
              </p>
            </Card>
          </div>

          {/* Gráficos de Visualização */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Gráfico de Status */}
            {statusData.length > 0 && (
              <Card>
                <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-accent" />
                  Distribuição por Status
                </h3>
                <DonutChart data={statusData} size={200} showLegend />
              </Card>
            )}

            {/* Gráfico de Fontes */}
            {sourcesChartData.length > 0 && (
              <Card>
                <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-accent" />
                  Vídeos por Origem
                </h3>
                <SimpleBarChart data={sourcesChartData} maxHeight={200} />
              </Card>
            )}
          </div>

          {/* Performance por Fonte (Detalhado) */}
          {Object.keys(sources).length > 0 && (
            <Card>
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                📊 Performance Detalhada por Origem
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(sources).map(([source, stats]) => (
                  <div key={source} className="p-4 bg-background/50 rounded-lg border border-border">
                    <p className="text-sm font-medium text-text-secondary capitalize mb-2">{source}</p>
                    <p className="text-xl font-bold text-text-primary mb-1">{stats.total_videos} vídeos</p>
                    <ProgressBar
                      value={stats.success_rate || 0}
                      max={100}
                      variant={stats.success_rate >= 80 ? 'success' : stats.success_rate >= 50 ? 'warning' : 'error'}
                      showLabel
                      className="mt-2"
                    />
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Modelos de IA */}
          {Object.keys(aiModels).length > 0 && (
            <Card>
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                🤖 Performance por Modelo de IA
              </h3>
              <div className="space-y-3">
                {Object.entries(aiModels).map(([model, stats]) => (
                  <div key={model} className="p-4 bg-background/50 rounded-lg border border-border">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-text-primary">{model}</p>
                      <Badge variant={stats.success_rate >= 80 ? 'success' : stats.success_rate >= 50 ? 'warning' : 'error'}>
                        {stats.success_rate}% sucesso
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-xs">
                      <div>
                        <p className="text-text-tertiary">Total</p>
                        <p className="text-text-primary font-medium">{stats.total_videos}</p>
                      </div>
                      <div>
                        <p className="text-text-tertiary">Postados</p>
                        <p className="text-green-500 font-medium">{stats.posted}</p>
                      </div>
                      <div>
                        <p className="text-text-tertiary">Custo estimado</p>
                        <p className="text-text-primary font-medium">${stats.estimated_cost}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Workflows N8N */}
          {Object.keys(workflows).length > 0 && (
            <Card>
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                ⚡ Workflows N8N
              </h3>
              <div className="space-y-3">
                {Object.entries(workflows).map(([workflowId, stats]) => (
                  <div key={workflowId} className="p-4 bg-background/50 rounded-lg border border-border">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-text-primary">{workflowId}</p>
                      <Badge variant={stats.success_rate >= 80 ? 'success' : 'warning'}>
                        {stats.success_rate}%
                      </Badge>
                    </div>
                    <div className="flex gap-4 text-xs text-text-tertiary">
                      <span>Vídeos: {stats.total_videos}</span>
                      <span>Postados: {stats.posted}</span>
                      {stats.ai_model_used && <span>IA: {stats.ai_model_used}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            🔔 Alertas e Recomendações
          </h3>
          <div className="space-y-3">
            {alerts.map((alert, index) => {
              const severityColors = {
                high: 'red',
                medium: 'yellow',
                low: 'blue',
              };
              const color = severityColors[alert.severity] || 'gray';
              const bgColor = `bg-${color}-500/10`;
              const borderColor = `border-${color}-500/20`;
              const textColor = `text-${color}-500`;

              return (
                <div key={index} className={`flex items-start gap-3 p-4 ${bgColor} border ${borderColor} rounded-lg`}>
                  <AlertCircle className={`w-5 h-5 ${textColor} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className={`text-sm font-medium ${textColor} capitalize`}>{alert.type?.replace('_', ' ')}</p>
                      <Badge variant={alert.severity === 'high' ? 'error' : alert.severity === 'medium' ? 'warning' : 'info'}>
                        {alert.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-text-primary mb-1">{alert.message}</p>
                    {alert.recommendation && (
                      <p className="text-xs text-text-tertiary">💡 {alert.recommendation}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Empty State */}
      {!analyticsLoading && overview.total_videos === 0 && (
        <Card>
          <div className="text-center py-12">
            <BarChart3 className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              Nenhum dado disponível
            </h3>
            <p className="text-text-secondary mb-4">
              Ainda não há vídeos {accountName ? `para a conta @${accountName}` : 'nas suas contas'} no período selecionado.
            </p>
            <p className="text-sm text-text-tertiary">
              Comece enviando vídeos para ver suas estatísticas aqui!
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
