import { useMemo } from 'react';
import { Heart, CalendarClock, ExternalLink, Pin, PinOff, RefreshCcw } from 'lucide-react';

import Card from '@/components/common/Card';
import Spinner from '@/components/common/Spinner';
import Badge from '@/components/common/Badge';
import { useToast } from '@/components/common/ToastContainer';
import { useRecentVideos, usePinRecentVideo, useUnpinRecentVideo } from '@/hooks/useRecentVideos';

const formatNumber = (value) => {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('pt-BR').format(value);
};

const formatDateTime = (isoString) => {
  if (!isoString) return '—';
  try {
    return new Date(isoString).toLocaleString('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  } catch (error) {
    console.error('[RecentVideosSection] Erro ao formatar data:', error);
    return isoString;
  }
};

export default function RecentVideosSection({ accountName, limit = 3 }) {
  const toast = useToast();
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useRecentVideos(accountName, limit);

  const pinMutation = usePinRecentVideo(accountName, limit);
  const unpinMutation = useUnpinRecentVideo(accountName, limit);

  const videos = data?.videos || [];
  const pinnedCount = data?.meta?.pinned_count || 0;
  const pinLimit = data?.meta?.limit || limit;
  const pinLimitReached = pinnedCount >= pinLimit;

  const isMutating = pinMutation.isPending || unpinMutation.isPending;

  const titleBadge = useMemo(() => {
    if (!pinnedCount) return null;
    return (
      <Badge variant="info">
        {pinnedCount} fixado{pinnedCount > 1 ? 's' : ''}
      </Badge>
    );
  }, [pinnedCount]);

  const handlePinToggle = (video) => {
    if (!accountName) return;

    if (video.is_pinned) {
      unpinMutation.mutate(video.id, {
        onSuccess: () => toast.success('Vídeo removido dos fixados.'),
        onError: (mutationError) => {
          console.error('[RecentVideosSection] Erro ao desfixar vídeo:', mutationError);
          toast.error(mutationError?.message || 'Não foi possível remover o vídeo dos fixados.');
        },
      });
    } else {
      pinMutation.mutate(video.id, {
        onSuccess: () => toast.success('Vídeo fixado para acompanhamento.'),
        onError: (mutationError) => {
          console.error('[RecentVideosSection] Erro ao fixar vídeo:', mutationError);
          toast.error(mutationError?.message || 'Não foi possível fixar o vídeo.');
        },
      });
    }
  };

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-text-primary flex items-center gap-3">
            Últimos vídeos postados
            {titleBadge}
          </h2>
          <p className="text-sm text-text-secondary">
            Acompanhe o desempenho dos conteúdos mais recentes e fixe aqueles que deseja monitorar.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={!accountName || isFetching}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-border text-text-secondary hover:text-text-primary hover:border-text-tertiary transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCcw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {!accountName ? (
        <div className="py-10 text-center text-text-secondary">
          Conecte ou selecione uma conta TikTok para visualizar os vídeos postados recentemente.
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-10">
          <Spinner size="md" />
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-text-secondary">
            Não foi possível carregar os vídeos recentes.
          </p>
          <p className="text-xs text-text-tertiary max-w-md">
            {error?.message || 'Tente atualizar novamente em instantes.'}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 text-sm rounded-lg bg-accent text-white hover:bg-accent/90 transition"
          >
            Tentar novamente
          </button>
        </div>
      ) : videos.length === 0 ? (
        <div className="py-10 text-center text-text-secondary">
          Nenhum vídeo público recente encontrado para esta conta.
        </div>
      ) : (
        <div className="space-y-4">
          {videos.map((video) => (
            <div
              key={video.id}
              className="flex flex-col sm:flex-row sm:items-start gap-4 p-4 rounded-xl border border-border bg-background-subtle/40"
            >
              <div className="w-full sm:w-40 h-56 rounded-lg overflow-hidden bg-background-subtle flex-shrink-0 relative">
                {video.cover_url ? (
                  <img
                    src={video.cover_url}
                    alt={video.description || 'Vídeo TikTok'}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-text-tertiary">
                    Prévia indisponível
                  </div>
                )}
                {video.is_pinned && (
                  <div className="absolute top-2 left-2">
                    <Badge variant="info" dot>
                      Fixado
                    </Badge>
                  </div>
                )}
              </div>

              <div className="flex-1 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="text-sm text-text-tertiary flex items-center gap-2">
                      <CalendarClock className="w-4 h-4 text-text-tertiary" />
                      {formatDateTime(video.create_time)}
                    </p>
                    <p className="text-sm font-medium text-text-primary mt-1 line-clamp-2 min-h-[3rem]">
                      {video.description || 'Vídeo sem descrição'}
                    </p>
                    {video.author?.avatar_thumb && (
                      <div className="flex items-center gap-2 mt-3">
                        <img
                          src={video.author.avatar_thumb}
                          alt={video.author.nickname || video.author.unique_id || 'Conta TikTok'}
                          className="w-9 h-9 rounded-full object-cover border border-border"
                          loading="lazy"
                        />
                        <div className="text-sm">
                          <p className="text-text-primary font-medium">
                            {video.author.nickname || `@${video.author.unique_id}` || 'Conta TikTok'}
                          </p>
                          {video.author.unique_id && (
                            <p className="text-xs text-text-secondary">@{video.author.unique_id}</p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  <a
                    href={video.permalink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
                  >
                    Ver no TikTok
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
                  <span className="inline-flex items-center gap-1.5">
                    <Heart className="w-4 h-4 text-rose-500" />
                    {formatNumber(video.like_count)}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    Visualizações: {formatNumber(video.play_count)}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    Comentários: {formatNumber(video.comment_count)}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    Compart.: {formatNumber(video.share_count)}
                  </span>
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => handlePinToggle(video)}
                    disabled={isMutating || (!video.is_pinned && pinLimitReached)}
                    className={`inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg border transition ${
                      video.is_pinned
                        ? 'border-rose-500 text-rose-500 hover:bg-rose-500/10'
                        : 'border-border text-text-secondary hover:text-text-primary hover:border-text-tertiary'
                    } ${(!video.is_pinned && pinLimitReached) ? 'opacity-60 cursor-not-allowed' : ''}`}
                  >
                    {video.is_pinned ? (
                      <>
                        <PinOff className="w-4 h-4" />
                        Remover fixado
                      </>
                    ) : (
                      <>
                        <Pin className="w-4 h-4" />
                        Fixar
                      </>
                    )}
                  </button>
                  {pinLimitReached && !video.is_pinned && (
                    <span className="text-xs text-text-tertiary flex items-center">
                      Limite de {pinLimit} vídeos fixados atingido.
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
