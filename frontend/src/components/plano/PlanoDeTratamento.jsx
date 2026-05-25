import { useState, useEffect, useRef } from "react";
import { apiGetPlanos, apiCriarPlano, apiAtualizarPlanoItem } from "../../services/api";
import { Plus, X } from "lucide-react";

const STATUS_PLANO = { "Orcamento": "#B45309", "Aprovado": "#0E7490", "Em Andamento": "#8B5CF6", "Concluido": "#15803D", "Cancelado": "#B91C1C" };
const STATUS_ITEM  = { "Pendente": "#B45309", "Concluido": "#15803D", "Cancelado": "#B91C1C" };

function formatCurrency(v) { return Number(v||0).toLocaleString("pt-BR", { style:"currency", currency:"BRL" }); }

const ITEM_VAZIO = { procedimento:"", dente:"", quantidade:1, valor_unitario:"" };

export default function PlanoDeTratamento({ pacienteId, token, itemInicial, onConsumirItemInicial }) {
    const [planos, setPlanos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [mostrarForm, setMostrarForm] = useState(false);
    const [titulo, setTitulo] = useState("Plano de Tratamento");
    const [observacoes, setObservacoes] = useState("");
    const [itens, setItens] = useState([{ ...ITEM_VAZIO }]);
    const [salvando, setSalvando] = useState(false);
    const [erro, setErro] = useState(null);
    const formRef = useRef(null);

    useEffect(() => {
        if (!pacienteId) { setLoading(false); return; }
        apiGetPlanos(token, pacienteId)
            .then(setPlanos)
            .catch(e => setErro(e.message))
            .finally(() => setLoading(false));
    }, [pacienteId, token]);

    // Quando o dentista clicou "+ Adicionar ao Plano" no odontograma, abrimos o
    // formulário já com o procedimento e o dente preenchidos. Se já estiver
    // aberto, apenas adiciona uma linha nova.
    useEffect(() => {
        if (!itemInicial) return;
        const novoItem = {
            procedimento: itemInicial.procedimento || "",
            dente: itemInicial.dente || "",
            quantidade: 1,
            valor_unitario: "",
        };
        if (mostrarForm) {
            setItens(prev => {
                // Se a primeira linha estiver vazia, substitui; senão, adiciona ao fim.
                const primeira = prev[0];
                const primeiraVazia = primeira && !primeira.procedimento && !primeira.dente;
                if (primeiraVazia) return [novoItem, ...prev.slice(1)];
                return [...prev, novoItem];
            });
        } else {
            setMostrarForm(true);
            setItens([novoItem]);
        }
        setTimeout(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
        onConsumirItemInicial && onConsumirItemInicial();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [itemInicial]);

    const totalOrcamento = itens.reduce((s, i) => s + (Number(i.quantidade)||1) * (Number(i.valor_unitario)||0), 0);

    function addItem() { setItens(p => [...p, { ...ITEM_VAZIO }]); }
    function removeItem(idx) { setItens(p => p.filter((_,i) => i !== idx)); }
    function updateItem(idx, field, val) { setItens(p => p.map((it, i) => i===idx ? {...it, [field]: val} : it)); }

    async function handleCriar(e) {
        e.preventDefault();
        setSalvando(true); setErro(null);
        try {
            const novo = await apiCriarPlano(token, { paciente_id: pacienteId, titulo, observacoes, itens });
            setPlanos(p => [novo, ...p]);
            setMostrarForm(false);
            setTitulo("Plano de Tratamento"); setObservacoes(""); setItens([{ ...ITEM_VAZIO }]);
        } catch(e) { setErro(e.message); }
        finally { setSalvando(false); }
    }

    async function toggleItem(planoId, itemId, statusAtual) {
        const novoStatus = statusAtual === "Pendente" ? "Concluido" : "Pendente";
        try {
            await apiAtualizarPlanoItem(token, planoId, itemId, { status: novoStatus });
            setPlanos(ps => ps.map(p => p.id !== planoId ? p : { ...p, itens: p.itens.map(it => it.id === itemId ? {...it, status: novoStatus} : it) }));
        } catch(e) { console.warn(e); }
    }

    if (loading) return <p style={{color:"var(--TextColor75)",fontSize:"14px"}}>Carregando planos...</p>;

    return (
        <div style={{display:"flex",flexDirection:"column",gap:"1.5rem"}}>
            <div style={{display:"flex",justifyContent:"flex-end"}}>
                <button onClick={() => setMostrarForm(v=>!v)} style={{display:"flex",alignItems:"center",gap:"6px",padding:"10px 20px",background:mostrarForm?"transparent":"var(--PrimaryColorsTheme)",color:mostrarForm?"var(--TextColor75)":"white",border:mostrarForm?"1px solid var(--LineColor)":"none",borderRadius:"var(--radius-md)",fontWeight:700,fontSize:"14px",cursor:"pointer"}}>
                    {mostrarForm ? <><X size={16} strokeWidth={2.5} /> Cancelar</> : <><Plus size={16} strokeWidth={2.5} /> Novo Plano de Tratamento</>}
                </button>
            </div>

            {mostrarForm && (
                <form ref={formRef} onSubmit={handleCriar} style={{background:"var(--ThemeColor)",border:"1px solid var(--LineColor)",borderRadius:"var(--radius-lg)",padding:"1.5rem",display:"flex",flexDirection:"column",gap:"1rem"}}>
                    <h4 style={{margin:0,color:"var(--PrimaryColorsTheme)"}}>Novo Plano / Orçamento</h4>
                    {erro && <div style={{background:"var(--DangerBack)",color:"var(--DangerText)",padding:"10px 14px",borderRadius:"var(--radius-sm)",fontSize:"14px"}}>{erro}</div>}

                    <input value={titulo} onChange={e=>setTitulo(e.target.value)} placeholder="Título do plano" required style={{padding:"10px 12px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"14px"}} />
                    <textarea value={observacoes} onChange={e=>setObservacoes(e.target.value)} rows={2} placeholder="Observações gerais..." style={{padding:"10px 12px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"14px",fontFamily:"inherit",resize:"vertical"}} />

                    <div>
                        <p style={{margin:"0 0 8px 0",fontWeight:700,fontSize:"13px",color:"var(--TextColor75)"}}>Procedimentos</p>
                        {itens.map((it, idx) => (
                            <div key={idx} style={{display:"grid",gridTemplateColumns:"2fr 1fr 80px 120px 36px",gap:"8px",marginBottom:"8px",alignItems:"center"}}>
                                <input value={it.procedimento} onChange={e=>updateItem(idx,"procedimento",e.target.value)} placeholder="Procedimento" required style={{padding:"8px 10px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"13px"}} />
                                <input value={it.dente} onChange={e=>updateItem(idx,"dente",e.target.value)} placeholder="Dente (ex: 36)" style={{padding:"8px 10px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"13px"}} />
                                <input type="number" min="1" value={it.quantidade} onChange={e=>updateItem(idx,"quantidade",e.target.value)} placeholder="Qtd" style={{padding:"8px 10px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"13px"}} />
                                <input type="number" min="0" step="0.01" value={it.valor_unitario} onChange={e=>updateItem(idx,"valor_unitario",e.target.value)} placeholder="R$ Valor" style={{padding:"8px 10px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"13px"}} />
                                <button type="button" aria-label="Remover item" onClick={()=>removeItem(idx)} style={{background:"var(--DangerBack)",color:"var(--DangerText)",border:"none",borderRadius:"var(--radius-sm)",width:"36px",height:"36px",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center"}}><X size={16} strokeWidth={2.5} /></button>
                            </div>
                        ))}
                        <button type="button" onClick={addItem} style={{display:"flex",alignItems:"center",gap:"6px",fontSize:"13px",color:"var(--PrimaryColorsTheme)",background:"none",border:"1px dashed var(--PrimaryColorsTheme)",borderRadius:"var(--radius-sm)",padding:"8px 14px",cursor:"pointer",fontWeight:600}}><Plus size={16} strokeWidth={2.5} /> Adicionar item</button>
                    </div>

                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",paddingTop:"0.5rem",borderTop:"1px solid var(--LineColor)"}}>
                        <p style={{margin:0,fontWeight:700,fontSize:"16px"}}>Total: <span style={{color:"var(--PrimaryColorsTheme)"}}>{formatCurrency(totalOrcamento)}</span></p>
                        <button type="submit" disabled={salvando} style={{padding:"10px 24px",background:"var(--PrimaryColorsTheme)",color:"white",border:"none",borderRadius:"var(--radius-sm)",fontWeight:700,opacity:salvando?0.7:1,cursor:salvando?"not-allowed":"pointer"}}>
                            {salvando ? "Salvando..." : "Salvar Plano"}
                        </button>
                    </div>
                </form>
            )}

            {planos.length === 0 && !mostrarForm && <p style={{fontSize:"14px",color:"var(--TextColor75)",fontStyle:"italic"}}>Nenhum plano de tratamento cadastrado.</p>}

            {planos.map(plano => {
                const concluidos = plano.itens?.filter(i=>i.status==="Concluido").length || 0;
                const total = plano.itens?.length || 0;
                const cor = STATUS_PLANO[plano.status] || "var(--TextColor75)";
                return (
                    <div key={plano.id} style={{background:"var(--ThemeColor)",border:"1px solid var(--LineColor)",borderRadius:"var(--radius-md)",padding:"1.25rem",boxShadow:"var(--shadow-sm)"}}>
                        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:"1rem"}}>
                            <div>
                                <h4 style={{margin:"0 0 4px 0",fontSize:"16px",fontWeight:700}}>{plano.titulo}</h4>
                                <p style={{margin:0,fontSize:"13px",color:"var(--TextColor75)"}}>
                                    {concluidos}/{total} procedimentos concluídos · Total: <strong>{formatCurrency(plano.valor_total)}</strong>
                                </p>
                            </div>
                            <span style={{background:cor+"1A",color:cor,padding:"4px 12px",borderRadius:"999px",fontSize:"12px",fontWeight:700}}>{plano.status}</span>
                        </div>

                        {total > 0 && (
                            <div style={{background:"var(--LineColor)",borderRadius:"999px",height:"6px",marginBottom:"1rem"}}>
                                <div style={{width:`${total?Math.round((concluidos/total)*100):0}%`,height:"100%",background:"var(--SuccessText)",borderRadius:"999px",transition:"width 0.3s"}} />
                            </div>
                        )}

                        <div style={{display:"flex",flexDirection:"column",gap:"6px"}}>
                            {plano.itens?.map(item => {
                                const corItem = STATUS_ITEM[item.status] || "var(--TextColor75)";
                                return (
                                    <div key={item.id} style={{display:"flex",alignItems:"center",gap:"10px",padding:"8px 12px",background:"var(--BackColor)",borderRadius:"var(--radius-sm)"}}>
                                        <div onClick={()=>toggleItem(plano.id, item.id, item.status)} style={{width:"18px",height:"18px",borderRadius:"4px",border:`2px solid ${corItem}`,background:item.status==="Concluido"?corItem:"transparent",cursor:"pointer",flexShrink:0}} />
                                        <div style={{flex:1}}>
                                            <span style={{fontSize:"14px",fontWeight:500,textDecoration:item.status==="Concluido"?"line-through":"none",color:item.status==="Concluido"?"var(--TextColor75)":"var(--TextColor)"}}>{item.procedimento}</span>
                                            {item.dente && <span style={{fontSize:"12px",color:"var(--TextColor75)",marginLeft:"8px"}}>Dente {item.dente}</span>}
                                        </div>
                                        <span style={{fontSize:"13px",fontWeight:700,color:"var(--TextColor75)",whiteSpace:"nowrap"}}>{item.quantidade > 1 ? `${item.quantidade}× ` : ""}{formatCurrency(item.valor_unitario)}</span>
                                    </div>
                                );
                            })}
                        </div>

                        {plano.observacoes && <p style={{margin:"1rem 0 0 0",fontSize:"13px",color:"var(--TextColor75)",fontStyle:"italic"}}>{plano.observacoes}</p>}
                    </div>
                );
            })}
        </div>
    );
}
