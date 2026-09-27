import { create } from 'zustand';
import type { ScanResult, ScanType } from '../types';
import scanService from '../services/scanService';

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
    set({ isScanning: true, error: null });
    try {
      const result = await scanService.createScan(scanType, imageUri);
      set((state) => ({
        recentScans: [result, ...state.recentScans.slice(0, 9)],
        currentScan: result,
        isScanning: false,
      }));
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Scan failed.';
      set({ isScanning: false, error: message });
      throw err;
    }
  },

  setCurrentScan: (scan) => set({ currentScan: scan }),

  loadRecentScans: async () => {
    try {
      const scans = await scanService.getRecentScans(5);
      set({ recentScans: scans });
    } catch {
      // Fail silently — not critical
    }
  },

  clearError: () => set({ error: null }),
}));

export default useScanStore;
