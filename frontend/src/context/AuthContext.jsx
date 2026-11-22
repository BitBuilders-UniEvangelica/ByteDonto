import { createContext, useContext } from "react";

/* O provedor fica em AuthProvider.jsx: este arquivo só exporta o contexto e o
   hook, para o fast refresh do Vite funcionar nos dois. */
export const AuthContext = createContext(null);

/* Hook de conveniência */
export function useAuth() {
    return useContext(AuthContext);
}
