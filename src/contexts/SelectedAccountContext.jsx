import { createContext, useContext, useState, useEffect } from 'react';

const SelectedAccountContext = createContext(undefined);

export function SelectedAccountProvider({ children }) {
  const [selectedAccountId, setSelectedAccountId] = useState(() => {
    return localStorage.getItem('selected_account_id') || null;
  });

  useEffect(() => {
    if (selectedAccountId) {
      localStorage.setItem('selected_account_id', selectedAccountId);
    } else {
      localStorage.removeItem('selected_account_id');
    }
  }, [selectedAccountId]);

  const value = {
    selectedAccountId,
    setSelectedAccountId,
  };

  return (
    <SelectedAccountContext.Provider value={value}>
      {children}
    </SelectedAccountContext.Provider>
  );
}

export function useSelectedAccount() {
  const context = useContext(SelectedAccountContext);
  if (context === undefined) {
    throw new Error('useSelectedAccount deve ser usado dentro de SelectedAccountProvider');
  }
  return context;
}
