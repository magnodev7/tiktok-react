export function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

export function validatePassword(password) {
  // Mínimo 6 caracteres
  if (password.length < 6) {
    return { valid: false, message: 'Senha deve ter no mínimo 6 caracteres' };
  }
  
  // Senha forte: 10+ caracteres, números e caracteres especiais
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
  
  if (password.length >= 10 && hasNumber && hasSpecial) {
    return { valid: true, strength: 'strong', message: 'Senha forte' };
  } else if (password.length >= 6) {
    return { valid: true, strength: 'medium', message: 'Senha média' };
  }
  
  return { valid: true, strength: 'weak', message: 'Senha fraca' };
}

export function validateRequired(value, fieldName) {
  if (!value || value.trim() === '') {
    return { valid: false, message: `${fieldName} é obrigatório` };
  }
  return { valid: true };
}
