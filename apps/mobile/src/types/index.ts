// ============================================================
// MediScan AI — Global Type Definitions
// ============================================================

// ── Auth ──────────────────────────────────────────────────────
export interface User {
  id: string;
  fullName: string;
  email: string;
  gender?: string;
  dateOfBirth?: string;
  weightKg?: number;
  heightCm?: number;
  bloodGroup?: string;
  role: 'User' | 'Doctor' | 'Admin';
  createdAt: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ── Scan ──────────────────────────────────────────────────────
export type ScanType =
  | 'Anemia'
  | 'SkinDisease'
  | 'Posture'
  | 'EyeDisease'
  | 'Wound'
  | 'TongueDiagnosis';

export type ScanStatus = 'Pending' | 'Processing' | 'Completed' | 'Failed';

export interface ScanResult {
  id: string;
  scanType: ScanType;
  status: ScanStatus;
  imageUrl?: string;
  detectionResult?: string;
  confidenceScore?: number;
  detectionDetails?: string;       // JSON string
  aiRecommendation?: string;
  nextScanRecommendation?: string;
  nextScanDate?: string;
  createdAt: string;
  completedAt?: string;
}

export interface ScanHistory {
  scans: ScanResult[];
  totalCount: number;
  page: number;
  pageSize: number;
}

// ── Medication ────────────────────────────────────────────────
export type MedicationInputMethod = 'BarcodeScanner' | 'OcrScan' | 'ManualEntry';

export interface MedicationRecord {
  id: string;
  drugName: string;
  genericName?: string;
  manufacturer?: string;
  barcode?: string;
  dosageForm?: string;
  strength?: string;
  indication?: string;
  sideEffects?: string;
  warnings?: string;
  drugInteractions?: string;
  aiAnalysis?: string;
  imageUrl?: string;
  inputMethod: MedicationInputMethod;
  isPrescription: boolean;
  prescribedBy?: string;
  prescribedDate?: string;
  createdAt: string;
}

// ── API ───────────────────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data?: T;
  errors: string[];
}

// ── Navigation ────────────────────────────────────────────────
export interface ScanModuleInfo {
  id: ScanType;
  title: string;
  description: string;
  icon: string;
  color: string;
  instructions: string;
  targetArea: string;
}

export const SCAN_MODULES: ScanModuleInfo[] = [
  {
    id: 'Anemia',
    title: 'Anemia Detection',
    description: 'Detect anemia via eye or nail pallor',
    icon: '🩸',
    color: '#EF4444',
    instructions: 'Pull down lower eyelid gently and point camera at inner eyelid.',
    targetArea: 'Lower eyelid or fingernail',
  },
  {
    id: 'SkinDisease',
    title: 'Skin Disease',
    description: 'Detect eczema, fungal, acne & more',
    icon: '🦠',
    color: '#F59E0B',
    instructions: 'Point camera directly at the affected skin area. Ensure good lighting.',
    targetArea: 'Affected skin area',
  },
  {
    id: 'Posture',
    title: 'Posture & Scoliosis',
    description: 'Analyze spine & body alignment',
    icon: '🦴',
    color: '#8B5CF6',
    instructions: 'Stand 2-3 meters away, full body visible in frame. Face camera or stand sideways.',
    targetArea: 'Full body (front or side view)',
  },
  {
    id: 'EyeDisease',
    title: 'Eye Disease',
    description: 'Detect cataract, jaundice, red eye',
    icon: '👁️',
    color: '#3B82F6',
    instructions: 'Open eye wide, camera ~20cm away. Use natural lighting.',
    targetArea: 'Eye (front-facing)',
  },
  {
    id: 'Wound',
    title: 'Wound Measurement',
    description: 'Measure wound size & healing stage',
    icon: '🩹',
    color: '#10B981',
    instructions: 'Place a 2.5cm coin next to wound for size reference. Capture clearly.',
    targetArea: 'Wound / affected area',
  },
  {
    id: 'TongueDiagnosis',
    title: 'Tongue Diagnosis',
    description: 'Detect deficiencies & infections',
    icon: '👅',
    color: '#EC4899',
    instructions: 'Extend tongue fully, use natural lighting, camera 15-20cm away.',
    targetArea: 'Extended tongue',
  },
];
