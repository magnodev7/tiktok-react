import { Upload, X, AlertCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import Button from '../common/Button';
import Input from '../common/Input';
import { useAccounts } from '@/hooks/useAccounts';
import { useUploadVideo } from '@/hooks/useScheduledVideos';
import { useSelectedAccount } from '@/contexts/SelectedAccountContext';

export default function UploadSection() {
  const [files, setFiles] = useState([]);
  const [filesMetadata, setFilesMetadata] = useState({});
  const [description, setDescription] = useState('');
  const [hashtags, setHashtags] = useState('');
  const [selectedAccount, setSelectedAccount] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
  const [editingFile, setEditingFile] = useState(null);

  const { data: accounts } = useAccounts();
  const uploadMutation = useUploadVideo();
  const { selectedAccountId, setSelectedAccountId } = useSelectedAccount();

  useEffect(() => {
    if (!accounts || accounts.length === 0) return;

    if (selectedAccountId) {
      const matchById = accounts.find(
        (account) => String(account.id) === String(selectedAccountId),
      );
      if (matchById && matchById.account_name !== selectedAccount) {
        setSelectedAccount(matchById.account_name);
      }
      return;
    }

    if (!selectedAccount) {
      const fallback = accounts.find((account) => account.is_active) || accounts[0];
      if (fallback) {
        setSelectedAccount(fallback.account_name);
        setSelectedAccountId(String(fallback.id));
      }
    }
  }, [accounts, selectedAccountId, selectedAccount, setSelectedAccountId]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      setFiles(prevFiles => [...prevFiles, ...newFiles]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles(prevFiles => [...prevFiles, ...newFiles]);
    }
  };

  const removeFile = (index) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };

  const handleAccountChange = (value) => {
    setSelectedAccount(value);
    const account = accounts?.find((item) => item.account_name === value);
    if (account) {
      setSelectedAccountId(String(account.id));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validação
    if (files.length === 0) {
      setError('Selecione pelo menos um vídeo');
      return;
    }

    if (!selectedAccount) {
      setError('Selecione uma conta TikTok');
      return;
    }

    setUploading(true);
    setUploadProgress({ current: 0, total: files.length });

    let successCount = 0;
    let errorCount = 0;
    const errors = [];

    // Fazer upload de cada arquivo
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setUploadProgress({ current: i + 1, total: files.length });

      // ✅ Preparar FormData com campos corretos
      const formData = new FormData();
      formData.append('video', file);
      formData.append('account', selectedAccount);

      // Para arquivo único, usa os campos do formulário
      // Para múltiplos, usa metadados individuais (se existirem)
      if (files.length === 1) {
        if (description) formData.append('description', description);
        if (hashtags) formData.append('hashtags', hashtags);
      } else {
        // Múltiplos arquivos: usa metadados individuais
        const metadata = filesMetadata[i] || {};
        if (metadata.description) formData.append('description', metadata.description);
        if (metadata.hashtags) formData.append('hashtags', metadata.hashtags);
      }

      // ✅ schedule_time é OPCIONAL - backend agenda automaticamente
      if (scheduleTime) {
        formData.append('schedule_time', scheduleTime);
      }

      console.log(`📤 Enviando ${i + 1}/${files.length}:`, {
        video: file.name,
        account: selectedAccount,
        metadata: files.length === 1 ? { description, hashtags } : filesMetadata[i]
      });

      try {
        await uploadMutation.mutateAsync(formData);
        successCount++;
      } catch (error) {
        console.error(`❌ Upload failed for ${file.name}:`, error);
        errorCount++;
        errors.push(`${file.name}: ${error.response?.data?.detail || error.message}`);
      }
    }

    setUploading(false);

    // Mostrar resultado
    if (errorCount === 0) {
      // Sucesso total - Reset form
      setFiles([]);
      setFilesMetadata({});
      setDescription('');
      setHashtags('');
      setScheduleTime('');
      setError('');
    } else {
      // Alguns erros
      const errorMsg = `✅ ${successCount} vídeo(s) enviado(s) com sucesso\n❌ ${errorCount} erro(s):\n${errors.join('\n')}`;
      setError(errorMsg);
    }
  };

  return (
    <div className="bg-background-elevated border border-border rounded-lg p-6">
      <h2 className="text-lg font-semibold text-text-primary mb-4">📤 Upload de Vídeo</h2>
      
      {/* Erro */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-400 whitespace-pre-wrap">{error}</p>
        </div>
      )}

      {files.length === 0 ? (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-lg p-12
            flex flex-col items-center justify-center
            transition-all duration-200 cursor-pointer
            ${dragActive
              ? 'border-accent bg-accent-subtle'
              : 'border-border hover:border-accent'
            }
          `}
          onClick={() => document.getElementById('file-input').click()}
        >
          <Upload className="w-12 h-12 text-accent mb-4" />
          <p className="text-text-primary mb-2">Arraste seus vídeos aqui ou clique para selecionar</p>
          <p className="text-sm text-text-tertiary">MP4, MOV • Máx. 100MB por vídeo • Múltiplos arquivos permitidos</p>
          <input
            id="file-input"
            type="file"
            accept="video/*"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Files Preview */}
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-text-primary">
                {files.length} {files.length === 1 ? 'vídeo selecionado' : 'vídeos selecionados'}
              </p>
              <button
                type="button"
                onClick={() => document.getElementById('file-input').click()}
                className="text-sm text-accent hover:underline"
              >
                + Adicionar mais
              </button>
            </div>

            <div className="max-h-96 overflow-y-auto space-y-2">
              {files.map((file, index) => (
                <div key={index} className="bg-background rounded-lg border border-border overflow-hidden">
                  <div className="flex items-center gap-3 p-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">{file.name}</p>
                      <p className="text-xs text-text-tertiary">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>

                    {/* Mostrar botão de editar apenas se houver múltiplos arquivos */}
                    {files.length > 1 && (
                      <button
                        type="button"
                        onClick={() => setEditingFile(editingFile === index ? null : index)}
                        className="px-3 py-1 text-xs text-accent hover:bg-accent/10 rounded transition-colors"
                      >
                        {editingFile === index ? 'Fechar' : 'Editar'}
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="p-1 hover:bg-red-500/10 rounded transition-colors flex-shrink-0"
                    >
                      <X className="w-4 h-4 text-red-500" />
                    </button>
                  </div>

                  {/* Editor de metadados para múltiplos arquivos */}
                  {files.length > 1 && editingFile === index && (
                    <div className="px-3 pb-3 space-y-3 border-t border-border pt-3">
                      <Input
                        label="Descrição (opcional)"
                        placeholder="Adicione uma descrição..."
                        value={filesMetadata[index]?.description || ''}
                        onChange={(value) => setFilesMetadata(prev => ({
                          ...prev,
                          [index]: { ...prev[index], description: value }
                        }))}
                      />
                      <Input
                        label="Hashtags (opcional)"
                        placeholder="#exemplo #hashtag"
                        value={filesMetadata[index]?.hashtags || ''}
                        onChange={(value) => setFilesMetadata(prev => ({
                          ...prev,
                          [index]: { ...prev[index], hashtags: value }
                        }))}
                      />
                      <p className="text-xs text-text-tertiary">
                        💡 Se não preencher, será gerada automaticamente
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <input
            id="file-input"
            type="file"
            accept="video/*"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Form Fields - Apenas para arquivo único */}
          {files.length === 1 && (
            <>
              <Input
                label="Descrição (opcional)"
                placeholder="Adicione uma descrição..."
                value={description}
                onChange={setDescription}
              />

              <Input
                label="Hashtags (opcional)"
                placeholder="#exemplo #hashtag"
                value={hashtags}
                onChange={setHashtags}
              />
            </>
          )}

          {/* Aviso para múltiplos arquivos */}
          {files.length > 1 && (
            <div className="p-3 bg-accent-subtle/50 border border-accent/20 rounded-lg">
              <p className="text-sm text-text-secondary">
                💡 <strong>Múltiplos vídeos:</strong> Use o botão "Editar" em cada vídeo para adicionar descrição e hashtags individualmente. Se não editar, será gerado automaticamente.
              </p>
            </div>
          )}

          {/* ✅ Select CORRIGIDO */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Conta TikTok <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedAccount}
              onChange={(e) => handleAccountChange(e.target.value)}
              className="w-full h-10 px-4 bg-background border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
              required
            >
              <option value="">Selecione uma conta</option>
              {accounts?.map((account) => (
                <option key={account.id} value={account.account_name}>
                  @{account.account_name}
                </option>
              ))}
            </select>
          </div>

          {/* ✅ Data/Hora OPCIONAL */}
          <div>
            <Input
              type="datetime-local"
              label="Agendar para (opcional)"
              value={scheduleTime}
              onChange={setScheduleTime}
            />
            <p className="text-xs text-text-tertiary mt-1">
              💡 Deixe em branco para agendar automaticamente no próximo horário disponível
            </p>
          </div>

          {/* Progress indicator */}
          {uploading && (
            <div className="p-3 bg-accent-subtle border border-accent/20 rounded-lg">
              <p className="text-sm text-accent font-medium mb-1">
                Fazendo upload... {uploadProgress.current}/{uploadProgress.total}
              </p>
              <div className="w-full bg-background rounded-full h-2">
                <div
                  className="bg-accent h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <Button type="submit" fullWidth loading={uploading} disabled={uploading}>
              {uploading
                ? `Enviando ${uploadProgress.current}/${uploadProgress.total}...`
                : scheduleTime
                  ? `Agendar ${files.length} vídeo(s)`
                  : `Agendar ${files.length} vídeo(s) automaticamente`
              }
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setFiles([]);
                setError('');
              }}
              disabled={uploading}
            >
              Cancelar
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
