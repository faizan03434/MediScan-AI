// ============================================================
// MediScan AI — Global Type Definitions
// ============================================================
import { Colors } from '../theme/colors';

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
  | 'TongueDiagnosis'
  | 'Retina';

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
  captureMode?: 'upload_only';
}

export const SCAN_MODULES: ScanModuleInfo[] = [
  {
    id: 'Retina',
    title: 'Retina / Fundus',
    description: 'Upload a retinal camera photo for private history and clinician review',
    icon: '🔬',
    color: Colors.eye,
    instructions: 'Choose a fundus photograph captured by a retinal camera or compatible retinal attachment. A normal phone photo of the outside of the eye is not a fundus image.',
    targetArea: 'Retina (fundus photograph)',
    captureMode: 'upload_only',
  },
  {
    id: 'Anemia',
    title: 'Anemia Detection',
    description: 'Record eye or nail photos for clinician review',
    icon: '🩸',
    color: Colors.anemia,
    instructions: 'Pull down lower eyelid gently and point camera at inner eyelid.',
    targetArea: 'Lower eyelid or fingernail',
  },
  {
    id: 'SkinDisease',
    title: 'Skin Disease',
    description: 'Record skin photos for clinician review',
    icon: '🦠',
    color: Colors.skin,
    instructions: 'Point camera directly at the affected skin area. Ensure good lighting.',
    targetArea: 'Affected skin area',
  },
  {
    id: 'Posture',
    title: 'Posture & Scoliosis',
    description: 'Record posture photos for physiotherapy review',
    icon: '🦴',
    color: Colors.posture,
    instructions: 'Stand 2-3 meters away, full body visible in frame. Face camera or stand sideways.',
    targetArea: 'Full body (front or side view)',
  },
  {
    id: 'EyeDisease',
    title: 'Eye Disease',
    description: 'Record eye photos for clinician review',
    icon: '👁️',
    color: Colors.eye,
    instructions: 'Open eye wide, camera ~20cm away. Use natural lighting.',
    targetArea: 'Eye (front-facing)',
  },
  {
    id: 'Wound',
    title: 'Wound Measurement',
    description: 'Record wound photos; calibrated measurement pending',
    icon: '🩹',
    color: Colors.wound,
    instructions: 'Capture clearly without touching the wound. Do not place coins near an open wound. Measurements are not available in this preview.',
    targetArea: 'Wound / affected area',
  },
  {
    id: 'TongueDiagnosis',
    title: 'Tongue Diagnosis',
    description: 'Record tongue photos for clinician review',
    icon: '👅',
    color: Colors.tongue,
    instructions: 'Extend tongue fully, use natural lighting, camera 15-20cm away.',
    targetArea: 'Extended tongue',
  },
];
