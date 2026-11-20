import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { apiGetItemEstoque, apiGetPacientesOpcoes, apiGetEquipe, apiRegistrarSaidaEstoque } from "../../services/api";
import { formatDate } from "../../utils/formatters";
import ModalEstoque from "./ModalEstoque";
import { MOTIVOS_SAIDA, hojeISO, formatQtd } from "./estoqueUtils";

/* Registrar saída (uso em procedimento, vencimento ou perda).
   O lote é obrigatório: a saída baixa o saldo daquele lote específico. */
export default function ModalSaida({ itens, itemFixo, onFechar, onSalvo }) {
    const { token, user } = useAuth();
    const [form, setForm] = useState({
        item_id: itemFixo?.id || "",
        lote_id: "",
        quantidade: "",
        motivo: "",
        data: hojeISO(),
        paciente_id: "",
        procedimento: "",
        responsavel_id: user?.id || "",
        observacao: "",
    });
    const [lotes, setLotes] = useState(itemFixo?.lotes || null);
    const [pacientes, setPacientes] = useState([]);
    const [equipe, setEquipe] = useState([]);
    const [erro, setErro] = useState("");
    const [salvando, setSalvando] = useState(false);

    const set = (campo) => (e) => setForm(f => ({ ...f, [campo]: e.target.value }));
    const loteSel = (lotes || []).find(l => l.id === form.lote_id);
    const item = itens.find(i => i.id === form.item_id) || itemFixo;

    useEffect(() => {
        if (!token) return;
        // Quem não tem acesso a pacientes ou à equipe só não vê as opções
        apiGetPacientesOpcoes(token).then(setPacientes).catch(() => {});
        apiGetEquipe(token).then(e => setEquipe((Array.isArray(e) ? e : []).filter(m => m.ativo !== false))).catch(() => {});
    }, [token]);

    // Ao trocar o item (fora da tela de detalhes), busca os lotes com saldo dele
    useEffect(() => {
        if (!token || !form.item_id || itemFixo) return;
        let ativo = true;
        apiGetItemEstoque(token, form.item_id)
            .then(d => { if (ativo) setLotes(d.lotes || []); })
            .catch(e => { if (ativo) { setLotes([]); setErro(e.message); } });
        return () => { ativo = false; };
    }, [token, form.item_id, itemFixo]);

    function escolherItem(e) {
        setLotes(null);
        setForm(f => ({ ...f, item_id: e.target.value, lote_id: "" }));
    }

    async function salvar() {
        if (!form.item_id) return setErro("Selecione o item.");
        if (!form.lote_id) return setErro("Selecione o lote.");
        if (!(Number(form.quantidade) > 0)) return setErro("Informe uma quantidade maior que zero.");
        if (loteSel && Number(form.quantidade) > Number(loteSel.quantidade)) {
            return setErro(`Quantidade maior que o saldo do lote (${formatQtd(loteSel.quantidade)}).`);
        }
        if (!form.motivo) return setErro("Selecione o motivo.");
        if (!form.data) return setErro("Informe a data da saída.");
        if (form.data > hojeISO()) return setErro("A data da saída não pode ser no futuro.");
        if (!form.responsavel_id) return setErro("Selecione o responsável.");

        setSalvando(true);
        setErro("");
        try {
            await apiRegistrarSaidaEstoque(token, { ...form, quantidade: Number(form.quantidade) });
            onSalvo();
        } catch (e) {
            setErro(e.message);
        } finally {
            setSalvando(false);
        }
    }

    // Garante que o usuário logado aparece como opção mesmo se a lista da equipe falhar
    const responsaveis = equipe.some(m => m.id === user?.id) || !user
        ? equipe
        : [{ id: user.id, nome: user.perfil?.nome || "Eu" }, ...equipe];

    return (
        <ModalEstoque
            titulo="Registrar Saída"
            subtitulo="Uso em procedimento, vencimento ou perda."
            erro={erro}
            salvando={salvando}
            onCancelar={onFechar}
            onSalvar={salvar}
            textoSalvar="Registrar saída"
        >
            <div className="est-form-grid">
                <div className="field inteiro">
                    <label>Item *</label>
                    <select value={form.item_id} onChange={escolherItem} disabled={Boolean(itemFixo)}>
                        <option value="">Selecione o item...</option>
                        {itens.map(i => <option key={i.id} value={i.id}>{i.nome}</option>)}
                    </select>
                </div>
                <div className="field">
                    <label>Lote *</label>
                    <select value={form.lote_id} onChange={set("lote_id")} disabled={!form.item_id || lotes === null}>
                        <option value="">
                            {!form.item_id ? "Selecione o item antes..." : lotes === null ? "Carregando lotes..." : lotes.length ? "Selecione o lote..." : "Item sem saldo"}
                        </option>
                        {(lotes || []).map(l => (
                            <option key={l.id} value={l.id}>
                                {(l.lote || "Sem lote")}{l.validade ? ` · val. ${formatDate(l.validade)}` : ""} · saldo {formatQtd(l.quantidade)}
                            </option>
                        ))}
                    </select>
                </div>
                <div className="field">
                    <label>Quantidade *{item?.unidade ? ` (${item.unidade})` : ""}</label>
                    <input type="number" min="0" step="any" placeholder="0" value={form.quantidade} onChange={set("quantidade")} />
                </div>
                <div className="field">
                    <label>Motivo *</label>
                    <select value={form.motivo} onChange={set("motivo")}>
                        <option value="">Selecione o motivo...</option>
                        {MOTIVOS_SAIDA.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                </div>
                <div className="field">
                    <label>Data da saída *</label>
                    <input type="date" max={hojeISO()} value={form.data} onChange={set("data")} />
                </div>
                <div className="field">
                    <label>Paciente</label>
                    <select value={form.paciente_id} onChange={set("paciente_id")}>
                        <option value="">Selecione o paciente...</option>
                        {pacientes.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}
                    </select>
                </div>
                <div className="field">
                    <label>Procedimento</label>
                    <input placeholder="Ex.: Restauração dente 36" value={form.procedimento} onChange={set("procedimento")} maxLength={160} />
                </div>
                <div className="field inteiro">
                    <label>Responsável *</label>
                    <select value={form.responsavel_id} onChange={set("responsavel_id")}>
                        <option value="">Selecione...</option>
                        {responsaveis.map(m => <option key={m.id} value={m.id}>{m.nome}</option>)}
                    </select>
                </div>
                <div className="field inteiro">
                    <label>Observação</label>
                    <textarea placeholder="Detalhes da saída (opcional)..." value={form.observacao} onChange={set("observacao")} maxLength={1000} />
                </div>
            </div>
        </ModalEstoque>
    );
}
