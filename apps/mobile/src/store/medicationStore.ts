import { create } from 'zustand';
import { errorMessage } from '../utils/errorMessage';
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
    set({ isLoading: true, error: null });
    try {
      const result = await medicationService.searchByName(query);
      set({ currentDrug: result, isLoading: false });
      return result;
    } catch (err: unknown) {
      const msg = errorMessage(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  searchByBarcode: async (barcode) => {
    set({ isLoading: true, error: null });
    try {
      const result = await medicationService.searchByBarcode(barcode);
      set({ currentDrug: result, isLoading: false });
      return result;
    } catch (err: unknown) {
      const msg = errorMessage(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  analyzePrescription: async (imageUri, doctorName, notes) => {
    set({ isLoading: true, error: null });
    try {
      const result = await medicationService.analyzePrescription(imageUri, doctorName, notes);
      set({ currentPrescription: result, isLoading: false });
      return result;
    } catch (err: unknown) {
      const msg = errorMessage(err);
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  loadHistory: async () => {
    try {
      const result = await medicationService.getHistory();
      set({ history: result.items });
    } catch { /* silent fail */ }
  },

  clearCurrent: () => set({ currentDrug: null, currentPrescription: null }),
  clearError: () => set({ error: null }),
}));

export default useMedicationStore;
