import { create } from 'zustand';

/**
 * User / authentication state store.
 *
 * Keeps track of the current user object and whether the session
 * is authenticated.
 */
const useUserStore = create((set) => ({
  // ---- state ----
  user: null,
  isAuthenticated: false,

  // ---- actions ----

  /** Directly replace the user object (null clears it). */
  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
    }),

  /**
   * Log in by providing user data.
   * Sets the user and flips isAuthenticated to true.
   */
  login: (userData) =>
    set({
      user: userData,
      isAuthenticated: true,
    }),

  /**
   * Log out.
   * Clears the user and sets isAuthenticated to false.
   */
  logout: () =>
    set({
      user: null,
      isAuthenticated: false,
    }),
}));

export { useUserStore };
export default useUserStore;
