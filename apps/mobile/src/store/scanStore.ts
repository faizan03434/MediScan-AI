import { create } from 'zustand';
import type { ScanResult, ScanType } from '../types';
import scanService from '../services/scanService';
import { onSessionCleared, sessionVersion } from '../services/sessionEvents';

interface ScanState {
  recentScans: ScanResult[];
  currentScan: ScanResult | null;
  isScanning: boolean;
  error: string | null;
}

interface ScanActions {
  submitScan: (scanType: ScanType, imageUri: string) => Promise<ScanResult>;
  setCurrentScan: (scan: ScanResult | null) => void;
  loadRecentScans: () => Promise<void>;
  clearError: () => void;
}

const useScanStore = create<ScanState & ScanActions>((set) => ({
  recentScans: [],
  currentScan: null,
  isScanning: false,
  error: null,

  submitScan: async (scanType, imageUri) => {
    const revision = sessionVersion();
    set({ isScanning: true, error: null });
    try {
      const result = await scanService.createScan(scanType, imageUri);
      if (revision !== sessionVersion()) throw new Error('Session changed. Open the scan again after signing in.');
      set((state) => ({
        recentScans: [result, ...state.recentScans.slice(0, 9)],
        currentScan: result,
        isScanning: false,
      }));
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Scan failed.';
      if (revision === sessionVersion()) set({ isScanning: false, error: message });
      throw err;
    }
  },

  setCurrentScan: (scan) => set({ currentScan: scan }),

  loadRecentScans: async () => {
    const revision = sessionVersion();
    try {
      const scans = await scanService.getRecentScans(5);
      if (revision === sessionVersion()) set({ recentScans: scans });
    } catch {
      // Fail silently — not critical
    }
  },

  clearError: () => set({ error: null }),
}));

onSessionCleared(() => useScanStore.setState({ recentScans: [], currentScan: null, isScanning: false, error: null }));

export default useScanStore;
