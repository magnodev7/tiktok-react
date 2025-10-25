import { Clock, Plus, Download, Upload, Trash2, Save, AlertCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import Button from '@/components/common/Button';
import Card from '@/components/common/Card';
import Input from '@/components/common/Input';
import { useAccounts } from '@/hooks/useAccounts';
import { useSelectedAccount } from '@/contexts/SelectedAccountContext';
import { useSchedules, useSaveSchedules } from '@/hooks/useSchedules';
import Spinner from '@/components/common/Spinner';

export default function PostingSchedules() {
  const [newTime, setNewTime] = useState('');
  const [schedules, setSchedules] = useState([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [error, setError] = useState('');
  
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();
  
  // Buscar horários salvos da conta selecionada
  const { data: savedSchedules, isLoading: schedulesLoading } = useSchedules(selectedAccountId);
  const saveSchedulesMutation = useSaveSchedules();

  // Carregar horários quando mudar de conta
  useEffect(() => {
    if (savedSchedules && Array.isArray(savedSchedules)) {
      setSchedules(savedSchedules);
      setHasChanges(false);
    } else if (selectedAccountId && !schedulesLoading) {
      // Se não tem horários salvos, usar padrão
      setSchedules(['08:00', '12:00', '16:00', '20:00']);
      setHasChanges(false);
    }
  }, [savedSchedules, selectedAccountId, schedulesLoading]);

  const addSchedule = () => {
    if (newTime && !schedules.includes(newTime)) {
      setSchedules([...schedules, newTime].sort());
      setNewTime('');
      setHasChanges(true);
    }
  };

  const removeSchedule = (time) => {
    setSchedules(schedules.filter(t => t !== time));
    setHasChanges(true);
  };

  const applyPreset = (preset) => {
    const presets = {
      '2h': Array.from({ length: 12 }, (_, i) => `${String(i * 2).padStart(2, '0')}:00`),
      '3h': Array.from({ length: 8 }, (_, i) => `${String(i * 3).padStart(2, '0')}:00`),
      '4h': Array.from({ length: 6 }, (_, i) => `${String(i * 4).padStart(2, '0')}:00`),
      'morning': ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00'],
      'night': ['18:00', '20:00', '22:00', '00:00', '02:00', '04:00'],
      'intensive': Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`),
    };
    setSchedules(presets[preset] || []);
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!selectedAccountId) {
      setError('Selecione uma conta primeiro');
      return;
    }

    setError('');

    try {
      await saveSchedulesMutation.mutateAsync({
        accountId: selectedAccountId,
        schedules: schedules,
      });
      setHasChanges(false);
    } catch (error) {
      console.error('Erro ao salvar horários:', error);
      const apiError = error.response?.data;
      const errorMsg = apiError?.message || apiError?.detail || 'Erro ao salvar horários';
      setError(errorMsg);
    }
  };

  const handleClearAll = () => {
    if (window.confirm('Tem certeza que deseja remover todos os horários?')) {
      setSchedules([]);
      setHasChanges(true);
    }
  };

  const handleExport = () => {
    if (!selectedAccount) return;
    
    const data = {
      account: selectedAccount.account_name,
      schedules: schedules,
      exported_at: new Date().toISOString(),
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `horarios-${selectedAccount.account_name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target.result);
          if (data.schedules && Array.isArray(data.schedules)) {
            setSchedules(data.schedules.sort());
            setHasChanges(true);
          } else {
            alert('Formato de arquivo inválido');
          }
        } catch (error) {
          alert('Erro ao ler arquivo');
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  if (accountsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  const selectedAccount = accounts?.find(a => a.id === parseInt(selectedAccountId));

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary mb-2">Horários de Postagem</h1>
        <p className="text-text-secondary">Configure quando seus vídeos serão publicados</p>
      </div>

      {/* Account Selector */}
      <Card>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-text-primary mb-2">
              📱 Conta TikTok
            </label>
            <select
              value={selectedAccountId || ''}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="w-full h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Selecione uma conta</option>
              {accounts?.map((account) => (
                <option key={account.id} value={account.id}>
                  @{account.account_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              icon={Download}
              onClick={handleExport}
              disabled={!selectedAccountId}
              data-testid="export-button"
            >
              Exportar
            </Button>
            <Button
              variant="secondary"
              icon={Upload}
              onClick={handleImport}
              data-testid="import-button"
            >
              Importar
            </Button>
            <Button
              variant="destructive"
              icon={Trash2}
              onClick={handleClearAll}
              disabled={!selectedAccountId}
              data-testid="clear-all-button"
            >
              Limpar Todos
            </Button>
          </div>
        </div>
      </Card>

      {selectedAccountId ? (
        <>
          {/* Erro */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Aviso de mudanças não salvas */}
          {hasChanges && (
            <div
              className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-center justify-between"
              data-testid="unsaved-banner"
            >
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-yellow-400">
                  Você tem alterações não salvas. Clique em "Salvar Horários" para aplicar as mudanças.
                </p>
              </div>
              <Button 
                icon={Save} 
                onClick={handleSave}
                loading={saveSchedulesMutation.isPending}
                data-testid="banner-save-button"
              >
                Salvar Horários
              </Button>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <p className="text-sm text-text-secondary mb-1">Total de Horários</p>
              <p className="text-2xl font-bold text-text-primary">{schedules.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-text-secondary mb-1">Horários Ativos</p>
              <p className="text-2xl font-bold text-accent">{schedules.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-text-secondary mb-1">Capacidade Diária</p>
              <p className="text-2xl font-bold text-text-primary">{schedules.length} vídeos</p>
            </Card>
            <Card>
              <p className="text-sm text-text-secondary mb-1">Intervalo Médio</p>
              <p className="text-2xl font-bold text-text-primary">
                {schedules.length > 1 ? `${Math.floor(24 / schedules.length)}h` : '-'}
              </p>
            </Card>
          </div>

          {/* Timeline Visualization */}
          <Card>
            <h3 className="text-lg font-semibold text-text-primary mb-4">Visualização Timeline (24h)</h3>
            <div className="relative h-12 bg-background rounded-lg">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full h-1 bg-border"></div>
              </div>
              {schedules.map((time) => {
                const [hours] = time.split(':');
                const position = (parseInt(hours) / 24) * 100;
                return (
                  <div
                    key={time}
                    className="absolute top-1/2 -translate-y-1/2 group"
                    style={{ left: `${position}%` }}
                  >
                    <div className="w-3 h-3 bg-accent rounded-full relative z-10"></div>
                    <div className="absolute top-full mt-2 -translate-x-1/2 left-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="bg-background-elevated border border-border rounded px-2 py-1 text-xs text-text-primary whitespace-nowrap">
                        {time}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div className="absolute -left-2 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">0h</div>
              <div className="absolute -right-2 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">24h</div>
            </div>
          </Card>

          {/* Schedules List */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">🕐 Horários Configurados</h3>
              {!hasChanges && schedules.length > 0 && (
                <span className="text-xs text-green-500 flex items-center gap-1">
                  ✓ Salvo
                </span>
              )}
            </div>
            
            {schedules.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
                {schedules.map((time, index) => (
                  <div
                    key={time}
                    data-testid="time-slot"
                    data-time={time}
                    data-index={index}
                    className="flex items-center justify-between p-3 bg-background border border-border rounded-lg hover:border-accent transition-colors group"
                  >
                    <span className="text-lg font-mono font-semibold text-text-primary">{time}</span>
                    <button
                      onClick={() => removeSchedule(time)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/10 rounded transition-all"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-text-tertiary mb-6" data-testid="time-slot-empty">
                Nenhum horário configurado. Adicione um horário ou use um preset.
              </div>
            )}

            {/* Add New Time */}
          <div className="flex gap-3" data-testid="manual-add-section">
              <Input
                type="time"
                placeholder="HH:MM"
                value={newTime}
                onChange={setNewTime}
                className="flex-1"
              />
              <Button icon={Plus} onClick={addSchedule}>
                Adicionar
              </Button>
            </div>
          </Card>

          {/* Presets */}
          <Card>
            <h3 className="text-lg font-semibold text-text-primary mb-4">Presets Rápidos</h3>
            <p className="text-sm text-text-secondary mb-4">
              Clique em um preset para aplicar rapidamente uma configuração de horários
            </p>
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={() => applyPreset('2h')} data-preset="2h">
                📅 A cada 2h (12 slots)
              </Button>
              <Button variant="secondary" onClick={() => applyPreset('3h')} data-preset="3h">
                📅 A cada 3h (8 slots)
              </Button>
              <Button variant="secondary" onClick={() => applyPreset('4h')} data-preset="4h">
                📅 A cada 4h (6 slots)
              </Button>
              <Button variant="secondary" onClick={() => applyPreset('morning')} data-preset="morning">
                🌅 Matinal (6h-18h)
              </Button>
              <Button variant="secondary" onClick={() => applyPreset('night')} data-preset="night">
                🌙 Noturno (18h-6h)
              </Button>
              <Button variant="secondary" onClick={() => applyPreset('intensive')} data-preset="intensive">
                🚀 Intensivo (24 slots)
              </Button>
            </div>
          </Card>

          {/* Botão de Salvar Fixo no Rodapé */}
          {hasChanges && (
            <div className="fixed bottom-6 right-6 z-50">
              <Button 
                icon={Save} 
                onClick={handleSave}
                loading={saveSchedulesMutation.isPending}
                size="lg"
                className="shadow-lg"
                data-testid="floating-save-button"
              >
                Salvar Horários ({schedules.length})
              </Button>
            </div>
          )}
        </>
      ) : (
        <Card className="text-center py-12">
          <Clock className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            Selecione uma conta
          </h3>
          <p className="text-text-secondary">
            Escolha uma conta TikTok acima para configurar os horários de postagem
          </p>
        </Card>
      )}
    </div>
  );
}
