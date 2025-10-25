import React, { useState } from 'react';
import { Plus, Trash2, Key, Copy, Check, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import Input from '@/components/common/Input';
import Modal from '@/components/common/Modal';
import Badge from '@/components/common/Badge';
import { useAPIKeys } from '@/hooks/useAPIKeys';

export default function APIKeys() {
  const { apiKeys, isLoading, createAPIKey, deleteAPIKey, toggleAPIKey } = useAPIKeys();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyData, setNewKeyData] = useState({ name: '', permissions: ['read', 'write'] });
  const [createdKey, setCreatedKey] = useState(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const handleCreateKey = async () => {
    if (!newKeyData.name.trim()) {
      alert('❌ Nome da API Key é obrigatório');
      return;
    }

    try {
      const result = await createAPIKey.mutateAsync(newKeyData);
      setCreatedKey(result);
      setNewKeyData({ name: '', permissions: ['read', 'write'] });
      setShowCreateModal(false);
    } catch (error) {
      const apiError = error.response?.data;
      const message = apiError?.message || apiError?.detail || error.message;
      alert('❌ Erro ao criar API Key: ' + message);
    }
  };

  const handleCopyKey = () => {
    if (createdKey?.api_key) {
      navigator.clipboard.writeText(createdKey.api_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const handleDelete = async (keyId, keyName) => {
    if (confirm(`Tem certeza que deseja deletar a API Key "${keyName}"? Esta ação não pode ser desfeita.`)) {
      try {
        await deleteAPIKey.mutateAsync(keyId);
      } catch (error) {
        const apiError = error.response?.data;
        const message = apiError?.message || apiError?.detail || error.message;
        alert('❌ Erro ao deletar API Key: ' + message);
      }
    }
  };

  const handleToggleStatus = async (keyId, currentStatus) => {
    try {
      await toggleAPIKey.mutateAsync({ keyId, isActive: !currentStatus });
    } catch (error) {
      const apiError = error.response?.data;
      const message = apiError?.message || apiError?.detail || error.message;
      alert('❌ Erro ao alterar status: ' + message);
    }
  };

  const togglePermission = (perm) => {
    setNewKeyData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(perm)
        ? prev.permissions.filter(p => p !== perm)
        : [...prev.permissions, perm]
    }));
  };

  const allPermissions = [
    { id: 'read', label: 'Leitura', description: 'Ver vídeos, logs e configurações' },
    { id: 'write', label: 'Escrita', description: 'Modificar configurações e agendamentos' },
    { id: 'upload', label: 'Upload', description: 'Fazer upload de vídeos' },
    { id: 'delete', label: 'Deletar', description: 'Remover vídeos e configurações' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-text-primary mb-2">API Keys</h2>
          <p className="text-sm text-text-secondary">
            Gerencie suas chaves de API para integração com N8N e outros sistemas externos.
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nova API Key
        </Button>
      </div>

      {/* Info Box */}
      <Card className="bg-blue-500/10 border-blue-500/30">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Key className="w-5 h-5 text-blue-400" />
          </div>
          <div className="flex-1 space-y-4">
            <div>
              <h3 className="font-medium text-blue-300 mb-1">Como usar as API Keys</h3>
              <p className="text-sm text-blue-200/80">
                As API Keys permitem que você acesse a API do sistema de forma programática.
                Use-as em integrações com N8N, scripts ou aplicações externas.
              </p>
            </div>

            {/* Exemplo de Upload */}
            <div className="space-y-2">
              <div className="text-sm font-medium text-blue-200">📤 Upload de Vídeo (multipart/form-data)</div>
              <code className="text-xs bg-black/40 px-3 py-2 rounded block text-blue-100 font-mono">
                POST http://localhost:8082/api/upload
              </code>
              <div className="text-xs text-blue-200/70 space-y-1">
                <div><strong>Header:</strong></div>
                <code className="text-xs bg-black/30 px-2 py-1 rounded text-blue-100">X-API-Key: tk_sua_chave_aqui</code>
              </div>
              <div className="text-xs text-blue-200/70 space-y-1">
                <div><strong>Body (form-data):</strong></div>
                <div className="bg-black/30 px-3 py-2 rounded space-y-1 font-mono">
                  <div><span className="text-red-300">*</span> video: [arquivo.mp4]</div>
                  <div><span className="text-red-300">*</span> account: "novadigitalbra"</div>
                  <div>description: "Descrição do vídeo"</div>
                  <div>hashtags: "#tiktok #automation"</div>
                  <div>schedule_time: "14:00" <span className="text-blue-400">(HH:MM)</span></div>
                  <div>scheduled_at: "2025-10-17T14:00:00-03:00" <span className="text-blue-400">(ISO 8601)</span></div>
                  <div>delete_after: "false" <span className="text-blue-400">(true|false)</span></div>
                </div>
                <div className="text-red-300 mt-1"><span className="text-red-300">*</span> = Obrigatório</div>
              </div>
            </div>

            {/* Exemplo de Consulta */}
            <div className="space-y-2 border-t border-blue-500/20 pt-3">
              <div className="text-sm font-medium text-blue-200">📋 Listar Vídeos Agendados</div>
              <code className="text-xs bg-black/40 px-3 py-2 rounded block text-blue-100 font-mono">
                GET http://localhost:8082/api/scheduled?account=novadigitalbra
              </code>
              <div className="text-xs text-blue-200/70 space-y-1">
                <div><strong>Header:</strong></div>
                <code className="text-xs bg-black/30 px-2 py-1 rounded text-blue-100">X-API-Key: tk_sua_chave_aqui</code>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* API Keys List */}
      {isLoading ? (
        <Card>
          <div className="text-center py-8 text-text-secondary">
            Carregando API Keys...
          </div>
        </Card>
      ) : apiKeys && apiKeys.length > 0 ? (
        <div className="space-y-3">
          {apiKeys.map((key) => (
            <Card key={key.id} className="hover:border-accent/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-text-primary">{key.name}</h3>
                    <Badge variant={key.is_active ? 'success' : 'warning'}>
                      {key.is_active ? 'Ativa' : 'Inativa'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-text-secondary">
                    <span className="flex items-center gap-1">
                      <Key className="w-4 h-4" />
                      ID: {key.id}
                    </span>
                    <span>
                      Criada: {new Date(key.created_at).toLocaleDateString('pt-BR')}
                    </span>
                    {key.last_used && (
                      <span>
                        Último uso: {new Date(key.last_used).toLocaleString('pt-BR')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    {key.permissions && key.permissions.map((perm) => (
                      <span
                        key={perm}
                        className="text-xs px-2 py-1 bg-accent/20 text-accent rounded"
                      >
                        {perm}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleToggleStatus(key.id, key.is_active)}
                    disabled={toggleAPIKey.isPending}
                  >
                    {key.is_active ? (
                      <>
                        <EyeOff className="w-4 h-4 mr-1" />
                        Desativar
                      </>
                    ) : (
                      <>
                        <Eye className="w-4 h-4 mr-1" />
                        Ativar
                      </>
                    )}
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDelete(key.id, key.name)}
                    disabled={deleteAPIKey.isPending}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <div className="text-center py-12">
            <Key className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">
              Nenhuma API Key criada
            </h3>
            <p className="text-text-secondary mb-4">
              Crie sua primeira API Key para começar a usar a API
            </p>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Criar API Key
            </Button>
          </div>
        </Card>
      )}

      {/* Create API Key Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Criar Nova API Key"
      >
        <div className="space-y-4">
          <Input
            label="Nome da API Key"
            placeholder="Ex: Integração N8N, Script de automação..."
            value={newKeyData.name}
            onChange={(value) => setNewKeyData({ ...newKeyData, name: value })}
          />

          <div>
            <label className="block text-sm font-medium text-text-primary mb-3">
              Permissões
            </label>
            <div className="space-y-2">
              {allPermissions.map((perm) => (
                <label
                  key={perm.id}
                  className="flex items-start gap-3 p-3 bg-background-subtle rounded-lg cursor-pointer hover:bg-background-subtle/80 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={newKeyData.permissions.includes(perm.id)}
                    onChange={() => togglePermission(perm.id)}
                    className="mt-1 w-4 h-4 rounded"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-text-primary">{perm.label}</div>
                    <div className="text-sm text-text-secondary">{perm.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              onClick={handleCreateKey}
              disabled={createAPIKey.isPending || !newKeyData.name.trim()}
            >
              {createAPIKey.isPending ? 'Criando...' : 'Criar API Key'}
            </Button>
            <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      </Modal>

      {/* Success Modal - Show Created Key */}
      <Modal
        isOpen={!!createdKey}
        onClose={() => {
          setCreatedKey(null);
          setShowKey(false);
          setCopiedKey(false);
        }}
        title="API Key Criada com Sucesso!"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-yellow-300 mb-1">
                ⚠️ Importante: Guarde esta chave em local seguro
              </p>
              <p className="text-sm text-yellow-200/80">
                Esta é a única vez que você verá esta API Key completa.
                Copie-a agora e armazene em um local seguro (como 1Password ou LastPass).
              </p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Sua Nova API Key
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1 relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={createdKey?.api_key || ''}
                  readOnly
                  className="w-full bg-background-subtle border border-border rounded-lg px-4 py-2 pr-10 font-mono text-sm text-text-primary"
                />
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <Button onClick={handleCopyKey}>
                {copiedKey ? (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    Copiado!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-2" />
                    Copiar
                  </>
                )}
              </Button>
            </div>
          </div>

          <div className="bg-background-subtle rounded-lg p-4">
            <h4 className="font-medium text-text-primary mb-2">Como usar</h4>
            <p className="text-sm text-text-secondary mb-3">
              Adicione esta chave no header de suas requisições HTTP:
            </p>
            <code className="block bg-black/30 px-3 py-2 rounded text-xs text-accent break-all">
              X-API-Key: {createdKey?.api_key || 'YOUR_API_KEY'}
            </code>
          </div>

          <Button onClick={() => {
            setCreatedKey(null);
            setShowKey(false);
            setCopiedKey(false);
          }} className="w-full">
            Entendi, fechar
          </Button>
        </div>
      </Modal>
    </div>
  );
}
