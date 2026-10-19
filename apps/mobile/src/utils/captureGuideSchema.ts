import { z } from 'zod';
const box = z.object({ x: z.number().finite().min(0).max(1), y: z.number().finite().min(0).max(1),
  width: z.number().finite().positive().max(1), height: z.number().finite().positive().max(1) })
  .refine(b => b.x + b.width <= 1.000001 && b.y + b.height <= 1.000001, 'Invalid rectangle');
export const captureGuideSchema = z.object({
  capture_eligible: z.boolean(), guidance: z.string().min(1).max(500),
  detector: z.enum(['framing_guide', 'yolov8n-person', 'unavailable', 'multiple_people']),
  target_verified: z.boolean(), box: box.nullable(), signal: z.array(z.number().finite().min(0).max(255)).length(64),
  clinical_inference: z.literal(false),
}).superRefine((value, context) => {
  if (value.capture_eligible && value.detector === 'yolov8n-person' && (!value.box || !value.target_verified)
    || value.capture_eligible && ['unavailable', 'multiple_people'].includes(value.detector)
    || value.detector === 'framing_guide' && (value.target_verified || value.box)) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: 'Invalid capture evidence' });
  }
});
