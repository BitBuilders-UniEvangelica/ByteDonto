/* IMPORTS OF COMPONENTS */
import ButtonsCamps from "../buttons/ButtonsCamps";
import ToothIcon from "../icons/ToothIcon";
import '../../styles/Section.css'

/* MAIN COMPONENT */
function SectionNotAuth() {
    return (
        <>
            <section>
                <h1 id="logo">
                    <span className="brand-mark">
                        <ToothIcon size={22} />
                    </span>
                    BYTE DONTO
                </h1>
                <div>
                    <ButtonsCamps type={"LOGIN"} url="/login" />
                    <div className="out">
                        <ButtonsCamps type={"CADASTRO"} url="/cadastro" />
                    </div>
                </div>
            </section>
        </>
    );
}

/* STANDARD EXPORT */
export default SectionNotAuth;