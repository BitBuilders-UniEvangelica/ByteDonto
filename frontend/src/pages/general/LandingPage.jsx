/* IMPORTS OF COMPONENTS */
import Section from "../../components/section/SectionNotAuth";
import Button from "../../components/buttons/ButtonsRediBorder";
import Footer from "../../components/footer/FooterNotAuth";
import '../../styles/LandingPage.css'


/* MAIN COMPONENT */
function LandingPage() {

    return (
        <div className="landing-wrapper">
            <Section />
            <main className="hero-section">
                <div className="hero-content">
                    <div className="badge-mono">
                        <span className="data-mono">STATUS DO SISTEMA: READY 01011001</span>
                    </div>
                    
                    <h1 className="display">
                        Gestão <span className="highlight-owner">Inteligente</span> para<br/>Clínicas Contemporâneas
                    </h1>
                    
                    <p className="body-text">
                        O design é onde a ciência e a arte se encontram em harmonia para o bem-estar do paciente. A IA do Byte-Donto analisa padrões de agendamento para reduzir as faltas na clínica em até 35%.
                    </p>

                    <div className="cta-container">
                        <Button text={"Vamos Começar"} url="/cadastro" />
                        <button className="secondary-button data-mono">VER FUNCIONALIDADES</button>
                    </div>
                </div>
                
                <div className="hero-mockup-wrapper">
                    <div className="glass-mockup">
                        <div className="mockup-header">
                            <span className="dot red"></span>
                            <span className="dot yellow"></span>
                            <span className="dot green"></span>
                        </div>
                        <div className="mockup-body">
                            <div className="mockup-sidebar"></div>
                            <div className="mockup-content">
                                <div className="mockup-card line-1"></div>
                                <div className="mockup-card skeleton line-2"></div>
                                <div className="mockup-card skeleton line-3"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}

/* STANDARD EXPORT */
export default LandingPage;