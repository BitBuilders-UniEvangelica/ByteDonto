import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiGetEquipe, apiCriarMembro, apiRemoverMembro, apiAtualizarMembro, apiAtualizarPermissoes, apiRedefinirSenha } from "../../services/api";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useOwnerSidebar } from "../../hooks/useSidebar";
import { validarEmail, formatDate } from "../../utils/formatters";
import { ArrowLeft, CheckCircle2, UserPlus, AlertTriangle, EllipsisVertical, Power, KeyRound, ShieldCheck, Pencil, Trash2 } from "lucide-react";
import "../../styles/clinic.css";
import "../../styles/Forms.css";
import "../../styles/Table.css";

const PAPEIS = ["Especialista", "Recepção"];

const LABELS_PERMISSAO = {
    ver_pacientes:      "Ver pacientes",
    editar_pacientes:   "Editar pacientes",
    ver_prontuario:     "Ver prontuário",
    editar_prontuario:  "Editar prontuário",
    ver_agenda:         "Ver agenda",
    agendar_consultas:  "Agendar consultas",
    cancelar_consultas: "Cancelar consultas",
    ver_financeiro:     "Ver financeiro",
};

const PAPEL_LABEL = {
    Dono: { label: "Proprietário", bg: "var(--PrimaryColorsBack)", cor: "var(--PrimaryColorsTheme)" },
    Especialista: { label: "Especialista", bg: "var(--PrimaryColorsBack)", cor: "var(--PrimaryColors)" },
    "Recepção": { label: "Recepção", bg: "var(--SuccessBack)", cor: "var(--SuccessText)" },
};

const FORM_INICIAL = { nome: "", email: "", senha: "", papel: "Especialista", cro: "" };

/* Menu de ações de um membro (botão de 3 pontos).
   O menu usa position: fixed porque a tabela corta o que passa da borda
   (overflow: hidden). As coordenadas do botão vêm em pixels de tela, então
   são divididas pelo zoom global do app (--app-zoom) antes de posicionar.
   No celular o menu abre como gaveta presa ao rodapé da tela: não depende
   dessas coordenadas, que o Safari do iPhone calcula diferente com zoom. */
function MenuAcoes({ itens, rotulo }) {
    const [pos, setPos] = useState(null);
    const botaoRef = useRef(null);
    const menuRef = useRef(null);
    const fundoRef = useRef(null);
    const aberto = pos !== null;
    const gaveta = pos?.gaveta === true;

    function alternar() {
        if (aberto) { setPos(null); return; }
        if (window.matchMedia("(max-width: 768px)").matches) { setPos({ gaveta: true }); return; }
        const zoom = parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
        const r = botaoRef.current.getBoundingClientRect();
        const alturaMenu = itens.length * 40 + 12;
        const abreParaCima = (window.innerHeight - r.bottom) / zoom < alturaMenu + 8;
        setPos({
            right: (window.innerWidth - r.right) / zoom,
            ...(abreParaCima ? { bottom: (window.innerHeight - r.top) / zoom + 4 } : { top: r.bottom / zoom + 4 }),
        });
    }

    // Fecha ao clicar fora, apertar Esc, rolar ou redimensionar a tela.
    useEffect(() => {
        if (!aberto) return;
        const fechar = () => setPos(null);
        const aoClicar = (e) => {
            // O fundo escuro da gaveta fecha pelo próprio onClick (evita que o
            // toque "atravesse" e acione o que estiver embaixo).
            if (menuRef.current?.contains(e.target) || botaoRef.current?.contains(e.target) || e.target === fundoRef.current) return;
            fechar();
        };
        const aoTeclar = (e) => { if (e.key === "Escape") fechar(); };
        document.addEventListener("mousedown", aoClicar);
        document.addEventListener("keydown", aoTeclar);
        window.addEventListener("scroll", fechar, true);
        window.addEventListener("resize", fechar);
        return () => {
            document.removeEventListener("mousedown", aoClicar);
            document.removeEventListener("keydown", aoTeclar);
            window.removeEventListener("scroll", fechar, true);
            window.removeEventListener("resize", fechar);
        };
    }, [aberto]);

    return (
        <>
            <button
                ref={botaoRef}
                type="button"
                onClick={alternar}
                aria-label={rotulo}
                title={rotulo}
                aria-haspopup="menu"
                aria-expanded={aberto}
                style={{
                    width: "34px", height: "34px", padding: 0, display: "inline-flex", alignItems: "center", justifyContent: "center",
                    background: aberto ? "var(--PrimaryColorsBack)" : "transparent",
                    color: aberto ? "var(--PrimaryColorsTheme)" : "var(--TextColor75)",
                    border: "1px solid var(--LineColor)", borderRadius: "8px", cursor: "pointer",
                }}>
                <EllipsisVertical size={18} strokeWidth={2} />
            </button>
            {aberto && gaveta && (
                <div ref={fundoRef} className="acoes-backdrop" onClick={() => setPos(null)} />
            )}
            {aberto && (
                <div
                    ref={menuRef}
                    role="menu"
                    style={gaveta ? {
                        position: "fixed", left: 0, right: 0, bottom: 0, zIndex: "calc(var(--z-dropdown) + 1)", padding: "12px 12px 24px",
                        background: "var(--ThemeColor)", borderTop: "1px solid var(--LineColor)", borderRadius: "16px 16px 0 0",
                        boxShadow: "var(--shadow-md)", display: "flex", flexDirection: "column", gap: "4px",
                    } : {
                        position: "fixed", ...pos, zIndex: "var(--z-dropdown)", minWidth: "190px", padding: "6px",
                        background: "var(--ThemeColor)", border: "1px solid var(--LineColor)", borderRadius: "10px",
                        boxShadow: "var(--shadow-md)", display: "flex", flexDirection: "column",
                    }}>
                    {gaveta && (
                        <p style={{ margin: "4px 12px 8px", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)" }}>{rotulo}</p>
                    )}
                    {itens.map(({ label, cor, onClick, disabled, ...item }) => {
                        const Icon = item.Icon;
                        return (
                        <button
                            key={label}
                            type="button"
                            role="menuitem"
                            disabled={disabled}
                            onClick={() => { setPos(null); onClick(); }}
                            onMouseEnter={e => { e.currentTarget.style.background = "var(--BackColor)"; }}
                            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
                            style={{
                                display: "flex", alignItems: "center", gap: "10px", width: "100%", height: gaveta ? "48px" : "40px", padding: "0 12px",
                                background: "transparent", border: "none", borderRadius: "8px", textAlign: "left",
                                color: cor || "var(--TextColor)", fontSize: gaveta ? "15px" : "13px", fontWeight: 600, fontFamily: "inherit",
                                cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1,
                            }}>
                            <Icon size={16} strokeWidth={2} />
                            {label}
                        </button>
                        );
                    })}
                </div>
            )}
        </>
    );
}

function BindClinic() {
    const { token } = useAuth();
    const opc_bar = useOwnerSidebar("team");

    const [equipe, setEquipe] = useState([]);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState(null);

    // Modal de criação
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState(FORM_INICIAL);
    const [enviando, setEnviando] = useState(false);
    const [formErro, setFormErro] = useState(null);
    const [formSucesso, setFormSucesso] = useState(null);

    // Modal de edição
    const [showEdit, setShowEdit] = useState(false);
    const [membroEditando, setMembroEditando] = useState(null);
    const [editForm, setEditForm] = useState({ nome: "", papel: "", percentual_repasse: 0, cro: "" });
    const [editEnviando, setEditEnviando] = useState(false);
    const [editErro, setEditErro] = useState(null);

    // Modal de permissões
    const [showPerm, setShowPerm] = useState(false);
    const [membroPermissoes, setMembroPermissoes] = useState(null);
    const [permForm, setPermForm] = useState({});
    const [permSalvando, setPermSalvando] = useState(false);
    const [permErro, setPermErro] = useState(null);
    const [permSucesso, setPermSucesso] = useState(false);

    // Modal de redefinir senha
    const [showSenha, setShowSenha] = useState(false);
    const [membroSenha, setMembroSenha] = useState(null);
    const [senhaForm, setSenhaForm] = useState({ senha: "", confirma: "" });
    const [senhaEnviando, setSenhaEnviando] = useState(false);
    const [senhaErro, setSenhaErro] = useState(null);
    const [senhaSucesso, setSenhaSucesso] = useState(false);

    // Confirmação de remoção
    const [removendoId, setRemovendoId] = useState(null);

    // Ativar / desativar membro
    const [statusId, setStatusId] = useState(null);

    const carregarEquipe = useCallback(async () => {
        setCarregando(true);
        setErro(null);
        try {
            const data = await apiGetEquipe(token);
            setEquipe(data);
        } catch (e) {
            setErro(e.message);
        } finally {
            setCarregando(false);
        }
    }, [token]);

    useEffect(() => {
        carregarEquipe();
    }, [carregarEquipe]);

    useEffect(() => {
        document.body.style.overflow = showForm || showEdit || showPerm ? "hidden" : "auto";
        return () => { document.body.style.overflow = "auto"; };
    }, [showForm, showEdit, showPerm]);

    // --- Criar membro ---
    function abrirForm() {
        setForm(FORM_INICIAL);
        setFormErro(null);
        setFormSucesso(null);
        setShowForm(true);
    }

    async function handleCriar(e) {
        e.preventDefault();
        setFormErro(null);
        setFormSucesso(null);

        if (!validarEmail(form.email)) {
            setFormErro("E-mail inválido.");
            return;
        }

        if (form.papel === "Especialista" && !form.cro.trim()) {
            setFormErro("CRO é obrigatório para o Especialista (ex.: CRO-SP 12345).");
            return;
        }

        setEnviando(true);
        try {
            const novo = await apiCriarMembro(token, form);
            setFormSucesso(`${novo.nome} adicionado com sucesso!`);
            setEquipe(prev => [...prev, { id: novo.id, nome: novo.nome, papel: novo.papel, created_at: new Date().toISOString() }]);
            setTimeout(() => {
                setShowForm(false);
                setFormSucesso(null);
            }, 1500);
        } catch (e) {
            setFormErro(e.message);
        } finally {
            setEnviando(false);
        }
    }

    // --- Editar membro ---
    function abrirEdit(membro) {
        setMembroEditando(membro);
        setEditForm({
            nome: membro.nome,
            papel: membro.papel,
            percentual_repasse: Number(membro.percentual_repasse || 0),
            cro: membro.cro || "",
        });
        setEditErro(null);
        setShowEdit(true);
    }

    async function handleEditar(e) {
        e.preventDefault();
        if (editForm.papel === "Especialista" && !String(editForm.cro || "").trim()) {
            setEditErro("CRO é obrigatório para o Especialista (ex.: CRO-SP 12345).");
            return;
        }
        setEditEnviando(true);
        setEditErro(null);
        try {
            // CRO só vale para Especialista; ao mudar para outro papel, zera o CRO.
            const payload = { ...editForm };
            if (payload.papel !== "Especialista") payload.cro = null;
            const atualizado = await apiAtualizarMembro(token, membroEditando.id, payload);
            setEquipe(prev => prev.map(m => m.id === membroEditando.id ? { ...m, ...atualizado } : m));
            setShowEdit(false);
        } catch (e) {
            setEditErro(e.message);
        } finally {
            setEditEnviando(false);
        }
    }

    // --- Redefinir senha ---
    function abrirSenha(membro) {
        setMembroSenha(membro);
        setSenhaForm({ senha: "", confirma: "" });
        setSenhaErro(null);
        setSenhaSucesso(false);
        setShowSenha(true);
    }

    async function handleRedefinirSenha(e) {
        e.preventDefault();
        setSenhaErro(null);
        if (senhaForm.senha.length < 8) {
            setSenhaErro("A senha deve ter no mínimo 8 caracteres.");
            return;
        }
        if (senhaForm.senha !== senhaForm.confirma) {
            setSenhaErro("As senhas não conferem.");
            return;
        }
        setSenhaEnviando(true);
        try {
            await apiRedefinirSenha(token, membroSenha.id, senhaForm.senha);
            setSenhaSucesso(true);
            setSenhaForm({ senha: "", confirma: "" });
        } catch (err) {
            setSenhaErro(err.message);
        } finally {
            setSenhaEnviando(false);
        }
    }

    // --- Permissões ---
    function abrirPermissoes(membro) {
        setMembroPermissoes(membro);
        setPermForm(membro.permissoes || {});
        setPermErro(null);
        setPermSucesso(false);
        setShowPerm(true);
    }

    async function handleSalvarPermissoes(e) {
        e.preventDefault();
        setPermSalvando(true);
        setPermErro(null);
        try {
            const resultado = await apiAtualizarPermissoes(token, membroPermissoes.id, permForm);
            setEquipe(prev => prev.map(m =>
                m.id === membroPermissoes.id ? { ...m, permissoes: resultado.permissoes } : m
            ));
            setPermSucesso(true);
            setTimeout(() => setShowPerm(false), 1200);
        } catch (e) {
            setPermErro(e.message);
        } finally {
            setPermSalvando(false);
        }
    }

    // --- Ativar / desativar membro ---
    async function handleAlternarStatus(membro) {
        const atual = membro.ativo !== false;
        setStatusId(membro.id);
        try {
            const atualizado = await apiAtualizarMembro(token, membro.id, { ativo: !atual });
            setEquipe(prev => prev.map(m =>
                m.id === membro.id ? { ...m, ativo: atualizado.ativo ?? !atual } : m
            ));
        } catch (e) {
            // A coluna "ativo" pode não existir se a migração do banco não foi aplicada
            alert(
                "Não foi possível alterar o status do membro. " +
                "Verifique se a atualização do banco de dados foi aplicada.\n\n" +
                e.message
            );
        } finally {
            setStatusId(null);
        }
    }

    // --- Remover membro ---
    async function handleRemover(id) {
        setRemovendoId(id);
        try {
            await apiRemoverMembro(token, id);
            setEquipe(prev => prev.filter(m => m.id !== id));
        } catch (e) {
            alert(e.message);
        } finally {
            setRemovendoId(null);
        }
    }

    const membrosNaoDono = equipe.filter(m => m.papel !== "Dono");
    const dono = equipe.find(m => m.papel === "Dono");

    return (
        <>
            <Section type_styles="owner" />
            <SideBar opc={opc_bar} styles="owner" />

            {/* Modal — Criar membro */}
            {showForm && (
                <div className="forms-hover owner" style={{ display: "flex" }}>
                    <div className="forms-card">
                        <div style={{ marginBottom: "1.5rem" }}>
                            <h2 style={{ margin: 0, color: "var(--PrimaryColorsTheme)" }}>Adicionar Membro</h2>
                            <p className="text75" style={{ margin: "0.5rem 0 0 0", fontSize: "14px" }}>
                                Crie o acesso para um profissional da sua clínica.
                            </p>
                        </div>

                        {formSucesso ? (
                            <div style={{ textAlign: "center", padding: "2rem 0" }}>
                                <CheckCircle2 size={48} strokeWidth={2} color="var(--SuccessText)" />
                                <p style={{ fontWeight: 700, color: "var(--SuccessText)", marginTop: "0.75rem" }}>{formSucesso}</p>
                            </div>
                        ) : (
                            <form onSubmit={handleCriar}>
                                {formErro && (
                                    <div style={{ background: "var(--DangerBack)", color: "var(--DangerText)", padding: "10px 14px", borderRadius: "8px", marginBottom: "1rem", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                                        <AlertTriangle size={16} strokeWidth={2} /> {formErro}
                                    </div>
                                )}
                                <div className="field">
                                    <label htmlFor="nome">Nome completo *</label>
                                    <input id="nome" type="text" required value={form.nome}
                                        onChange={e => setForm(p => ({ ...p, nome: e.target.value }))} />
                                </div>
                                <div className="field">
                                    <label htmlFor="email">E-mail *</label>
                                    <input id="email" type="email" required value={form.email}
                                        onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
                                </div>
                                <div className="field">
                                    <label htmlFor="senha">Senha de acesso *</label>
                                    <input id="senha" type="password" required minLength={6} value={form.senha}
                                        onChange={e => setForm(p => ({ ...p, senha: e.target.value }))}
                                        placeholder="Mínimo 6 caracteres" />
                                </div>
                                <div className="field">
                                    <label htmlFor="papel">Nível de acesso *</label>
                                    <select id="papel" value={form.papel}
                                        onChange={e => setForm(p => ({ ...p, papel: e.target.value }))}>
                                        {PAPEIS.map(p => (
                                            <option key={p} value={p}>{p === "Recepção" ? "Recepção / Atendimento" : p}</option>
                                        ))}
                                    </select>
                                </div>
                                {form.papel === "Especialista" && (
                                    <div className="field">
                                        <label htmlFor="cro">CRO (Registro no Conselho) *</label>
                                        <input id="cro" type="text" value={form.cro}
                                            onChange={e => setForm(p => ({ ...p, cro: e.target.value }))}
                                            placeholder="Ex.: CRO-SP 12345" />
                                        <p style={{ fontSize: "12px", color: "var(--TextColor75)", margin: "6px 0 0 0" }}>
                                            Obrigatório para cirurgiões-dentistas. Aparece no prontuário e nas prescrições.
                                        </p>
                                    </div>
                                )}
                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "2rem" }}>
                                    <button type="button" className="submit"
                                        style={{ background: "var(--LineColor)", color: "var(--TextColor)", boxShadow: "none" }}
                                        onClick={() => setShowForm(false)} disabled={enviando}>
                                        Cancelar
                                    </button>
                                    <button type="submit" className="submit" disabled={enviando}>
                                        {enviando ? "Criando..." : "Criar Acesso"}
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}

            {/* Modal — Editar membro */}
            {showEdit && membroEditando && (
                <div className="forms-hover owner" style={{ display: "flex" }}>
                    <div className="forms-card">
                        <div style={{ marginBottom: "1.5rem" }}>
                            <h2 style={{ margin: 0, color: "var(--PrimaryColorsTheme)" }}>Editar Membro</h2>
                            <p className="text75" style={{ margin: "0.5rem 0 0 0", fontSize: "14px" }}>
                                Altere o nome ou o nível de acesso de {membroEditando.nome}.
                            </p>
                        </div>
                        <form onSubmit={handleEditar}>
                            {editErro && (
                                <div style={{ background: "var(--DangerBack)", color: "var(--DangerText)", padding: "10px 14px", borderRadius: "8px", marginBottom: "1rem", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                                    <AlertTriangle size={16} strokeWidth={2} /> {editErro}
                                </div>
                            )}
                            <div className="field">
                                <label htmlFor="edit-nome">Nome completo *</label>
                                <input id="edit-nome" type="text" required value={editForm.nome}
                                    onChange={e => setEditForm(p => ({ ...p, nome: e.target.value }))} />
                            </div>
                            <div className="field">
                                <label htmlFor="edit-papel">Nível de acesso *</label>
                                <select id="edit-papel" value={editForm.papel}
                                    onChange={e => setEditForm(p => ({ ...p, papel: e.target.value }))}>
                                    {PAPEIS.map(p => (
                                        <option key={p} value={p}>{p === "Recepção" ? "Recepção / Atendimento" : p}</option>
                                    ))}
                                </select>
                            </div>
                            {editForm.papel === "Especialista" && (
                                <div className="field">
                                    <label htmlFor="edit-cro">CRO (Registro no Conselho) *</label>
                                    <input id="edit-cro" type="text" value={editForm.cro}
                                        onChange={e => setEditForm(p => ({ ...p, cro: e.target.value }))}
                                        placeholder="Ex.: CRO-SP 12345" />
                                </div>
                            )}
                            {editForm.papel === "Especialista" && (
                                <div className="field">
                                    <label htmlFor="edit-pct">Percentual de repasse (%)</label>
                                    <input
                                        id="edit-pct"
                                        type="number"
                                        min="0"
                                        max="100"
                                        step="0.5"
                                        value={editForm.percentual_repasse}
                                        onChange={e => setEditForm(p => ({ ...p, percentual_repasse: e.target.value }))}
                                    />
                                    <p style={{ fontSize: "12px", color: "var(--TextColor75)", margin: "6px 0 0 0" }}>
                                        Quanto este dentista recebe sobre o valor dos procedimentos pagos por seus pacientes.
                                    </p>
                                </div>
                            )}
                            <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "2rem" }}>
                                <button type="button" className="submit"
                                    style={{ background: "var(--LineColor)", color: "var(--TextColor)", boxShadow: "none" }}
                                    onClick={() => setShowEdit(false)} disabled={editEnviando}>
                                    Cancelar
                                </button>
                                <button type="submit" className="submit" disabled={editEnviando}>
                                    {editEnviando ? "Salvando..." : "Salvar"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal — Redefinir senha */}
            {showSenha && membroSenha && (
                <div className="forms-hover owner" style={{ display: "flex" }}>
                    <div className="forms-card" style={{ maxWidth: "440px", width: "100%" }}>
                        <div style={{ marginBottom: "1.5rem" }}>
                            <h2 style={{ margin: 0, color: "var(--PrimaryColorsTheme)" }}>Redefinir Senha</h2>
                            <p className="text75" style={{ margin: "0.5rem 0 0 0", fontSize: "14px" }}>
                                Defina uma nova senha de acesso para <strong>{membroSenha.nome}</strong>.
                            </p>
                        </div>

                        {senhaSucesso ? (
                            <div style={{ textAlign: "center", padding: "1.5rem 0" }}>
                                <CheckCircle2 size={48} strokeWidth={2} color="var(--SuccessText)" />
                                <p style={{ margin: "1rem 0 0 0", fontWeight: 600 }}>Senha redefinida com sucesso.</p>
                                <p className="text75" style={{ margin: "0.5rem 0 0 0", fontSize: "13px" }}>
                                    Informe a nova senha ao membro. Ela já vale no próximo login.
                                </p>
                                <button type="button" className="submit" style={{ marginTop: "1.5rem" }} onClick={() => setShowSenha(false)}>
                                    Fechar
                                </button>
                            </div>
                        ) : (
                            <form onSubmit={handleRedefinirSenha}>
                                {senhaErro && (
                                    <div style={{ background: "var(--DangerBack)", color: "var(--DangerText)", padding: "10px 14px", borderRadius: "8px", marginBottom: "1rem", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                                        <AlertTriangle size={16} strokeWidth={2} /> {senhaErro}
                                    </div>
                                )}
                                <div className="field">
                                    <label htmlFor="nova-senha">Nova senha *</label>
                                    <input id="nova-senha" type="password" required minLength={8} value={senhaForm.senha}
                                        onChange={e => setSenhaForm(p => ({ ...p, senha: e.target.value }))}
                                        placeholder="Mínimo 8 caracteres" />
                                </div>
                                <div className="field">
                                    <label htmlFor="confirma-senha">Confirmar nova senha *</label>
                                    <input id="confirma-senha" type="password" required value={senhaForm.confirma}
                                        onChange={e => setSenhaForm(p => ({ ...p, confirma: e.target.value }))}
                                        placeholder="Repita a nova senha" />
                                </div>
                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "2rem" }}>
                                    <button type="button" className="submit"
                                        style={{ background: "var(--LineColor)", color: "var(--TextColor)", boxShadow: "none" }}
                                        onClick={() => setShowSenha(false)} disabled={senhaEnviando}>
                                        Cancelar
                                    </button>
                                    <button type="submit" className="submit" disabled={senhaEnviando}>
                                        {senhaEnviando ? "Salvando..." : "Redefinir Senha"}
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}

            {/* Modal — Permissões */}
            {showPerm && membroPermissoes && (
                <div className="forms-hover owner" style={{ display: "flex" }}>
                    <div className="forms-card" style={{ maxWidth: "480px", width: "100%" }}>
                        <div style={{ marginBottom: "1.5rem" }}>
                            <h2 style={{ margin: 0, color: "var(--PrimaryColorsTheme)" }}>Permissões</h2>
                            <p className="text75" style={{ margin: "0.5rem 0 0 0", fontSize: "14px" }}>
                                Defina o que <strong>{membroPermissoes.nome}</strong> pode acessar.
                            </p>
                        </div>

                        {permSucesso ? (
                            <div style={{ textAlign: "center", padding: "2rem 0" }}>
                                <CheckCircle2 size={48} strokeWidth={2} color="var(--SuccessText)" />
                                <p style={{ fontWeight: 700, color: "var(--SuccessText)", marginTop: "0.75rem" }}>Permissões salvas!</p>
                            </div>
                        ) : (
                            <form onSubmit={handleSalvarPermissoes}>
                                {permErro && (
                                    <div style={{ background: "var(--DangerBack)", color: "var(--DangerText)", padding: "10px 14px", borderRadius: "8px", marginBottom: "1rem", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                                        <AlertTriangle size={16} strokeWidth={2} /> {permErro}
                                    </div>
                                )}

                                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "1.5rem" }}>
                                    {Object.entries(LABELS_PERMISSAO).map(([chave, label]) => (
                                        <label key={chave} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", background: "var(--BackColor)", border: "1px solid var(--LineColor)", borderRadius: "8px", cursor: "pointer", gap: "1rem" }}>
                                            <span style={{ fontSize: "14px", fontWeight: 500 }}>{label}</span>
                                            <div
                                                onClick={() => setPermForm(p => ({ ...p, [chave]: !p[chave] }))}
                                                style={{
                                                    width: "42px", height: "24px", borderRadius: "12px", flexShrink: 0,
                                                    background: permForm[chave] ? "var(--PrimaryColorsTheme)" : "var(--LineColor)",
                                                    position: "relative", cursor: "pointer", transition: "background 0.2s",
                                                }}>
                                                <div style={{
                                                    position: "absolute", top: "3px",
                                                    left: permForm[chave] ? "21px" : "3px",
                                                    width: "18px", height: "18px", borderRadius: "50%",
                                                    background: "#fff", transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                                                }} />
                                            </div>
                                        </label>
                                    ))}
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem" }}>
                                    <button type="button" className="submit"
                                        style={{ background: "var(--LineColor)", color: "var(--TextColor)", boxShadow: "none" }}
                                        onClick={() => setShowPerm(false)} disabled={permSalvando}>
                                        Cancelar
                                    </button>
                                    <button type="submit" className="submit" disabled={permSalvando}>
                                        {permSalvando ? "Salvando..." : "Salvar Permissões"}
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}

            <main className="mainBar owner register">
                <p>
                    <Link className="text75" to="/owner/clinic" style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <ArrowLeft size={16} strokeWidth={2} /> Voltar para Clínicas
                    </Link>
                </p>

                <div className="camp-clinic camp-register">
                    <div className="page-header" style={{ alignItems: "center", marginBottom: "2em" }}>
                        <div>
                            <h1 style={{ margin: "0 0 0.5rem 0" }}>Equipe da Clínica</h1>
                            <p className="text75 page-header-desc">Gerencie os acessos dos profissionais. Você define o login e o nível de permissão de cada membro.</p>
                        </div>
                        <button className="submit" onClick={abrirForm} style={{ padding: "12px 24px", fontSize: "15px", display: "inline-flex", alignItems: "center", gap: "6px" }}>
                            <UserPlus size={18} strokeWidth={2} /> Adicionar Membro
                        </button>
                    </div>

                    {carregando ? (
                        <div style={{ textAlign: "center", padding: "3rem" }}>
                            <p className="text75">Carregando equipe...</p>
                        </div>
                    ) : erro ? (
                        <div style={{ textAlign: "center", padding: "3rem" }}>
                            <p style={{ color: "var(--DangerText)" }}>{erro}</p>
                            <button className="submit" onClick={carregarEquipe} style={{ marginTop: "1rem" }}>Tentar novamente</button>
                        </div>
                    ) : (
                        <>
                            {/* Card do Proprietário */}
                            {dono && (
                                <div style={{ marginBottom: "2rem" }}>
                                    <p className="text75" style={{ marginBottom: "0.75rem", fontWeight: 700, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Proprietário</p>
                                    <div className="table-row grid-owner" style={{ background: "var(--PrimaryColorsBack)", borderRadius: "10px", padding: "14px 16px" }}>
                                        <div>
                                            <p style={{ fontWeight: 700 }}>{dono.nome}</p>
                                        </div>
                                        <span style={{ background: "var(--ThemeColor)", color: "var(--PrimaryColorsTheme)", padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, alignSelf: "center", width: "fit-content" }}>
                                            Proprietário
                                        </span>
                                        <p className="hide-mobile" style={{ fontSize: "12px", color: "var(--TextColor75)", alignSelf: "center" }}>Acesso total</p>
                                    </div>
                                </div>
                            )}

                            {/* Tabela da equipe */}
                            <p className="text75" style={{ marginBottom: "0.75rem", fontWeight: 700, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                                Membros ({membrosNaoDono.length})
                            </p>

                            {membrosNaoDono.length === 0 ? (
                                <div style={{ textAlign: "center", padding: "3rem 1rem", border: "2px dashed var(--LineColor)", borderRadius: "12px" }}>
                                    <p style={{ fontWeight: 700, fontSize: "16px" }}>Nenhum membro adicionado</p>
                                    <p className="text75" style={{ marginTop: "0.5rem" }}>
                                        Clique em "Adicionar Membro" para criar o acesso de um especialista ou recepcionista.
                                    </p>
                                </div>
                            ) : (
                                <div className="table">
                                    <div className="table-header grid-team">
                                        <p className="text75">Nome</p>
                                        <p className="text75">Nível de Acesso</p>
                                        <p className="text75 hide-mobile">Status</p>
                                        <p className="text75 hide-mobile">Adicionado em</p>
                                        <p className="text75" style={{ textAlign: "right" }}>Ações</p>
                                    </div>

                                    <div className="table-body">
                                        {membrosNaoDono.map(membro => {
                                            const config = PAPEL_LABEL[membro.papel] || { label: membro.papel, bg: "var(--BackColor)", cor: "var(--TextColor75)" };
                                            const dataFormatada = formatDate(membro.created_at);
                                            const ativo = membro.ativo !== false;
                                            return (
                                                <div className="table-row grid-team" key={membro.id}>
                                                    <div>
                                                        <p style={{ fontWeight: 600 }}>{membro.nome}</p>
                                                        {membro.papel === "Especialista" && membro.cro && (
                                                            <span style={{ fontSize: "12px", color: "var(--TextColor75)" }}>{membro.cro}</span>
                                                        )}
                                                    </div>
                                                    <span style={{ background: config.bg, color: config.cor, padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, alignSelf: "center", width: "fit-content" }}>
                                                        {config.label}
                                                    </span>
                                                    <span className="hide-mobile" style={{
                                                        background: ativo ? "var(--SuccessBack)" : "var(--DangerBack)",
                                                        color: ativo ? "var(--SuccessText)" : "var(--DangerText)",
                                                        padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700,
                                                        alignSelf: "center", width: "fit-content",
                                                    }}>
                                                        {ativo ? "Ativo" : "Inativo"}
                                                    </span>
                                                    <p className="text75 hide-mobile" style={{ fontSize: "13px", alignSelf: "center" }}>{dataFormatada}</p>
                                                    <div style={{ display: "flex", justifyContent: "flex-end", alignSelf: "center" }}>
                                                        <MenuAcoes
                                                            rotulo={`Ações de ${membro.nome}`}
                                                            itens={[
                                                                {
                                                                    label: statusId === membro.id ? "Aguarde..." : (ativo ? "Desativar" : "Ativar"),
                                                                    Icon: Power,
                                                                    cor: ativo ? "var(--WarningText)" : "var(--SuccessText)",
                                                                    onClick: () => handleAlternarStatus(membro),
                                                                    disabled: statusId === membro.id,
                                                                },
                                                                { label: "Redefinir senha", Icon: KeyRound, onClick: () => abrirSenha(membro) },
                                                                { label: "Permissões", Icon: ShieldCheck, onClick: () => abrirPermissoes(membro) },
                                                                { label: "Editar", Icon: Pencil, onClick: () => abrirEdit(membro) },
                                                                {
                                                                    label: removendoId === membro.id ? "Removendo..." : "Remover",
                                                                    Icon: Trash2,
                                                                    cor: "var(--DangerText)",
                                                                    onClick: () => handleRemover(membro.id),
                                                                    disabled: removendoId === membro.id,
                                                                },
                                                            ]}
                                                        />
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </main>
        </>
    );
}

export default BindClinic;
