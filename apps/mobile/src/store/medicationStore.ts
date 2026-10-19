import { create } from 'zustand';
import { errorMessage } from '../utils/errorMessage';
import { onSessionCleared, sessionVersion } from '../services/sessionEvents';
import medicationService, {
  type DrugInfo,
  type MedicationRecord,
  type PrescriptionAnalysis,
} from '../services/medicationService';

interface MedicationState {
  currentDrug: DrugInfo | null;
  history: MedicationRecord[];
  currentPrescription: PrescriptionAnalysis | null;
  isLoading: boolean;
  error: string | null;
}

interface MedicationActions {
  searchByName: (query: string) => Promise<DrugInfo>;
  searchByBarcode: (barcode: string) => Promise<DrugInfo>;
  analyzePrescription: (
    imageUri: string,
    doctorName?: string,
    notes?: string,
  ) => Promise<PrescriptionAnalysis>;
  loadHistory: () => Promise<void>;
  clearCurrent: () => void;
  clearError: () => void;
}

const useMedicationStore = create<MedicationState & MedicationActions>((set) => ({
  currentDrug: null,
  history: [],
  currentPrescription: null,
  isLoading: false,
  error: null,

  searchByName: async (query) => {
    const revision = sessionVersion();
    set({ isLoading: true, error: null });
    try {
      const result = await medicationService.searchByName(query);
      if (revision !== sessionVersion()) throw new Error('Session changed. Search again after signing in.');
      set({ currentDrug: result, isLoading: false });
      return result;
    } catch (err: unknown) {
      const msg = errorMessage(err);
      if (revision === sessionVersion()) set({ isLoading: false, error: msg });
      throw err;
    }
  },

  searchByBarcode: async (barcode) => {
    const revision = sessionVersion();
    set({ isLoading: true, error: null });
    try {
      const result = await medicationService.searchByBarcode(barcode);
      if (revision !== sessionVersion()) throw new Error('Session changed. Search again after signing in.');
      set({ currentDrug: result, isLoading: false });
      return result;
    } catch (err: unknown) {
      const msg = errorMessage(err);
      if (revision === sessionVersion()) set({ isLoading: false, error: msg });
      throw err;
    }
  },

  analyzePrescription: async (imageUri, doctorName, notes) => {
    const revision = sessionVersion();
    set({ isLoading: true, error: null });
    try {
      const result = await medicationService.analyzePrescription(imageUri, doctorName, notes);
      if (revision !== sessionVersion()) throw new Error('Session changed. Open the prescription again after signing in.');
      set({ currentPrescription: result, isLoading: false });
      return result;
    } catch (err: unknown) {
      const msg = errorMessage(err);
      if (revision === sessionVersion()) set({ isLoading: false, error: msg });
      throw err;
    }
  },

  loadHistory: async () => {
    const revision = sessionVersion();
    try {
      const result = await medicationService.getHistory();
      if (revision === sessionVersion()) set({ history: result.items });
    } catch { /* silent fail */ }
  },

  clearCurrent: () => set({ currentDrug: null, currentPrescription: null }),
  clearError: () => set({ error: null }),
}));

onSessionCleared(() => useMedicationStore.setState({
  currentDrug: null, history: [], currentPrescription: null, isLoading: false, error: null,
}));

export default useMedicationStore;
