import { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
}

export const Button = ({ 
  children, 
  variant = 'primary', 
  className = '', 
  ...props 
}: ButtonProps) => {
  const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-colors';
  const variants = {
    primary: 'bg-blue-500 hover:bg-blue-600 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600'
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}; 