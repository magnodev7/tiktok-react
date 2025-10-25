/**
 * Utilitário para construir URLs de arquivos estáticos
 *
 * Resolve o problema de arquivos estáticos que são servidos diretamente
 * pelo servidor (sem o prefixo /api)
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8082/').replace(/\/$/, '');

/**
 * Constrói URL completa para arquivos estáticos
 *
 * @param {string} path - Caminho do arquivo (ex: "/user_data/users/1/profile/avatar.jpg")
 * @returns {string|null} URL completa ou null se path for inválido
 *
 * @example
 * getStaticFileUrl("/user_data/users/1/profile/avatar.jpg")
 * // => "http://localhost:8082/user_data/users/1/profile/avatar.jpg"
 *
 * // Funciona mesmo se API_BASE_URL tiver /api no final
 * // http://localhost:8082/api => http://localhost:8082/user_data/...
 */
export const getStaticFileUrl = (path) => {
  if (!path) return null;

  // Remove /api do final se existir, pois arquivos estáticos não usam /api
  const baseUrl = API_BASE_URL.replace(/\/api$/, '');

  // Garante que path começa com /
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  return `${baseUrl}${cleanPath}`;
};

/**
 * Constrói URL para imagem de perfil
 *
 * @param {string} profilePicturePath - Caminho da foto de perfil do usuário
 * @returns {string|null} URL completa ou null
 */
export const getProfilePictureUrl = (profilePicturePath) => {
  return getStaticFileUrl(profilePicturePath);
};

/**
 * Constrói URL para vídeo
 *
 * @param {string} videoPath - Caminho do vídeo
 * @returns {string|null} URL completa ou null
 */
export const getVideoUrl = (videoPath) => {
  return getStaticFileUrl(videoPath);
};

export default {
  getStaticFileUrl,
  getProfilePictureUrl,
  getVideoUrl,
};
