import { Video, Clock, Users, Calendar, TrendingUp, AlertCircle } from 'lucide-react';
import { useState } from 'react';
import StatCard from '@/components/dashboard/StatCard';
import UploadSection from '@/components/dashboard/UploadSection';
import RecentVideosSection from '@/components/dashboard/RecentVideosSection';
import VideoList from '@/components/dashboard/VideoList';
import CapacityWidget from '@/components/dashboard/CapacityWidget';
import { useScheduledVideos } from '@/hooks/useScheduledVideos';
import { useAccounts } from '@/hooks/useAccounts';
import { useSelectedAccount } from '@/contexts/SelectedAccountContext';
import { useAnalytics } from '@/hooks/useAnalytics';
import Spinner from '@/components/common/Spinner';
import SimpleBarChart from '@/components/charts/SimpleBarChart';
import Card from '@/components/common/Card';

export default function Dashboard() {
  const [showAllVideos, setShowAllVideos] = useState(false);
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();

  // Se não tem conta selecionada, pega a primeira ativa ou primeira disponível
  const activeAccount = selectedAccountId
    ? accounts?.find(a => a.id === parseInt(selectedAccountId))
    : accounts?.find(a => a.is_active) || accounts?.[0];

  const accountName = activeAccount?.account_name;
  const accountId = activeAccount?.id;

  const { data: videos, isLoading: videosLoading } = useScheduledVideos(accountName);
  const { data: analytics } = useAnalytics(accountName, 7);

  if (accountsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  // Se não houver contas, exibe mensagem
  if (!accounts || accounts.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Nenhuma conta conectada</h2>
          <p className="text-text-secondary mb-4">
            Adicione uma conta TikTok para visualizar vídeos agendados.
          </p>
        </div>
      </div>
    );
  }

  if (videosLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  const stats = {
    totalVideos: videos?.length || 0,
    activeAccounts: accounts?.filter(a => a.is_active).length || 0,
    nextSlot: videos?.[0]?.when || 'Nenhum agendado',
    totalPosted: analytics?.overview?.posted || 0,
  };

  // Preparar dados para gráfico de atividade semanal
  const weeklyActivity = analytics?.daily_stats
    ? Object.entries(analytics.daily_stats).slice(0, 7).map(([date, count]) => ({
        label: new Date(date).toLocaleDateString('pt-BR', { weekday: 'short' }),
        value: count
      }))
    : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary mb-2">Dashboard</h1>
          <p className="text-text-secondary">
            Visão geral dos seus agendamentos e analytics
          </p>
        </div>
        {accounts && accounts.length > 1 && (
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {accounts?.map((account) => (
              <option key={account.id} value={account.id}>
                @{account.account_name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Video}
          label="Vídeos Agendados"
          value={stats.totalVideos}
        />
        <StatCard
          icon={TrendingUp}
          label="Vídeos Postados (7d)"
          value={stats.totalPosted}
        />
        <StatCard
          icon={Calendar}
          label="Contas Ativas"
          value={stats.activeAccounts}
        />
        <StatCard
          icon={Clock}
          label="Próximo Agendamento"
          value={videos?.[0] ? new Date(videos[0].when).toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
          }) : 'Nenhum'}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <UploadSection />
          <RecentVideosSection accountName={accountName} />
        </div>
        <div>
          <CapacityWidget accountId={accountId} accountName={accountName} />
        </div>
      </div>

      {/* Activity Chart */}
      {weeklyActivity.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-accent" />
            Atividade dos Últimos 7 Dias
          </h3>
          <SimpleBarChart data={weeklyActivity} maxHeight={160} />
        </Card>
      )}

      {/* Videos List */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Vídeos Agendados {activeAccount && `(@${activeAccount.account_name})`}
          </h2>
          {videos && videos.length > 5 && (
            <button
              onClick={() => setShowAllVideos(!showAllVideos)}
              className="text-sm text-accent hover:underline"
            >
              {showAllVideos ? 'Ver menos' : `Ver todos (${videos.length})`}
            </button>
          )}
        </div>
        <VideoList videos={showAllVideos ? videos : videos?.slice(0, 5)} />
      </Card>
    </div>
  );
}
