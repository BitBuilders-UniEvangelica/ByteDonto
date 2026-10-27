/* IMPORTS OF COMPONENTS */
import { useState, useEffect } from 'react'
import { PanelLeftOpen, X } from 'lucide-react'
import '../../styles/Bar.css'
import ButtonsCamps from '../buttons/ButtonsSadeBar'

// Mesmo breakpoint do Bar.css: abaixo dele a barra lateral fica escondida
// e passa a abrir como gaveta pelo botão flutuante.
const MEDIA_GAVETA = '(max-width: 768px)'

/* MAIN COMPONENT */
function SideBar({ opc, styles }) {
    const [aberta, setAberta] = useState(false)

    function fechar() {
        setAberta(false)
    }

    // Fecha com Esc e quando a tela volta a ter espaço para a barra fixa.
    useEffect(() => {
        if (!aberta) return
        const media = window.matchMedia(MEDIA_GAVETA)
        const aoTeclar = (e) => { if (e.key === 'Escape') fechar() }
        const aoMudarTela = (e) => { if (!e.matches) fechar() }
        window.addEventListener('keydown', aoTeclar)
        media.addEventListener('change', aoMudarTela)
        return () => {
            window.removeEventListener('keydown', aoTeclar)
            media.removeEventListener('change', aoMudarTela)
        }
    }, [aberta])

    return (
        <>
            {!aberta && (
                <button
                    type="button"
                    className="sidebar-toggle"
                    onClick={() => setAberta(true)}
                    aria-label="Abrir menu de navegação"
                    title="Abrir menu de navegação"
                >
                    <PanelLeftOpen size={20} strokeWidth={2} />
                </button>
            )}

            {aberta && <div className="sidebar-overlay" onClick={fechar} aria-hidden="true" />}

            <div className={`sidebar ${styles} ${aberta ? 'open' : ''}`}>
                <button
                    type="button"
                    className="sidebar-close"
                    onClick={fechar}
                    aria-label="Fechar menu de navegação"
                    title="Fechar menu de navegação"
                >
                    <X size={20} strokeWidth={2} />
                </button>
                {opc.map((op) => (
                    <ButtonsCamps
                        key={op.id}
                        icon={op.icon}
                        name={op.name}
                        style={op.style}
                        url={op.url}
                        onNavigate={fechar}
                    />
                ))}
            </div>
        </>
    );

}

/* STANDARD EXPORT */
export default SideBar;
