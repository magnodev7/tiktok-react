import { Calendar, Trash2, Edit } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import Badge from '../common/Badge';
import { formatRelativeTime, formatDate, formatTime } from '@/utils/dateFormatter';
import { useDeleteVideo } from '@/hooks/useScheduledVideos';
import { useAccounts } from '@/hooks/useAccounts';
import { useSelectedAccount } from '@/contexts/SelectedAccountContext';
import apiClient from '@/api/client';

export default function VideoList({ videos = [] }) {
  const deleteMutation = useDeleteVideo();
  const { data: accounts } = useAccounts();
  const { setSelectedAccountId } = useSelectedAccount();
  const queryClient = useQueryClient();

  const getStatusVariant = (status) => {
    const variants = {
      scheduled: 'info',
      pending: 'info',
      published: 'success',
      failed: 'error',
      processing: 'warning',
      queued: 'info',
    };
    return variants[status] || 'neutral';
  };

  const handleDelete = async (video) => {
    if (window.confirm(`Tem certeza que deseja remover "${video.video_path}"?`)) {
      try {
        await deleteMutation.mutateAsync({
          account: video.account,
          filename: video.video_path,
          mode: 'move', // move para pasta de backup
        });
      } catch (error) {
        console.error('Erro ao deletar vídeo:', error);
        alert('Erro ao deletar vídeo');
      }
    }
  };

  const handleEdit = async (video) => {
    if (!video) return;
    if (accounts && accounts.length) {
      const match = accounts.find((acc) => acc.account_name === video.account);
      if (match) {
        setSelectedAccountId(String(match.id));
      }
    }

    let defaultValue = '';
    try {
      if (video.scheduled_at) {
        const dt = new Date(video.scheduled_at);
        if (!isNaN(dt.getTime())) {
          defaultValue = new Date(dt.getTime() - dt.getTimezoneOffset() * 60000)
            .toISOString()
            .slice(0, 16);
        }
      }
    } catch (error) {
      console.warn('Erro ao preparar horário padrão', error);
    }

    const input = window.prompt('Novo horário (formato yyyy-mm-ddThh:mm)', defaultValue);
    if (!input) {
      return;
    }

    try {
      await apiClient.post(`/api/videos/${video.account}/${video.video_path}/reschedule`, {
        new_datetime: input,
      });
      queryClient.invalidateQueries({ queryKey: ['videos', 'scheduled'] });
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      alert('Horário atualizado com sucesso. O scheduler vai postar no novo horário.');
    } catch (error) {
      console.error('Erro ao reagendar vídeo:', error);
      const message = error.response?.data?.message || error.response?.data?.detail || error.message;
      alert(`Falha ao reagendar: ${message}`);
    }
  };

  if (videos.length === 0) {
    return (
      <div className="text-center py-12">
        <Calendar className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
        <h3 className="text-lg font-medium text-text-primary mb-2">
          Nenhum vídeo agendado
        </h3>
        <p className="text-text-secondary">
          Faça upload do seu primeiro vídeo para começar
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {videos.map((video, index) => {
        // ✅ Converter when/scheduled_at para Date e montar strings
        let scheduleDate = null;
        let scheduleRelative = 'Data inválida';
        let scheduleDateText = '';
        let scheduleTimeText = '';
        const scheduleTimezone = video.timezone || '';

        try {
          const reference = video.scheduled_at || video.when;
          if (reference) {
            scheduleDate = new Date(reference);
            if (!isNaN(scheduleDate.getTime())) {
              scheduleRelative = formatRelativeTime(scheduleDate);
              scheduleDateText = formatDate(scheduleDate);
            }
          }

          if (video.schedule_time) {
            scheduleTimeText = video.schedule_time;
          } else if (scheduleDate && !isNaN(scheduleDate.getTime())) {
            scheduleTimeText = formatTime(scheduleDate);
          }
        } catch (e) {
          console.error('Erro ao parsear data:', e);
        }

        return (
          <div
            key={video.video_path || index}
            className="bg-background border border-border rounded-lg p-4 hover:border-accent transition-colors"
          >
            <div className="flex items-start gap-4">
              {/* Thumbnail */}
              <div className="w-20 h-20 rounded-lg bg-background-subtle flex-shrink-0 overflow-hidden">
                {video.thumbnail ? (
                  <img
                    src={video.thumbnail}
                    alt={video.video_path}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Calendar className="w-8 h-8 text-text-tertiary" />
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-text-primary mb-1 truncate">
                  {video.video_path || 'Sem nome'}
                </h4>
                <p className="text-sm text-text-secondary mb-2 line-clamp-2">
                  {video.description || 'Sem descrição'}
                </p>
                <div className="flex flex-wrap items-center gap-3 text-sm text-text-tertiary">
                  <span>@{video.account || 'Conta desconhecida'}</span>
                  {video.hashtags && (
                    <>
                      <span className="text-text-tertiary">•</span>
                      <span className="text-accent">{video.hashtags}</span>
                    </>
                  )}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="px-2 py-0.5 rounded-full bg-accent/10 text-accent text-xs font-semibold uppercase tracking-wide">
                    Agendado
                  </span>
                  <span className="text-sm font-semibold text-text-primary">
                    {scheduleDateText || 'Data indefinida'}
                    {scheduleTimeText ? ` às ${scheduleTimeText}` : ''}
                  </span>
                  {scheduleTimezone && (
                    <span className="text-xs text-text-tertiary">
                      ({scheduleTimezone})
                    </span>
                  )}
                  <span className="text-xs text-text-secondary">
                    • {scheduleRelative}
                  </span>
                </div>
              </div>

              {/* Status & Actions */}
              <div className="flex flex-col items-end gap-2">
                <Badge variant={getStatusVariant(video.status)} dot>
                  {video.status || 'pending'}
                </Badge>
                <div className="flex gap-2">
                  <button 
                    onClick={() => handleEdit(video)}
                    className="p-1.5 hover:bg-accent/10 rounded transition-colors"
                    title="Editar horário"
                  >
                    <Edit className="w-4 h-4 text-accent" />
                  </button>
                  <button
                    onClick={() => handleDelete(video)}
                    className="p-1.5 hover:bg-red-500/10 rounded transition-colors"
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
