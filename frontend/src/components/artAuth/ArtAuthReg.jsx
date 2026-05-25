import '../../styles/ArtAuth.css';

/* MAIN COMPONENT */
function ArtAuthReg({ type, img }) {
    return (
        <div className={`art ${type} dir-right`}>
            <span>
                BYTE DONTO
            </span>

            <img src={img} alt="" />
        </div>
    );
}

/* STANDARD EXPORT */
export default ArtAuthReg;