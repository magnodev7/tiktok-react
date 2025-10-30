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
  const [gitLog, setGitLog] = useState([]);
  const [updateLog, setUpdateLog] = useState([]);
  const [logs, setLogs] = useState('');
  const [selectedLogService, setSelectedLogService] = useState('backend');

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

  // Carregar status do git ao mudar para aba git
  useEffect(() => {
    if (activeTab === 'git') {
      loadGitStatus();
      loadGitLog();
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
      if (response.data?.success) {
        setServiceStatus(response.data.data);
      }
    } catch (error) {
      console.error('Erro ao carregar status dos serviços:', error);
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
    if (!confirm(
      force
        ? 'Tem certeza? Mudanças locais serão descartadas!'
        : 'Atualizar o sistema do GitHub?'
    )) {
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
      const message = error.response?.data?.message || error.message;
      alert(`❌ Erro na atualização: ${message}`);
      setUpdateLog([{ step: 'error', success: false, error: message }]);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString('pt-BR');
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
            <div className="flex flex-wrap gap-3 mb-6">
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
            </div>

            {serviceStatus && (
              <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Status dos Serviços:
                </h3>
                <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
                  {serviceStatus.status || 'Carregando...'}
                </pre>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Git Status Tab */}
      {activeTab === 'git' && (
        <div className="space-y-6">
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
