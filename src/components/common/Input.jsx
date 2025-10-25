import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export default function Input({
  type = 'text',
  label,
  placeholder,
  helperText,
  error = false,
  disabled = false,
  icon: Icon,
  value,
  onChange,
  className = '',
  ...props
}) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword && showPassword ? 'text' : type;
  
  const handleChange = (e) => {
    if (onChange) {
      onChange(e.target.value);
    }
  };
  
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && (
        <label className="text-sm font-medium text-text-primary">
          {label}
        </label>
      )}
      
      <div className="relative">
        {Icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary">
            <Icon className="w-5 h-5" />
          </div>
        )}
        
        <input
          type={inputType}
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          disabled={disabled}
          className={`
            w-full h-10 px-4 ${Icon ? 'pl-10' : ''} ${isPassword ? 'pr-10' : ''}
            bg-background border rounded-lg
            text-text-primary placeholder:text-text-tertiary
            transition-all duration-200
            focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed
            ${error ? 'border-red-500' : 'border-border hover:border-border-hover'}
          `}
          {...props}
        />
        
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary transition-colors"
          >
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        )}
      </div>
      
      {helperText && (
        <p className={`text-sm ${error ? 'text-red-500' : 'text-text-tertiary'}`}>
          {helperText}
        </p>
      )}
    </div>
  );
}
