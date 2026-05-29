import { createContext, useContext, useState, useEffect } from "react";
import { apiMe } from "../services/api";
import { supabase } from "../services/supabaseClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(() => localStorage.getItem("token"));
    const [loading, setLoading] = useState(true);

    /* Verifica se o token salvo ainda é válido ao carregar */
    useEffect(() => {
        if (token) {
            apiMe(token)
                .then((data) => setUser(data))
                .catch(() => {
                    localStorage.removeItem("token");
                    setToken(null);
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    function login(tokenValue, userData) {
        localStorage.setItem("token", tokenValue);
        setToken(tokenValue);
        setUser(userData);
    }

    /* Re-busca o perfil do backend (ex.: após trocar a clínica ativa, para que
       clinica_id e demais dados do usuário fiquem atualizados no app). */
    async function refreshUser() {
        if (!token) return null;
        const data = await apiMe(token);
        setUser(data);
        return data;
    }

    async function logout() {
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
        try {
            await supabase.auth.signOut();
        } catch (e) {
            console.error(e);
        }
        window.location.href = "/login";
    }

    return (
        <AuthContext.Provider value={{ user, token, login, logout, loading, refreshUser }}>
            {children}
        </AuthContext.Provider>
    );
}

/* Hook de conveniência */
export function useAuth() {
    return useContext(AuthContext);
}
