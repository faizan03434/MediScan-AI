import type { CaptureGuide } from '../services/captureService';
export function stableCapture(previous: CaptureGuide | null, next: CaptureGuide): boolean {
  if (previous?.clinical_inference !== false || next.clinical_inference !== false) return false;
  if (!previous?.capture_eligible || !next.capture_eligible) return false;
  if (previous.signal.length !== 64 || next.signal.length !== 64) return false;
  if (![...previous.signal, ...next.signal].every(v => Number.isFinite(v) && v >= 0 && v <= 255)) return false;
  const change = next.signal.reduce((sum, value, i) => sum + Math.abs(value - previous.signal[i]), 0) / (64 * 255);
  if (change > .035 || next.detector !== previous.detector) return false;
  if (next.detector === 'yolov8n-person') {
    if (!previous.box || !next.box || !next.target_verified || !previous.target_verified) return false;
    return (['x', 'y', 'width', 'height'] as const).every(key => Math.abs(next.box![key] - previous.box![key]) < .025);
  }
  return next.detector === 'framing_guide';
}
