import { format, formatDistance, formatRelative } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export function formatDate(date, formatStr = 'dd/MM/yyyy') {
  return format(new Date(date), formatStr, { locale: ptBR });
}

export function formatDateTime(date) {
  return format(new Date(date), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR });
}

export function formatRelativeTime(date) {
  return formatDistance(new Date(date), new Date(), {
    addSuffix: true,
    locale: ptBR,
  });
}

export function formatRelativeDate(date) {
  return formatRelative(new Date(date), new Date(), { locale: ptBR });
}

export function formatTime(date) {
  return format(new Date(date), 'HH:mm', { locale: ptBR });
}
