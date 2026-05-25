import ToothIcon from '../icons/ToothIcon'
import '../../styles/Footer.css'

function FooterAuth({ type_styles, text }) {
    const lines = text.split("\n");

    return (
        <>
            <footer className={`${type_styles} auth`}>
                <h1 id="logo">
                    <span className="brand-mark">
                        <ToothIcon size={22} />
                    </span>
                    BYTE DONTO
                </h1>
                <div className='medio'>
                    <div className='frases'>
                        {lines.map((line, i) => (
                            <p key={i}>
                                {line}
                                <br />
                            </p>
                        ))}
                    </div>
                    <div>
                        <p id='title'>Navegue</p>
                        <p>Termos de Uso e Política de Privacidade</p>
                        <p>Política de Privacidade</p>
                    </div>
                    <div>
                        <p id='title'>Entre em contato</p>
                        <p>+55 (66) XXXX-XXXX</p>
                    </div>
                </div>
                <div className='bottom text75'>
                    <label>BYTE DONTO SERVICOS EM GESTÃO E SAUDE LTDA | CNPJ: XX.XXX.XXX/XXXX-XX</label>
                    <label>label© 2025 ByteDonto - Todos os direitos reservados</label>
                </div>
            </footer>
        </>
    );
}

/* STANDARD EXPORT */
export default FooterAuth;