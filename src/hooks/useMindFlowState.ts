import { useState, useEffect } from "react";
import { AppState } from "../types";
import { getState, subscribe } from "../state/store";

/**
 * Subscribe to MindFlow state changes.
 * Re-renders when state updates.
 */
export function useMindFlowState(): AppState {
    const [state, setState] = useState<AppState>(getState);

    useEffect(() => {
        return subscribe(() => {
            setState(getState());
        });
    }, []);

    return state;
}