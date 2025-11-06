import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Server,
  GitBranch,
  RefreshCw,
  RotateCw,
  Activity,
  Terminal,
  Download,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Archive,
  UploadCloud,
  Trash2,
  Info,
} from 'lucide-react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import { useAuth } from '@/contexts/AuthContext';
import api from '@/api/client';
import { restoreBackup, fetchRestoreStatus, triggerUpdate, fetchUpdateStatus } from '@/services/api/maintenance';

export default function Maintenance() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('services');
  const [loading, setLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [gitStatus, setGitStatus] = useState(null);
  const [gitConfig, setGitConfig] = useState(null);
  const [gitLog, setGitLog] = useState([]);
  const [updateLog, setUpdateLog] = useState([]);
  const [branchData, setBranchData] = useState({ locals: [], remotes: [], current_branch: '' });
  const [selectedBranch, setSelectedBranch] = useState('');
  const [branchForce, setBranchForce] = useState(false);
  const [branchFetch, setBranchFetch] = useState(true);
  const [branchLog, setBranchLog] = useState([]);
  const [branchLoading, setBranchLoading] = useState(false);
  const [logs, setLogs] = useState('');
  const [selectedLogService, setSelectedLogService] = useState('backend');
  const [editingGitUrl, setEditingGitUrl] = useState(false);
  const [newGitUrl, setNewGitUrl] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [backups, setBackups] = useState([]);
  const [backupsLoading, setBackupsLoading] = useState(false);
  const [creatingBackup, setCreatingBackup] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [restoreSteps, setRestoreSteps] = useState([]);
  const [selectedBackupFile, setSelectedBackupFile] = useState(null);
  const [restoreJob, setRestoreJob] = useState(null);
  const [restoreStatus, setRestoreStatus] = useState(null);
  const [selectedUpdateRef, setSelectedUpdateRef] = useState('');
  const [selectedUpdateRemote, setSelectedUpdateRemote] = useState('');
  const [updateJob, setUpdateJob] = useState(null);
  const [updateStatus, setUpdateStatus] = useState(null);
  const fileInputRef = useRef(null);

  // Verificar se é admin
  useEffect(() => {
    if (user && !user.is_admin) {
      alert('Acesso negado. Esta página é restrita a administradores.');
      window.location.href = '/';
    }
  }, [user]);

  useEffect(() => {
    const loadInitialUpdateStatus = async () => {
      try {
        const response = await fetchUpdateStatus();
        if (response?.status) {
          setUpdateStatus(response.status);
          setUpdateLog(response.status.steps || []);
          if (!response.status.completed && response.status.state !== 'failed') {
            setUpdateJob(response.status);
          }
        }
      } catch (error) {
        console.error('Erro ao carregar status de atualização:', error);
      }
    };
    loadInitialUpdateStatus();
  }, []);
  const loadServiceStatus = useCallback(async () => {
    try {
      const response = await api.get('/api/maintenance/service/status');
      console.log('[Maintenance] Service status response:', response.data);

      // O backend pode retornar de 2 formas:
      // 1. {success: true, data: {services: {...}}}
      // 2. Diretamente: {services: {...}, timestamp: '...'}

      if (response.data?.success === true) {
        // Formato com wrapper
        setServiceStatus(response.data.data);
      } else if (response.data?.services) {
        // Formato direto (FastAPI serialização)
        setServiceStatus(response.data);
      } else {
        console.error('[Maintenance] Service status - formato inválido:', response.data);
        setServiceStatus({ services: {}, error: 'Formato de resposta inválido' });
      }
    } catch (error) {
      console.error('Erro ao carregar status dos serviços:', error);
      setServiceStatus({ services: {}, error: error.message });
    }
  }, []);

  const loadGitStatus = useCallback(async () => {
    try {
      const response = await api.get('/api/maintenance/git/status');
      console.log('[Maintenance] Git status response:', response.data);

      if (response.data?.success === true) {
        setGitStatus(response.data.data);
      } else if (response.data?.branch) {
        // Formato direto
        setGitStatus(response.data);
      }
    } catch (error) {
      console.error('Erro ao carregar status do git:', error);
    }
  }, []);

  const loadGitLog = useCallback(async () => {
    try {
      const response = await api.get('/api/maintenance/git/log?limit=10');
      console.log('[Maintenance] Git log response:', response.data);

      if (response.data?.success === true) {
        setGitLog(response.data.data?.commits || []);
      } else if (response.data?.commits) {
        // Formato direto
        setGitLog(response.data.commits);
      }
    } catch (error) {
      console.error('Erro ao carregar log do git:', error);
    }
  }, []);

  const loadGitConfig = useCallback(async () => {
    try {
      const response = await api.get('/api/maintenance/git/config');
      console.log('[Maintenance] Git config response:', response.data);

      const configData = response.data?.success === true ? response.data.data : response.data;

      if (configData) {
        setGitConfig(configData);
        setNewGitUrl(configData.remotes?.origin || '');
      }
    } catch (error) {
      console.error('Erro ao carregar configuração do git:', error);
    }
  }, []);

  const computeRemoteFromRef = useCallback(
    (ref, data = null) => {
      const source = data || branchData;
      if (!ref || !source) {
        return '';
      }
      const remotesList = source.remotes || [];
      const remoteMatch = remotesList.find((item) => item.name === ref);
      if (!remoteMatch) {
        const slashIndex = ref.indexOf('/');
        if (slashIndex > 0) {
          const remoteCandidate = ref.slice(0, slashIndex);
          const existsRemote = remotesList.some((item) => item.name.startsWith(`${remoteCandidate}/`));
          if (existsRemote) {
            return remoteCandidate;
          }
        }
        return '';
      }
      const slashIndex = ref.indexOf('/');
      return slashIndex > 0 ? ref.slice(0, slashIndex) : ref;
    },
    [branchData],
  );

  const loadBranches = useCallback(async (refresh = false) => {
    try {
      const url = refresh ? '/api/maintenance/git/branches?refresh=true' : '/api/maintenance/git/branches';
      const response = await api.get(url);
      console.log('[Maintenance] Git branches response:', response.data);

      const payload = response.data?.success === true ? response.data.data : response.data;
      if (!payload) return;

      const branchPayload = {
        locals: payload.locals || [],
        remotes: payload.remotes || [],
        current_branch: payload.current_branch || '',
      };

      setBranchData(branchPayload);

      if (!selectedBranch) {
        setSelectedBranch(branchPayload.current_branch || '');
      }

      let nextUpdateRef = selectedUpdateRef;
      if (!nextUpdateRef) {
        const current = branchPayload.current_branch || '';
        const originRef = branchPayload.remotes?.find((item) => item.name === `origin/${current}`);
        nextUpdateRef = originRef ? originRef.name : current;
        setSelectedUpdateRef(nextUpdateRef);
      }
      setSelectedUpdateRemote(computeRemoteFromRef(nextUpdateRef, branchPayload));
    } catch (error) {
      console.error('Erro ao carregar branches do git:', error);
      alert('❌ Erro ao carregar branches do repositório');
    }
  }, [selectedBranch, selectedUpdateRef, computeRemoteFromRef]);

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

  const loadLogs = useCallback(async () => {
    try {
      const response = await api.get(`/api/maintenance/logs/tail?service=${selectedLogService}&lines=100`);
      console.log('[Maintenance] Logs response:', response.data);

      const logsData = response.data?.success === true ? response.data.data : response.data;
      setLogs(logsData?.logs || '');
    } catch (error) {
      console.error('Erro ao carregar logs:', error);
      setLogs('Erro ao carregar logs');
    }
  }, [selectedLogService]);

  const loadBackups = useCallback(async () => {
    setBackupsLoading(true);
    try {
      const response = await api.get('/api/maintenance/backup/list');
      console.log('[Maintenance] Backup list response:', response.data);
      const payload = response.data?.success === true ? response.data.data : response.data;
      setBackups(payload?.backups || []);
    } catch (error) {
      console.error('Erro ao carregar backups:', error);
      alert('❌ Erro ao carregar lista de backups');
    } finally {
      setBackupsLoading(false);
    }
  }, []);

  const pollRestoreStatus = useCallback(
    async (jobId) => {
      try {
        const response = await fetchRestoreStatus(jobId);
        const statusData = response.status;
        setRestoreStatus(statusData);
        if (statusData?.steps) {
          setRestoreSteps(statusData.steps);
        }
        if (statusData?.completed || statusData?.state === 'failed') {
          setRestoreJob(null);
          if (Array.isArray(statusData?.errors) && statusData.errors.length > 0) {
            alert(`⚠️ Restauração finalizada com erros:\n${statusData.errors.join('\n')}`);
          } else {
            alert('✅ Restauração concluída com sucesso (serviços reiniciados em background).');
          }
        }
      } catch (error) {
        console.error('Erro ao consultar status da restauração:', error);
      }
    },
    []
  );

  const pollUpdateStatus = useCallback(
    async (jobId) => {
      try {
        const response = await fetchUpdateStatus(jobId);
        const statusData = response.status;
        if (statusData) {
          setUpdateStatus(statusData);
          setUpdateLog(statusData.steps || []);
        }
      } catch (error) {
        console.error('Erro ao consultar status da atualização:', error);
      }
    },
    []
  );

  useEffect(() => {
    if (activeTab === 'services') {
      loadServiceStatus();
    }
  }, [activeTab, loadServiceStatus]);

  useEffect(() => {
    if (activeTab === 'services' && autoRefresh) {
      const interval = setInterval(() => {
        loadServiceStatus();
      }, 3000); // Atualiza a cada 3 segundos

      return () => clearInterval(interval);
    }
  }, [activeTab, autoRefresh, loadServiceStatus]);

  useEffect(() => {
    if (activeTab === 'git') {
      loadGitStatus();
      loadGitLog();
      loadGitConfig();
      loadBranches(false);
    }
  }, [activeTab, loadBranches, loadGitConfig, loadGitLog, loadGitStatus]);

  useEffect(() => {
    if (!selectedBranch && gitStatus?.branch) {
      setSelectedBranch(gitStatus.branch);
    }
  }, [gitStatus, selectedBranch]);

  useEffect(() => {
    if (activeTab === 'logs') {
      loadLogs();
    }
  }, [activeTab, loadLogs]);

  useEffect(() => {
    if (activeTab === 'update') {
      loadBranches();
    }
  }, [activeTab, loadBranches]);

  useEffect(() => {
    if (activeTab === 'backups') {
      loadBackups();
    }
  }, [activeTab, loadBackups]);

  useEffect(() => {
    if (!restoreJob) {
      return undefined;
    }

    const fetchStatus = () => pollRestoreStatus(restoreJob.job_id || restoreJob);
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [restoreJob, pollRestoreStatus]);

  useEffect(() => {
    if (!updateJob) {
      return undefined;
    }

    const fetchStatus = () => pollUpdateStatus(updateJob.job_id || updateJob);
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [updateJob, pollUpdateStatus]);

  useEffect(() => {
    if (!updateStatus || !updateJob) {
      return;
    }

    if (updateStatus.state === 'failed') {
      const msg = Array.isArray(updateStatus.errors) && updateStatus.errors.length
        ? updateStatus.errors.join('\n')
        : 'Atualização falhou.';
      alert(`❌ ${msg}`);
      setUpdateJob(null);
    } else if (updateStatus.state === 'waiting_restart') {
      alert('✅ Atualização concluída. Reinício dos serviços agendado.');
      setUpdateJob(null);
      loadServiceStatus();
    }
  }, [updateStatus, updateJob, loadServiceStatus]);

  const handleBranchCheckout = async () => {
    if (!selectedBranch) {
      alert('Selecione um branch antes de continuar.');
      return;
    }

    if (!confirm(`Tem certeza que deseja alterar o branch para "${selectedBranch}"?`)) {
      return;
    }

    setBranchLoading(true);
    setBranchLog([]);
    try {
      const response = await api.post('/api/maintenance/git/checkout', {
        branch: selectedBranch,
        force: branchForce,
        fetch: branchFetch,
      });

      console.log('[Maintenance] Git checkout response:', response.data);
      const payload = response.data?.success === true ? response.data.data : response.data;
      if (payload?.steps) {
        setBranchLog(payload.steps);
      }

      alert(response.data?.message || payload?.message || 'Branch alterado com sucesso!');
      await loadBranches(false);
      await loadGitStatus();
      await loadGitLog();
    } catch (error) {
      console.error('Erro ao trocar de branch:', error);
      const details = error.response?.data;
      const steps = details?.data?.steps || [];
      if (steps.length > 0) {
        setBranchLog(steps);
      }
      const message = details?.message || error.message || 'Erro ao trocar de branch';
      alert(`❌ ${message}`);
    } finally {
      setBranchLoading(false);
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
    const refDescription = selectedUpdateRef ? `\\nReferência selecionada: ${selectedUpdateRef}` : '';
    const confirmMessage = force
      ? `⚠️ ATENÇÃO: Mudanças locais serão DESCARTADAS!${refDescription}\\n\\nO processo será executado em background:\\n- git pull (forçado)\\n- npm run build\\n- manage.sh all restart\\n\\nDeseja continuar?`
      : `🔄 Atualizar o sistema do GitHub?${refDescription}\\n\\nIsso vai:\\n- Fazer git pull na referência selecionada\\n- Detectar arquivos alterados\\n- Executar npm run build\\n- Reiniciar os serviços em background\\n\\n✅ Seus dados (vídeos, contas, etc) serão MANTIDOS`;

    if (!confirm(confirmMessage)) {
      return;
    }

    setLoading(true);
    setActiveTab('update');
    setUpdateLog([]);
    setUpdateStatus(null);

    try {
      const payload = await triggerUpdate({
        force,
        target_ref: selectedUpdateRef || undefined,
        remote: selectedUpdateRemote || undefined,
      });
      const job = payload?.status || payload;
      if (job) {
        setUpdateJob(job);
        setUpdateStatus(job);
        setUpdateLog(job.steps || []);
      }
      alert(payload?.message || 'Atualização agendada. Acompanhe o status abaixo.');
      setLoading(false);
    } catch (error) {
      console.error('[Maintenance] Update error:', error);
      const apiError = error.response?.data;
      const message = apiError?.message || error.message || 'Erro na atualização';

      if (message.includes('alterações locais') || message.includes('uncommitted changes')) {
        const forceUpdate = confirm(
          `❌ ${message}\\n\\n💡 Deseja FORÇAR a atualização?\\n(Isso vai descartar as mudanças locais)`
        );

        if (forceUpdate) {
          setLoading(false);
          await handleUpdate(true);
          return;
        }
      }

      alert(`❌ Erro na atualização: ${message}`);
      setUpdateLog([{ step: 'error', success: false, error: message }]);
      setLoading(false);
    }
  };

  const handleCompleteReinstall = async () => {
    const confirmed = confirm(
      '🔥 REINSTALAÇÃO COMPLETA\n\n' +
      '⚠️ ATENÇÃO: Esta ação é IRREVERSÍVEL!\n\n' +
      'Todos os seus dados serão APAGADOS:\n' +
      '❌ Vídeos agendados\n' +
      '❌ Contas TikTok\n' +
      '❌ Perfis do Chrome\n' +
      '❌ Histórico de posts\n' +
      '❌ Configurações\n\n' +
      'Digite "CONFIRMAR" para prosseguir:'
    );

    if (!confirmed) {
      return;
    }

    const doubleCheck = prompt(
      '🚨 ÚLTIMA CONFIRMAÇÃO\n\n' +
      'Digite exatamente: APAGAR TUDO\n\n' +
      'Isso vai DELETAR permanentemente todos os dados!'
    );

    if (doubleCheck !== 'APAGAR TUDO') {
      alert('❌ Reinstalação cancelada. Texto não corresponde.');
      return;
    }

    setLoading(true);
    setUpdateLog([]);
    setActiveTab('update');

    try {
      const response = await api.post('/api/maintenance/reinstall');

      const data = response.data?.data || response.data;
      setUpdateLog(data.steps || []);

      if (data.completed || response.data?.success) {
        alert(
          '✅ Reinstalação completa concluída!\n\n' +
          'O sistema foi resetado. Você pode precisar:\n' +
          '1. Fazer login novamente\n' +
          '2. Reconfigurar contas TikTok\n' +
          '3. Reagendar vídeos'
        );

        // Recarregar página após 2 segundos
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
      } else {
        alert(`⚠️ Reinstalação completada com erros:\n${data.errors?.join('\n') || 'Erro desconhecido'}`);
      }
    } catch (error) {
      console.error('[Maintenance] Reinstall error:', error);
      const message = error.response?.data?.message || error.message;
      alert(`❌ Erro na reinstalação: ${message}`);
      setUpdateLog([{ step: 'error', success: false, error: message }]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    if (!confirm('Criar backup do sistema (exceto vídeos)? Perfis e configurações serão incluídos.')) {
      return;
    }

    setCreatingBackup(true);
    try {
      const response = await api.post('/api/maintenance/backup/create');
      console.log('[Maintenance] Backup create response:', response.data);
      const payload = response.data?.success === true ? response.data.data : response.data;
      alert(response.data?.message || '✅ Backup criado com sucesso!');
      if (payload?.filename) {
        setRestoreSteps([{
          step: 'backup_create',
          success: true,
          message: `Backup gerado: ${payload.filename}`,
        }]);
      }
      await loadBackups();
    } catch (error) {
      console.error('Erro ao criar backup:', error);
      const message = error.response?.data?.message || error.message;
      alert(`❌ Falha ao criar backup: ${message}`);
    } finally {
      setCreatingBackup(false);
    }
  };

  const handleDownloadBackup = async (filename) => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        alert('Sessão expirada. Faça login novamente.');
        window.location.href = '/login';
        return;
      }

      const baseURL = (import.meta.env.VITE_API_URL || window.location.origin).replace(/\/$/, '');
      const url = `${baseURL}/api/maintenance/backup/download?file=${encodeURIComponent(filename)}`;

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const disposition = response.headers.get('content-disposition');
      let suggestedName = filename;
      if (disposition) {
        const match = disposition.match(/filename="?([^"]+)"?/);
        if (match?.[1]) {
          suggestedName = match[1];
        }
      }

      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = suggestedName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);
    } catch (error) {
      console.error('Erro ao baixar backup:', error);
      const message = error.message || 'Erro desconhecido';
      alert(`❌ Falha ao baixar backup: ${message}`);
    }
  };

  const handleRestoreBackup = async (event) => {
    event.preventDefault();
    if (!selectedBackupFile) {
      alert('Selecione um arquivo de backup (.tar.gz)');
      return;
    }

    if (!confirm('Restaurar backup selecionado? Isso substituirá arquivos do sistema.')) {
      return;
    }

    setRestoreLoading(true);
    setRestoreSteps([]);

    try {
      const payload = await restoreBackup(selectedBackupFile);
      console.log('[Maintenance] Backup restore response:', payload);
      const job = payload?.status || payload;
      setRestoreJob(job);
      setRestoreSteps(job?.steps || []);
      setRestoreStatus(job);
      alert(payload?.message || '🔄 Restauração iniciada. Acompanhe o progresso abaixo.');
      await loadBackups();
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setSelectedBackupFile(null);
    } catch (error) {
      console.error('Erro ao restaurar backup:', error);
      const message = error.response?.data?.message || error.message;
      setRestoreSteps([{ step: 'error', success: false, error: message }]);
      alert(`❌ Falha na restauração: ${message}`);
    } finally {
      setRestoreLoading(false);
    }
  };

  const handleDeleteBackup = async (filename) => {
    if (!confirm(`Excluir backup "${filename}"? Esta ação não pode ser desfeita.`)) {
      return;
    }

    try {
      await api.delete('/api/maintenance/backup/delete', { params: { file: filename } });
      alert('✅ Backup removido com sucesso.');
      await loadBackups();
    } catch (error) {
      console.error('Erro ao excluir backup:', error);
      const message = error.response?.data?.message || error.message;
      alert(`❌ Falha ao excluir backup: ${message}`);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString('pt-BR');
  };

  const formatBytes = (bytes) => {
    const value = Number(bytes);
    if (!Number.isFinite(value)) return '0 B';
    if (value === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let idx = 0;
    let size = value;
    while (size >= 1024 && idx < units.length - 1) {
      size /= 1024;
      idx += 1;
    }
    const formatted = size >= 10 ? size.toFixed(0) : size.toFixed(1);
    return `${formatted} ${units[idx]}`;
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
     { id: 'backups', label: 'Backups', icon: Archive },
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
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                💡 <strong>Dica:</strong> Use "Reiniciar" após fazer alterações no código.
                Evite parar os serviços, pois você perderá acesso à interface web.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 mb-6">
              <Button
                onClick={() => handleServiceAction('restart')}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <RotateCw className="w-4 h-4 mr-2" />
                {loading ? 'Reiniciando...' : 'Reiniciar Todos os Serviços'}
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
                  <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                        Branch Atual
                      </h3>
                      <code className="px-2 py-1 bg-gray-200 dark:bg-gray-900 rounded text-xs font-mono text-blue-600 dark:text-blue-400">
                        {branchData.current_branch || gitStatus.branch || 'desconhecido'}
                      </code>
                    </div>

                    <select
                      value={selectedBranch}
                      onChange={(e) => setSelectedBranch(e.target.value)}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm"
                    >
                      <option value="">-- Escolha um branch local --</option>
                      {branchData.locals.map((branch) => (
                        <option key={`git-local-${branch.name}`} value={branch.name}>
                          {branch.name} {branch.subject ? `• ${branch.subject}` : ''}
                        </option>
                      ))}
                      {branchData.remotes.length > 0 && (
                        <optgroup label="Remotos">
                          {branchData.remotes.map((branch) => (
                            <option key={`git-remote-${branch.name}`} value={branch.name}>
                              {branch.name} {branch.subject ? `• ${branch.subject}` : ''}
                            </option>
                          ))}
                        </optgroup>
                      )}
                    </select>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="rounded"
                          checked={branchFetch}
                          onChange={(e) => setBranchFetch(e.target.checked)}
                        />
                        git fetch antes de trocar
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="rounded"
                          checked={branchForce}
                          onChange={(e) => setBranchForce(e.target.checked)}
                        />
                        Stash automático (force)
                      </label>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        onClick={handleBranchCheckout}
                        disabled={branchLoading || !selectedBranch}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <GitBranch className="w-4 h-4 mr-2" />
                        {branchLoading ? 'Aplicando...' : 'Trocar Branch'}
                      </Button>
                      <Button
                        onClick={() => loadBranches(true)}
                        disabled={branchLoading}
                        variant="outline"
                        size="sm"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Atualizar lista
                      </Button>
                    </div>

                    {branchLog.length > 0 && (
                      <div className="bg-white dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2 max-h-48 overflow-auto">
                        {branchLog.map((step, index) => (
                          <div key={`git-branch-log-${index}`} className="text-xs">
                            <div className="flex items-center gap-2">
                              {step.success ? (
                                <CheckCircle className="w-4 h-4 text-green-600" />
                              ) : (
                                <AlertCircle className="w-4 h-4 text-red-600" />
                              )}
                              <span className="font-medium text-gray-800 dark:text-gray-200">
                                {step.step}
                              </span>
                            </div>
                            {step.output && (
                              <pre className="mt-1 whitespace-pre-wrap font-mono text-gray-600 dark:text-gray-400">
                                {step.output}
                              </pre>
                            )}
                            {step.error && (
                              <p className="mt-1 text-red-600 dark:text-red-400">
                                {step.error}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
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
              {gitLog.map((commit) => (
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
          <Card title="🌿 Gerenciar Branch / Rollback">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span>
                  Branch atual:{' '}
                  <code className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded font-mono text-blue-600 dark:text-blue-400">
                    {branchData.current_branch || 'desconhecido'}
                  </code>
                </span>
                <Button
                  onClick={() => loadBranches(true)}
                  disabled={branchLoading}
                  variant="outline"
                  size="sm"
                >
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Atualizar lista
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                    Selecionar branch local
                  </label>
                  <select
                    className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm"
                    value={selectedBranch}
                    onChange={(e) => setSelectedBranch(e.target.value)}
                  >
                  <option value="">-- Escolha um branch local --</option>
                    {branchData.locals.map((branch) => (
                      <option key={`local-${branch.name}`} value={branch.name}>
                        {branch.name} • {branch.subject}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                    Ou escolher branch remoto
                  </label>
                  <select
                    className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm"
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value) {
                        setSelectedBranch(value);
                      }
                    }}
                  >
                    <option value="">-- Escolha um branch remoto --</option>
                    {branchData.remotes.map((branch) => (
                      <option key={`remote-${branch.name}`} value={branch.name}>
                        {branch.name} • {branch.subject}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-sm">
                <label className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <input
                    type="checkbox"
                    className="rounded"
                    checked={branchFetch}
                    onChange={(e) => setBranchFetch(e.target.checked)}
                  />
                  Atualizar refs remotas (git fetch)
                </label>
                <label className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <input
                    type="checkbox"
                    className="rounded"
                    checked={branchForce}
                    onChange={(e) => setBranchForce(e.target.checked)}
                  />
                  Stash automático (force)
                </label>
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={handleBranchCheckout}
                  disabled={branchLoading || !selectedBranch}
                  className="bg-green-600 hover:bg-green-700"
                >
                  <GitBranch className="w-4 h-4 mr-2" />
                  {branchLoading ? 'Aplicando...' : 'Trocar para o branch selecionado'}
                </Button>
                {selectedBranch && (
                  <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                    Destino: <code className="ml-1 font-mono">{selectedBranch}</code>
                  </div>
                )}
              </div>

              {branchLog.length > 0 && (
                <div className="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2">
                  {branchLog.map((step, index) => (
                    <div key={`branch-log-${index}`} className="text-sm">
                      <div className="flex items-center gap-2">
                        {step.success ? (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-red-600" />
                        )}
                        <span className="font-medium text-gray-800 dark:text-gray-200">
                          {step.step}
                        </span>
                      </div>
                      {step.output && (
                        <pre className="mt-1 text-xs whitespace-pre-wrap text-gray-600 dark:text-gray-400 font-mono">
                          {step.output}
                        </pre>
                      )}
                      {step.error && (
                        <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                          {step.error}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* Atualização do Sistema */}
          <Card title="🔄 Atualizar Sistema (Fluxo 2025)">
            <div className="mb-4 rounded-lg border border-indigo-400/70 bg-indigo-50 px-4 py-3 text-sm text-indigo-800 shadow-sm dark:border-indigo-300/40 dark:bg-indigo-900/40 dark:text-indigo-100">
              <p className="font-semibold">Novo fluxo de atualização disponível!</p>
              <p className="mt-1 text-xs">
                Selecione abaixo a referência (branch/tag) desejada para atualizar o sistema e confirme para aplicar a nova versão.
              </p>
            </div>
            <div className="mb-4">
              <p className="text-gray-600 dark:text-gray-400 mb-3">
                Atualiza o código do sistema mantendo seus dados:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400 mb-4">
                <li>✅ Atualiza código (frontend/backend)</li>
                <li>✅ Mantém vídeos agendados</li>
                <li>✅ Mantém contas TikTok</li>
                <li>✅ Mantém configurações</li>
                <li>✅ Mantém histórico de posts</li>
              </ul>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Selecionar branch/tag para atualizar
                </label>
                <select
                  value={selectedUpdateRef}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSelectedUpdateRef(value);
                    setSelectedUpdateRemote(computeRemoteFromRef(value));
                  }}
                  className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-md text-sm"
                >
                  <option value="">
                    Usar upstream configurado ({branchData.current_branch || 'desconhecido'})
                  </option>
                  {(branchData.remotes || []).map((remote) => (
                    <option key={`remote-${remote.name}`} value={remote.name}>
                      {remote.name}
                    </option>
                  ))}
                  {(branchData.locals || []).map((local) => (
                    <option key={`local-${local.name}`} value={local.name}>
                      {local.name} (local)
                    </option>
                  ))}
                </select>
                {selectedUpdateRef ? (
                  <div className="mt-3 flex items-center gap-2 rounded-md border border-blue-400/60 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 dark:border-blue-400/40 dark:bg-blue-900/30 dark:text-blue-200">
                    <Info className="h-4 w-4" />
                    <span>
                      Atualização preparada para{' '}
                      <code className="font-mono text-sm">{selectedUpdateRef}</code>
                      {selectedUpdateRemote
                        ? ` (remote ${selectedUpdateRemote})`
                        : ' (branch local)'}
                    </span>
                  </div>
                ) : (
                  <div className="mt-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:border-gray-700 dark:bg-gray-800/60 dark:text-gray-300">
                    Escolha um branch ou tag acima para preparar a próxima atualização.
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={() => handleUpdate(false)}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  {loading ? 'Aplicando atualização...' : 'Atualizar Sistema (novo fluxo)'}
                </Button>

                <Button
                  onClick={() => handleUpdate(true)}
                  disabled={loading}
                  variant="outline"
                  className="border-orange-500 text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20"
                >
                  <AlertCircle className="w-4 h-4 mr-2" />
                  Forçar (se houver conflitos)
                </Button>
              </div>
            </div>
          </Card>

          {/* Atualização Completa */}
          <Card title="🔥 Atualização Completa (Avançado)">
            <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-red-800 dark:text-red-200 mb-2">
                    ⚠️ ATENÇÃO: Esta ação é IRREVERSÍVEL!
                  </p>
                  <p className="text-sm text-red-700 dark:text-red-300 mb-2">
                    Esta opção vai APAGAR todos os seus dados:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-red-700 dark:text-red-300">
                    <li>❌ Vídeos agendados serão DELETADOS</li>
                    <li>❌ Contas TikTok serão REMOVIDAS</li>
                    <li>❌ Perfis do Chrome serão LIMPOS</li>
                    <li>❌ Histórico de posts será APAGADO</li>
                    <li>❌ Configurações serão RESETADAS</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="mb-4">
              <p className="text-gray-600 dark:text-gray-400 mb-3">
                Use apenas se quiser começar do zero ou resolver problemas graves.
              </p>
            </div>

            <Button
              onClick={() => handleCompleteReinstall()}
              disabled={loading}
              className="bg-red-600 hover:bg-red-700"
            >
              <AlertCircle className="w-4 h-4 mr-2" />
              {loading ? 'Reinstalando...' : 'Reinstalar Completamente'}
            </Button>
          </Card>

          {/* Log de Atualização/Reinstalação */}
          {(updateLog.length > 0 || updateStatus) && (
            <Card title="Log de Atualização">
              <div className="space-y-3">
                {updateStatus && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                    <p>
                      Estado:{' '}
                      <span className="font-semibold text-gray-700 dark:text-gray-200">
                        {updateStatus.state || 'desconhecido'}
                      </span>
                    </p>
                    <p>
                      Job ID:{' '}
                      <code className="font-mono text-blue-600 dark:text-blue-300">
                        {updateStatus.job_id}
                      </code>
                    </p>
                    {updateStatus.started_at && (
                      <p>Iniciado: {new Date(updateStatus.started_at).toLocaleString('pt-BR')}</p>
                    )}
                    {updateStatus.finished_at && (
                      <p>Finalizado: {new Date(updateStatus.finished_at).toLocaleString('pt-BR')}</p>
                    )}
                    {Array.isArray(updateStatus.errors) && updateStatus.errors.length > 0 && (
                      <div className="text-red-600 dark:text-red-400">
                        <p>Erros:</p>
                        <ul className="list-disc pl-6">
                          {updateStatus.errors.map((err, idx) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                {updateLog.length > 0 ? (
                  updateLog.map((step, index) => (
                    <div key={index} className="flex items-start gap-2 text-sm">
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
                  ))
                ) : (
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Nenhum passo registrado ainda. Aguarde alguns segundos e o status será atualizado.
                  </p>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Backups Tab */}
      {activeTab === 'backups' && (
        <div className="space-y-6">
          <Card title="📦 Criar Backup do Sistema">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <p>
                  Gera um arquivo <code>.tar.gz</code> com o código e configurações do projeto.
                </p>
                <p>
                  A pasta <strong>videos</strong> é preservada (fora do backup). Perfis, configurações e demais arquivos serão incluídos.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  onClick={handleCreateBackup}
                  disabled={creatingBackup}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Archive className="w-4 h-4 mr-2" />
                  {creatingBackup ? 'Gerando backup...' : 'Criar backup (.tar.gz)'}
                </Button>
                <Button
                  onClick={loadBackups}
                  variant="outline"
                  disabled={backupsLoading}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Atualizar lista
                </Button>
              </div>
            </div>
          </Card>

          <Card title="📁 Backups Disponíveis">
            {backupsLoading ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">Carregando backups...</p>
            ) : backups.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Nenhum backup encontrado. Clique em &quot;Criar backup&quot; para gerar o primeiro.
              </p>
            ) : (
              <div className="space-y-3">
                {backups.map((backup) => (
                  <div
                    key={backup.filename}
                    className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between rounded-lg border border-gray-200 dark:border-gray-700 p-4"
                  >
                    <div className="space-y-1">
                      <p className="font-medium text-gray-900 dark:text-white">{backup.filename}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Criado em{' '}
                        {backup.created_at
                          ? new Date(backup.created_at).toLocaleString('pt-BR')
                          : 'desconhecido'}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-mono text-gray-600 dark:text-gray-300">
                        {formatBytes(backup.size)}
                      </span>
                      <Button
                        onClick={() => handleDownloadBackup(backup.filename)}
                        variant="outline"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Baixar
                      </Button>
                      <Button
                        onClick={() => handleDeleteBackup(backup.filename)}
                        variant="ghost"
                        className="text-red-600 hover:text-red-700 dark:text-red-400"
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Excluir
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="🔄 Restaurar Backup">
            <form onSubmit={handleRestoreBackup} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Selecionar arquivo (.tar.gz)
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".tar.gz,application/gzip"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    setSelectedBackupFile(file || null);
                  }}
                  className="w-full text-sm text-gray-600 dark:text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-900/30 dark:file:text-blue-200"
                />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  O processo executa automaticamente <code>npm run build</code> e{' '}
                  <code>manage.sh all restart</code> após restaurar os arquivos. A pasta{' '}
                  <code>videos</code> existente não é substituída.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  type="submit"
                  disabled={!selectedBackupFile || restoreLoading}
                  className="bg-green-600 hover:bg-green-700"
                >
                  <UploadCloud className="w-4 h-4 mr-2" />
                  {restoreLoading ? 'Restaurando...' : 'Restaurar Backup'}
                </Button>
                {selectedBackupFile && (
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    Arquivo selecionado:{' '}
                    <code className="font-mono text-blue-600 dark:text-blue-300">
                      {selectedBackupFile.name}
                    </code>
                  </span>
                )}
              </div>
            </form>

            {restoreSteps.length > 0 && (
              <div className="mt-6 bg-gray-100 dark:bg-gray-800 p-4 rounded-lg space-y-3">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Passos executados {restoreStatus?.state ? `(${restoreStatus.state})` : ''}
                </h3>
                {restoreStatus && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                    <p>Job ID: <code className="font-mono text-blue-600 dark:text-blue-300">{restoreStatus.job_id}</code></p>
                    {restoreStatus.started_at && <p>Iniciado: {new Date(restoreStatus.started_at).toLocaleString('pt-BR')}</p>}
                    {restoreStatus.finished_at && <p>Finalizado: {new Date(restoreStatus.finished_at).toLocaleString('pt-BR')}</p>}
                    {Array.isArray(restoreStatus.errors) && restoreStatus.errors.length > 0 && (
                      <div className="text-red-600 dark:text-red-400">
                        <p>Erros:</p>
                        <ul className="list-disc pl-6">
                          {restoreStatus.errors.map((err, idx) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                <div className="space-y-3">
                  {restoreSteps.map((step, index) => {
                    const success = step.success !== false;
                    const title = step.message || step.step || `Passo ${index + 1}`;
                    return (
                      <div key={index} className="flex items-start gap-3">
                        {success ? (
                          <CheckCircle className="mt-1 w-5 h-5 text-green-600" />
                        ) : (
                          <AlertCircle className="mt-1 w-5 h-5 text-red-600" />
                        )}
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                            {title}
                          </p>
                          {Array.isArray(step.restored_items) && step.restored_items.length > 0 && (
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                              Itens restaurados: {step.restored_items.join(', ')}
                            </p>
                          )}
                          {step.error && (
                            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{step.error}</p>
                          )}
                          {step.output && (
                            <pre className="mt-2 max-h-48 overflow-auto rounded bg-black/80 p-2 text-xs text-green-200 whitespace-pre-wrap">
                              {step.output}
                            </pre>
                          )}
                        </div>
                      </div>
                    );
                  })}
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
