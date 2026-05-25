/* IMPORTS */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { apiRegistro } from "../../services/api";
import { validarEmail } from "../../utils/formatters";
import '../../styles/Auth.css';

/* MAIN COMPONENT */
function CadastroPage() {
    const navigate = useNavigate();
    const [form, setForm] = useState({
        nome: "",
        email: "",
        password: "",
        confirmPassword: "",
    });
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [loading, setLoading] = useState(false);

    function handleChange(e) {
        setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setError("");
        setSuccess("");

        if (!validarEmail(form.email)) {
            setError("E-mail inválido.");
            return;
        }

        if (form.password.length < 8) {
            setError("A senha deve ter no mínimo 8 caracteres.");
            return;
        }

        if (form.password !== form.confirmPassword) {
            setError("As senhas não coincidem.");
            return;
        }

        setLoading(true);
        try {
            await apiRegistro(form.nome, form.email, form.password);
            setSuccess("Conta criada com sucesso! Redirecionando para o login...");
            setTimeout(() => navigate("/login"), 2000);
        } catch (err) {
            setError(err.message || "Erro ao cadastrar.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-wrapper owner">
            <div className="auth-card">

                {/* HEADER */}
                <div className="auth-header">
                    <h1 className="auth-card-logo">BYTE DONTO</h1>
                    <p>Comece a gerenciar a sua clínica hoje.</p>
                </div>

                <div className="auth-badge">NOVO PROPRIETÁRIO</div>

                {/* FORM */}
                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="field">
                        <label htmlFor="nome">Nome Completo</label>
                        <input
                            id="nome"
                            name="nome"
                            type="text"
                            placeholder="Dr. Nome Sobrenome"
                            value={form.nome}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="email">E-mail Corporativo</label>
                        <input
                            id="email"
                            name="email"
                            type="email"
                            placeholder="clinica@email.com"
                            value={form.email}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="password">Criar Senha</label>
                        <input
                            id="password"
                            name="password"
                            type="password"
                            placeholder="Mínimo de 8 caracteres"
                            value={form.password}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="confirmPassword">Confirmar Senha</label>
                        <input
                            id="confirmPassword"
                            name="confirmPassword"
                            type="password"
                            placeholder="Repita a senha"
                            value={form.confirmPassword}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    {error && <p className="auth-error">{error}</p>}
                    {success && (
                        <p style={{
                            color: "var(--SuccessText)",
                            fontSize: "13px",
                            textAlign: "center",
                            padding: "10px",
                            backgroundColor: "var(--SuccessBack)",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--LineColor)",
                            fontWeight: "500"
                        }}>
                            {success}
                        </p>
                    )}

                    <button
                        type="submit"
                        className="auth-submit"
                        disabled={loading}
                    >
                        {loading ? "CADASTRANDO..." : "CRIAR CONTA AGORA"}
                    </button>
                </form>

                {/* FOOTER */}
                <div className="auth-footer">
                    <p className="text75">
                        Já tem uma conta?{" "}
                        <Link to="/login">Fazer login</Link>
                    </p>
                    <p style={{marginTop: "8px"}}><Link to="/" style={{display: "inline-flex", alignItems: "center", gap: "4px"}}><ArrowLeft size={14} strokeWidth={2.5} /> Voltar para o início</Link></p>
                </div>
            </div>
        </div>
    );
}

/* STANDARD EXPORT */
export default CadastroPage;
