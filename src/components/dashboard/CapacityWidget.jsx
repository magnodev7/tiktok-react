import { Calendar, AlertTriangle, TrendingUp, Clock } from 'lucide-react';
import Card from '../common/Card';
import ProgressBar from '../common/ProgressBar';
import Badge from '../common/Badge';
import Spinner from '../common/Spinner';
import { useAccountCapacity, useCapacityAlerts } from '@/hooks/useCapacity';

export default function CapacityWidget({ accountId, accountName }) {
  const { data: capacity, isLoading: capacityLoading } = useAccountCapacity(accountId, 30);
  const { data: alerts, isLoading: alertsLoading } = useCapacityAlerts(accountId, 7);

  if (!accountId) {
    return (
      <Card>
        <div className="text-center py-6 text-text-secondary text-sm">
          Selecione uma conta para ver a capacidade de agendamento
        </div>
      </Card>
    );
  }

  if (capacityLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-6">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (!capacity) {
    return (
      <Card>
        <div className="text-center py-6 text-text-tertiary text-sm">
          Não foi possível carregar dados de capacidade
        </div>
      </Card>
    );
  }

  const percentageFull = capacity.percentage_full || 0;
  const progressVariant =
    percentageFull >= 90 ? 'error' :
    percentageFull >= 70 ? 'warning' :
    'success';

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Calendar className="w-5 h-5 text-accent" />
          Capacidade de Agendamento
        </h3>
        {accountName && (
          <Badge variant="info">@{accountName}</Badge>
        )}
      </div>

      {/* Estatísticas principais */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-3 bg-background rounded-lg">
          <p className="text-xs text-text-secondary mb-1">Capacidade Diária</p>
          <p className="text-xl font-bold text-text-primary">{capacity.daily_capacity}</p>
          <p className="text-xs text-text-tertiary">slots por dia</p>
        </div>
        <div className="p-3 bg-background rounded-lg">
          <p className="text-xs text-text-secondary mb-1">Ocupados (30d)</p>
          <p className="text-xl font-bold text-accent">{capacity.total_occupied}</p>
          <p className="text-xs text-text-tertiary">de {capacity.total_capacity} total</p>
        </div>
      </div>

      {/* Barra de progresso */}
      <div className="mb-4">
        <ProgressBar
          value={capacity.total_occupied}
          max={capacity.total_capacity}
          variant={progressVariant}
          size="lg"
          showLabel
        />
      </div>

      {/* Dias até ficar cheio */}
      {capacity.days_until_full !== null && (
        <div className={`p-3 rounded-lg flex items-start gap-2 mb-4 ${
          capacity.days_until_full <= 3
            ? 'bg-red-500/10 border border-red-500/20'
            : 'bg-blue-500/10 border border-blue-500/20'
        }`}>
          <Clock className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
            capacity.days_until_full <= 3 ? 'text-red-500' : 'text-blue-500'
          }`} />
          <div className="flex-1">
            <p className="text-sm font-medium text-text-primary">
              {capacity.days_until_full === 0
                ? 'Hoje ainda tem slots disponíveis!'
                : `${capacity.days_until_full} dias até preencher`}
            </p>
            <p className="text-xs text-text-secondary">
              Continue fazendo upload de vídeos
            </p>
          </div>
        </div>
      )}

      {/* Alertas */}
      {!alertsLoading && alerts && alerts.length > 0 && (
        <div className="border-t border-border pt-4">
          <p className="text-sm font-medium text-text-primary mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-500" />
            Alertas Recentes
          </p>
          <div className="space-y-2">
            {alerts.slice(0, 3).map((alert, index) => (
              <div key={index} className="text-xs p-2 bg-background rounded flex items-start gap-2">
                <Badge
                  variant={alert.alert_type === 'critical' ? 'error' : alert.alert_type === 'warning' ? 'warning' : 'info'}
                  className="flex-shrink-0"
                >
                  {alert.alert_type}
                </Badge>
                <p className="text-text-secondary flex-1">{alert.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Horários configurados */}
      {capacity.time_slots && capacity.time_slots.length > 0 && (
        <div className="border-t border-border pt-4 mt-4">
          <p className="text-sm font-medium text-text-primary mb-2">
            Horários Configurados ({capacity.time_slots.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {capacity.time_slots.slice(0, 8).map((slot, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-accent-subtle text-accent text-xs rounded font-mono"
              >
                {slot}
              </span>
            ))}
            {capacity.time_slots.length > 8 && (
              <span className="px-2 py-1 bg-background text-text-tertiary text-xs rounded">
                +{capacity.time_slots.length - 8}
              </span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
