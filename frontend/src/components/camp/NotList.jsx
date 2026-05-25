/* IMPORTS OF COMPONENTS */
import ButtonP from "../buttons/ButtonsRediText"
import '../../styles/List.css'

/* MAIN COMPONENT */
function NotList({ img, text_p, text_l, text_btn, utl_btn }) {
    return (
        <>
            <div className="not-list">
                <img src={img} alt="" />
                <p>{text_p}</p>
                <label>{text_l}</label>
                <ButtonP text={text_btn} url={utl_btn} />
            </div>
        </>
    );

}

/* STANDARD EXPORT */
export default NotList;