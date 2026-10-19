// Keep transport independent of the auth store, avoiding a circular import.
const listeners = new Set<() => void>();
let revision = 0;
export const sessionVersion = () => revision;
export const onSessionCleared = (listener: () => void) => {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
};
export const notifySessionCleared = () => {
  ++revision;
  listeners.forEach((listener) => listener());
};
