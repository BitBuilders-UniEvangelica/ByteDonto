/* ToothIcon — ícone de dente para os pontos de marca odontológica.
   A biblioteca lucide-react não possui um ícone de dente, então este
   componente fornece um SVG simples e limpo de contorno.

   Uso:
     import ToothIcon from "../icons/ToothIcon";
     <ToothIcon size={20} color="#0E7490" />
*/
function ToothIcon({ size = 24, color = "currentColor", strokeWidth = 1.8, ...props }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            {...props}
        >
            <path d="M12 5.5c-1.6-1.6-3.4-2.5-5-2.5C4.5 3 3 5 3 8c0 2 .6 3.6 1.2 5.7.5 1.8.7 4 1.1 5.6.3 1.3.9 2.2 1.8 2.2 1.1 0 1.5-1.2 1.8-2.8.3-1.7.6-3.4 1.4-3.4l1.4 0c.8 0 1.1 1.7 1.4 3.4.3 1.6.7 2.8 1.8 2.8.9 0 1.5-.9 1.8-2.2.4-1.6.6-3.8 1.1-5.6C20.4 11.6 21 10 21 8c0-3-1.5-5-4-5-1.6 0-3.4.9-5 2.5Z" />
        </svg>
    );
}

export default ToothIcon;
