import { createContext, useContext } from "react";

/* Contexto do FeedbackProvider (components/feedback/Feedback.jsx).
   useFeedback() devolve { toast, confirmar }. */
export const FeedbackContext = createContext(null);

export function useFeedback() {
    return useContext(FeedbackContext);
}
