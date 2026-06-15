import { useState, useEffect } from "react";
import { apiGetImagens, apiUploadImagem, apiDeletarImagem } from "../../services/api";
import { ImagePlus, Trash2, Image as ImageIcon } from "lucide-react";

export default function GaleriaImagens({ pacienteId, token }) {
    const [imagens, setImagens] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [erro, setErro] = useState(null);

    useEffect(() => {
        if (!pacienteId) { setLoading(false); return; }
        apiGetImagens(token, pacienteId)
            .then(setImagens)
            .catch(() => setImagens([]))
            .finally(() => setLoading(false));
    }, [pacienteId, token]);

    async function handleUpload(e) {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true); setErro(null);
        try {
            const nova = await apiUploadImagem(token, pacienteId, file);
            setImagens(p => [nova, ...p]);
        } catch(e) { setErro(e.message); }
        finally { setUploading(false); e.target.value = ""; }
    }

    async function handleDeletar(id) {
        if (!confirm("Remover imagem?")) return;
        try {
            await apiDeletarImagem(token, id);
            setImagens(p => p.filter(i => i.id !== id));
        } catch(e) { setErro(e.message); }
    }

    return (
        <div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"1.5rem"}}>
                <div>
                    <h3 style={{margin:"0 0 4px 0",color:"var(--PrimaryColorsTheme)"}}>Imagens e Raio-X</h3>
                    <p style={{margin:0,fontSize:"13px",color:"var(--TextColor75)"}}>Radiografias, fotos clínicas e documentações do paciente.</p>
                </div>
                <label style={{display:"flex",alignItems:"center",gap:"8px",padding:"10px 20px",background:"var(--PrimaryColorsTheme)",color:"white",borderRadius:"var(--radius-md)",fontWeight:700,fontSize:"14px",cursor:"pointer"}}>
                    <ImagePlus size={18} strokeWidth={2.5} /> {uploading ? "Enviando..." : "Adicionar Imagem"}
                    <input type="file" accept="image/*,.pdf" onChange={handleUpload} style={{display:"none"}} disabled={uploading} />
                </label>
            </div>

            {erro && <div style={{background:"var(--DangerBack)",color:"var(--DangerText)",padding:"10px 14px",borderRadius:"var(--radius-sm)",fontSize:"14px",marginBottom:"1rem"}}>{erro}</div>}

            {loading ? <p style={{color:"var(--TextColor75)",fontSize:"14px"}}>Carregando...</p> :
             imagens.length === 0 ? (
                <div style={{border:"1px dashed var(--LineColor)",borderRadius:"var(--radius-lg)",padding:"3rem",textAlign:"center",color:"var(--TextColor75)"}}>
                    <ImageIcon size={40} strokeWidth={1.5} style={{margin:"0 auto 12px",display:"block",color:"var(--TextColor75)"}} />
                    <p style={{fontSize:"16px",fontWeight:600,margin:"0 0 8px 0"}}>Nenhuma imagem adicionada</p>
                    <p style={{fontSize:"14px",margin:0}}>Adicione radiografias, fotos intraorais ou documentos.</p>
                </div>
             ) : (
                <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))",gap:"1rem"}}>
                    {imagens.map(img => (
                        <div key={img.id} style={{border:"1px solid var(--LineColor)",borderRadius:"var(--radius-md)",overflow:"hidden",position:"relative",background:"var(--ThemeColor)",boxShadow:"var(--shadow-sm)"}}>
                            <img src={img.url} alt={img.nome} style={{width:"100%",height:"140px",objectFit:"cover",display:"block"}} onError={e=>{e.target.style.display="none"}} />
                            <div style={{padding:"8px 10px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                                <p style={{margin:0,fontSize:"12px",fontWeight:600,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:"120px"}}>{img.nome}</p>
                                <button aria-label="Excluir imagem" onClick={()=>handleDeletar(img.id)} style={{background:"var(--DangerBack)",color:"var(--DangerText)",border:"none",borderRadius:"var(--radius-sm)",padding:"5px",cursor:"pointer",flexShrink:0,display:"flex",alignItems:"center"}}><Trash2 size={14} strokeWidth={2} /></button>
                            </div>
                        </div>
                    ))}
                </div>
             )}
        </div>
    );
}
