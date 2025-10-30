import React, { useState, useEffect } from 'react';
import {
  Server,
  GitBranch,
  RefreshCw,
  Play,
  Square,
  RotateCw,
  Activity,
  Terminal,
  Download,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
} from 'lucide-react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import { useAuth } from '@/contexts/AuthContext';
import api from '@/api/client';

export default function Maintenance() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('services');
  const [loading, setLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [gitStatus, setGitStatus] = useState(null);
  const [gitConfig, setGitConfig] = useState(null);
  const [gitLog, setGitLog] = useState([]);
  const [updateLog, setUpdateLog] = useState([]);
  const [logs, setLogs] = useState('');
  const [selectedLogService, setSelectedLogService] = useState('backend');
  const [editingGitUrl, setEditingGitUrl] = useState(false);
  const [newGitUrl, setNewGitUrl] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Verificar se é admin
  useEffect(() => {
    if (user && !user.is_admin) {
      alert('Acesso negado. Esta página é restrita a administradores.');
      window.location.href = '/';
    }
  }, [user]);

  // Carregar status dos serviços ao montar
  useEffect(() => {
    if (activeTab === 'services') {
      loadServiceStatus();
    }
  }, [activeTab]);

  // Auto-refresh do status dos serviços
  useEffect(() => {
    if (activeTab === 'services' && autoRefresh) {
      const interval = setInterval(() => {
        loadServiceStatus();
      }, 3000); // Atualiza a cada 3 segundos

      return () => clearInterval(interval);
    }
  }, [activeTab, autoRefresh]);

  // Carregar status do git ao mudar para aba git
  useEffect(() => {
    if (activeTab === 'git') {
      loadGitStatus();
      loadGitLog();
      loadGitConfig();
    }
  }, [activeTab]);

  // Carregar logs ao mudar de serviço
  useEffect(() => {
    if (activeTab === 'logs') {
      loadLogs();
    }
  }, [activeTab, selectedLogService]);

  const loadServiceStatus = async () => {
    try {
      const response = await api.get('/api/maintenance/service/status');
      console.log('[Maintenance] Service status response:', response.data);
      if (response.data?.success) {
        setServiceStatus(response.data.data);
      } else {
        console.error('[Maintenance] Service status failed:', response.data);
      }
    } catch (error) {
      console.error('Erro ao carregar status dos serviços:', error);
      setServiceStatus({ services: {}, error: error.message });
    }
  };

  const loadGitStatus = async () => {
    try {
      const response = await api.get('/api/maintenance/git/status');
      if (response.data?.success) {
        setGitStatus(response.data.data);
      }
    } catch (error) {
      console.error('Erro ao carregar status do git:', error);
    }
  };

  const loadGitLog = async () => {
    try {
      const response = await api.get('/api/maintenance/git/log?limit=10');
      if (response.data?.success) {
        setGitLog(response.data.data.commits || []);
      }
    } catch (error) {
      console.error('Erro ao carregar log do git:', error);
    }
  };

  const loadGitConfig = async () => {
    try {
      const response = await api.get('/api/maintenance/git/config');
      if (response.data?.success) {
        setGitConfig(response.data.data);
        setNewGitUrl(response.data.data.remotes?.origin || '');
      }
    } catch (error) {
      console.error('Erro ao carregar configuração do git:', error);
    }
  };

  const saveGitConfig = async () => {
    if (!newGitUrl.trim()) {
      alert('❌ URL do repositório não pode estar vazia');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/api/maintenance/git/config', {
        remote_url: newGitUrl,
        remote_name: 'origin',
      });

      console.log('[Maintenance] Git config save response:', response.data);

      if (response.data?.success) {
        alert('✅ ' + response.data.message);
        setEditingGitUrl(false);
        // Recarregar configuração e status
        await loadGitConfig();
        await loadGitStatus();
      }
    } catch (error) {
      console.error('[Maintenance] Git config error:', error);
      const message = error.response?.data?.message || error.message;
      alert(`❌ Erro ao salvar configuração: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      const response = await api.get(`/api/maintenance/logs/tail?service=${selectedLogService}&lines=100`);
      if (response.data?.success) {
        setLogs(response.data.data.logs || '');
      }
    } catch (error) {
      console.error('Erro ao carregar logs:', error);
      setLogs('Erro ao carregar logs');
    }
  };

  const handleServiceAction = async (action) => {
    if (!confirm(`Tem certeza que deseja executar: ${action}?`)) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.post(`/api/maintenance/service/${action}`);
      if (response.data?.success) {
        alert(`✅ ${response.data.message}`);
        await loadServiceStatus();
      }
    } catch (error) {
      const message = error.response?.data?.message || error.message;
      alert(`❌ Erro: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (force = false) => {
    const confirmMessage = force
      ? '⚠️ ATENÇÃO: Mudanças locais serão DESCARTADAS!\n\nDeseja continuar?'
      : '🔄 Atualizar o sistema do GitHub?\n\nIsso vai:\n- Fazer git pull\n- Detectar mudanças\n- Buildar frontend (se necessário)\n- Reiniciar backend (se necessário)';

    if (!confirm(confirmMessage)) {
      return;
    }

    setLoading(true);
    setUpdateLog([]);
    setActiveTab('update');

    try {
      const response = await api.post('/api/maintenance/update', { force });
      if (response.data?.success) {
        const data = response.data.data;
        setUpdateLog(data.steps || []);

        if (data.completed) {
          alert('✅ Sistema atualizado com sucesso!');
        } else {
          alert(`⚠️ Atualização completada com erros:\n${data.errors.join('\n')}`);
        }
      }
    } catch (error) {
      console.error('[Maintenance] Update error:', error);
      const apiError = error.response?.data;
      const message = apiError?.message || error.message;

      // Se for erro de mudanças locais, mostrar opção de forçar
      if (message.includes('alterações locais') || message.includes('uncommitted changes')) {
        const forceUpdate = confirm(
          `❌ ${message}\n\n` +
          '💡 Deseja FORÇAR a atualização?\n' +
          '(Isso vai descartar as mudanças locais)'
        );

        if (forceUpdate) {
          // Chamar novamente com force=true
          handleUpdate(true);
          return;
        }
      }

      alert(`❌ Erro na atualização: ${message}`);
      setUpdateLog([{ step: 'error', success: false, error: message }]);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString('pt-BR');
  };

  const getStatusBadge = (service) => {
    const statusConfig = {
      running: {
        color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        icon: '●',
        label: 'Executando',
      },
      stopped: {
        color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
        icon: '■',
        label: 'Parado',
      },
      starting: {
        color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        icon: '◐',
        label: 'Iniciando',
      },
      stopping: {
        color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
        icon: '◑',
        label: 'Parando',
      },
      failed: {
        color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        icon: '✕',
        label: 'Falhou',
      },
      unknown: {
        color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
        icon: '?',
        label: 'Desconhecido',
      },
    };

    const config = statusConfig[service.status] || statusConfig.unknown;

    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${config.color}`}>
        <span className="text-lg leading-none">{config.icon}</span>
        {config.label}
      </span>
    );
  };

  const tabs = [
    { id: 'services', label: 'Serviços', icon: Server },
    { id: 'git', label: 'Git Status', icon: GitBranch },
    { id: 'update', label: 'Atualizar Sistema', icon: Download },
    { id: 'logs', label: 'Logs', icon: FileText },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Manutenção do Sistema
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Gerencie serviços, atualize o sistema e visualize logs
        </p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 mb-6 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <Icon className="w-5 h-5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Services Tab */}
      {activeTab === 'services' && (
        <div className="space-y-6">
          <Card title="Controle de Serviços">
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <Button
                onClick={() => handleServiceAction('start')}
                disabled={loading}
                className="bg-green-600 hover:bg-green-700"
              >
                <Play className="w-4 h-4 mr-2" />
                Iniciar
              </Button>
              <Button
                onClick={() => handleServiceAction('stop')}
                disabled={loading}
                className="bg-red-600 hover:bg-red-700"
              >
                <Square className="w-4 h-4 mr-2" />
                Parar
              </Button>
              <Button
                onClick={() => handleServiceAction('restart')}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <RotateCw className="w-4 h-4 mr-2" />
                Reiniciar
              </Button>
              <Button
                onClick={loadServiceStatus}
                disabled={loading}
                variant="outline"
              >
                <Activity className="w-4 h-4 mr-2" />
                Atualizar Status
              </Button>

              <label className="flex items-center gap-2 ml-auto text-sm text-gray-600 dark:text-gray-400">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded"
                />
                Auto-refresh (3s)
              </label>
            </div>

            {serviceStatus?.error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-800 dark:text-red-200">
                  <AlertCircle className="w-5 h-5" />
                  <p className="font-medium">Erro ao carregar serviços:</p>
                </div>
                <p className="text-sm text-red-600 dark:text-red-300 mt-1">
                  {serviceStatus.error}
                </p>
              </div>
            )}

            {serviceStatus?.services && Object.keys(serviceStatus.services).length > 0 && (
              <div className="space-y-4">
                {Object.values(serviceStatus.services).map((service) => (
                  <div
                    key={service.name}
                    className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                          {service.name}
                        </h3>
                        {getStatusBadge(service)}
                      </div>
                      {service.main_pid !== '0' && (
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          PID: {service.main_pid}
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">State:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">
                          {service.active_state}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Sub-state:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">
                          {service.sub_state}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Load:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">
                          {service.load_state}
                        </span>
                      </div>
                      {service.uptime && (
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Uptime:</span>
                          <span className="ml-2 font-medium text-gray-900 dark:text-white text-xs">
                            {service.uptime.split(' ').slice(0, 4).join(' ')}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!serviceStatus && (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Activity className="w-8 h-8 mx-auto mb-2 animate-spin" />
                <p>Carregando status dos serviços...</p>
              </div>
            )}

            {serviceStatus && !serviceStatus.error && (!serviceStatus.services || Object.keys(serviceStatus.services).length === 0) && (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <AlertCircle className="w-8 h-8 mx-auto mb-2" />
                <p>Nenhum serviço encontrado</p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Git Status Tab */}
      {activeTab === 'git' && (
        <div className="space-y-6">
          <Card title="Configuração do Repositório">
            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg mb-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                URL do Repositório Git:
              </h3>

              {!editingGitUrl ? (
                <div className="flex items-center gap-3">
                  <code className="flex-1 px-3 py-2 bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-sm font-mono text-gray-900 dark:text-gray-100">
                    {gitConfig?.remotes?.origin || 'Não configurado'}
                  </code>
                  <Button
                    onClick={() => setEditingGitUrl(true)}
                    variant="outline"
                    size="sm"
                  >
                    Editar
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <input
                    type="text"
                    value={newGitUrl}
                    onChange={(e) => setNewGitUrl(e.target.value)}
                    placeholder="https://github.com/usuario/repositorio.git"
                    className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={saveGitConfig}
                      disabled={loading}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      Salvar
                    </Button>
                    <Button
                      onClick={() => {
                        setEditingGitUrl(false);
                        setNewGitUrl(gitConfig?.remotes?.origin || '');
                      }}
                      variant="outline"
                    >
                      Cancelar
                    </Button>
                  </div>
                </div>
              )}

              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                Esta URL será usada para fazer git pull nas atualizações automáticas
              </p>
            </div>
          </Card>

          <Card title="Status do Repositório">
            <div className="flex items-center justify-between mb-4">
              <Button
                onClick={() => {
                  loadGitStatus();
                  loadGitLog();
                }}
                disabled={loading}
                variant="outline"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Atualizar
              </Button>

              {gitStatus?.has_updates && (
                <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-semibold">
                    {gitStatus.commits_behind} commit(s) disponível(is)
                  </span>
                </div>
              )}
            </div>

            {gitStatus && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Branch Atual:
                    </h3>
                    <p className="text-lg font-mono text-blue-600 dark:text-blue-400">
                      {gitStatus.branch}
                    </p>
                  </div>

                  <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Status:
                    </h3>
                    <div className="flex items-center gap-2">
                      {gitStatus.clean ? (
                        <>
                          <CheckCircle className="w-5 h-5 text-green-600" />
                          <span className="text-green-600 dark:text-green-400">
                            Limpo
                          </span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-5 h-5 text-orange-600" />
                          <span className="text-orange-600 dark:text-orange-400">
                            Com alterações
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {gitStatus.last_commit && (
                  <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Último Commit:
                    </h3>
                    <div className="space-y-1 text-sm">
                      <p className="text-gray-600 dark:text-gray-400">
                        <span className="font-mono text-blue-600 dark:text-blue-400">
                          {gitStatus.last_commit.hash}
                        </span>
                        {' - '}
                        {gitStatus.last_commit.message}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-500">
                        {gitStatus.last_commit.author} •{' '}
                        {formatTimestamp(gitStatus.last_commit.timestamp)}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card title="Histórico de Commits">
            <div className="space-y-3">
              {gitLog.map((commit, index) => (
                <div
                  key={commit.full_hash}
                  className="border-l-2 border-blue-500 pl-4 py-2"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {commit.message}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        <span className="font-mono text-blue-600 dark:text-blue-400">
                          {commit.hash}
                        </span>
                        {' • '}
                        {commit.author}
                        {' • '}
                        {formatTimestamp(commit.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Update Tab */}
      {activeTab === 'update' && (
        <div className="space-y-6">
          <Card title="Atualizar Sistema do GitHub">
            <div className="mb-6">
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Esta ferramenta atualiza o sistema automaticamente:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400 mb-6">
                <li>Faz git pull do repositório</li>
                <li>Detecta arquivos alterados (frontend/backend)</li>
                <li>Executa npm run build se o frontend mudou</li>
                <li>Reinicia serviços se o backend mudou</li>
                <li>Instala dependências se necessário</li>
              </ul>

              <div className="flex gap-3">
                <Button
                  onClick={() => handleUpdate(false)}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  {loading ? 'Atualizando...' : 'Atualizar Agora'}
                </Button>

                <Button
                  onClick={() => handleUpdate(true)}
                  disabled={loading}
                  className="bg-red-600 hover:bg-red-700"
                >
                  <AlertCircle className="w-4 h-4 mr-2" />
                  Forçar Atualização
                </Button>
              </div>
            </div>

            {updateLog.length > 0 && (
              <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <Terminal className="w-4 h-4" />
                  Log de Atualização:
                </h3>
                <div className="space-y-2">
                  {updateLog.map((step, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-2 text-sm"
                    >
                      {step.success ? (
                        <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <p className="font-medium text-gray-900 dark:text-white">
                          {step.step}
                        </p>
                        {step.message && (
                          <p className="text-gray-600 dark:text-gray-400 text-xs">
                            {step.message}
                          </p>
                        )}
                        {step.output && (
                          <pre className="text-xs text-gray-500 dark:text-gray-500 mt-1 whitespace-pre-wrap font-mono">
                            {step.output}
                          </pre>
                        )}
                        {step.error && (
                          <p className="text-red-600 dark:text-red-400 text-xs mt-1">
                            {step.error}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="space-y-6">
          <Card title="Logs do Sistema">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Selecione o serviço:
              </label>
              <div className="flex flex-wrap gap-2">
                {['backend', 'scheduler', 'backend-error', 'scheduler-error'].map((service) => (
                  <button
                    key={service}
                    onClick={() => setSelectedLogService(service)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedLogService === service
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    {service}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <Button onClick={loadLogs} disabled={loading} variant="outline">
                <RefreshCw className="w-4 h-4 mr-2" />
                Atualizar Logs
              </Button>
            </div>

            <div className="bg-gray-900 p-4 rounded-lg overflow-x-auto">
              <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">
                {logs || 'Nenhum log disponível'}
              </pre>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
