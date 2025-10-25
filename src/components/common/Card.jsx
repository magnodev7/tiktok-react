export default function Card({
  children,
  variant = 'default',
  padding = 'md',
  onClick,
  className = '',
  ...rest
}) {
  const baseStyles = 'bg-background-elevated border border-border rounded-lg transition-all duration-200';
  
  const variants = {
    default: '',
    interactive: 'cursor-pointer hover:border-accent hover:-translate-y-0.5 hover:shadow-md',
    highlighted: 'border-accent',
  };
  
  const paddings = {
    none: 'p-0',
    sm: 'p-3',
    md: 'p-6',
    lg: 'p-8',
  };
  
  return (
    <div
      onClick={onClick}
      className={`${baseStyles} ${variants[variant]} ${paddings[padding]} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
