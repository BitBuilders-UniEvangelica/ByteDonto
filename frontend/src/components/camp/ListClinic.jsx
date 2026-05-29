/* IMPORTS OF COMPONENTS */
import { Link } from "react-router-dom";
import { formatCNPJ, formatPhone } from "../../utils/formatters";
import { CheckCircle2 } from "lucide-react";
import '../../styles/List.css'

/* MAIN COMPONENT */
function ListClinic({ clinic_id, clinic_logo, clinic_img, clinic_name, clinic_cnpj, clinic_phone, is_active, ativando, onAtivar }) {
    return (
        <div className="list" style={{ display: 'flex', alignItems: 'center', gap: '1rem', border: is_active ? '1px solid var(--PrimaryColors)' : undefined }}>
            <Link to={`/owner/view-clinic/${clinic_id}`} style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1, textDecoration: 'none', color: 'inherit' }}>
                <div className='circle'>
                    <img src={clinic_logo ? clinic_logo : clinic_img} alt={`Logotipo da clínica ${clinic_name}`} />
                </div>
                <div>
                    <p>{clinic_name}</p>
                    <p>{formatCNPJ(clinic_cnpj)} | {formatPhone(clinic_phone)}</p>
                </div>
            </Link>

            {is_active ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', padding: '6px 14px', borderRadius: '999px', fontSize: '13px', fontWeight: 700, whiteSpace: 'nowrap' }}>
                    <CheckCircle2 size={15} strokeWidth={2.4} /> Clínica ativa
                </span>
            ) : (
                <button
                    onClick={() => onAtivar && onAtivar(clinic_id)}
                    disabled={ativando}
                    style={{ background: 'var(--ThemeColor)', color: 'var(--PrimaryColorsTheme)', border: '1px solid var(--LineColor)', padding: '8px 16px', borderRadius: '999px', fontSize: '13px', fontWeight: 700, cursor: ativando ? 'default' : 'pointer', opacity: ativando ? 0.6 : 1, whiteSpace: 'nowrap' }}
                >
                    {ativando ? 'Trocando...' : 'Tornar ativa'}
                </button>
            )}
        </div>
    );
}

export default ListClinic;
