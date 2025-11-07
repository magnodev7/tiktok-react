import apiClient from '@/api/client';

export const restoreBackup = async (file) => {
  const formData = new FormData();
  formData.append('uploaded_file', file);
  const response = await apiClient.post('/api/maintenance/backup/restore', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const fetchRestoreStatus = async (jobId) => {
  const response = await apiClient.get('/api/maintenance/backup/restore/status', {
    params: jobId ? { job_id: jobId } : {},
  });
  return response.data;
};

export const triggerUpdate = async (payload) => {
  const response = await apiClient.post('/api/maintenance/update', payload);
  return response.data;
};

export const fetchUpdateStatus = async (jobId) => {
  const response = await apiClient.get('/api/maintenance/update/status', {
    params: jobId ? { job_id: jobId } : {},
  });
  return response.data;
};
