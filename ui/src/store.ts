import { create } from "zustand";

interface TokenState {
  token: string;
  setToken: (token: string) => void;
  removeToken: () => void;
}

export const useTokenStore = create<TokenState>((set) => ({
  token: "",
  setToken: (token: string) => set({ token: token }),
  removeToken: () => set({ token: "" }),
}));
