/* IMPORTS OF COMPONENTS */
import { useNavigate } from "react-router-dom";
import '../../styles/Buttons.css'

/* MAIN COMPONENT
   `icon` é um componente de ícone do lucide-react (ver useSidebar.js). */
function ButtonsCamps({ icon: Icon, name, style, url, onNavigate }) {
    const navigate = useNavigate();

    function registration() {
        onNavigate?.();
        navigate(`${url}`);
    }

    return (
        <button className={`bar ${style}`} onClick={registration}>
            {Icon && (
                <span className="bar-icon">
                    <Icon size={20} strokeWidth={2} />
                </span>
            )}
            <p>{name}</p>
        </button>
    );

}

/* STANDARD EXPORT */
export default ButtonsCamps;
