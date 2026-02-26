import type { PrivacyPolicy } from '@/lib/types/privacy';

const DEFAULT_LOCAL_CONFIDENCE_THRESHOLD = 0.6;

function clamp01(value: number): number {
  if (Number.isNaN(value)) return DEFAULT_LOCAL_CONFIDENCE_THRESHOLD;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

export function getPrivacyPolicy(): PrivacyPolicy {
  const parsed = Number(process.env.PRIVACY_LOCAL_CONFIDENCE_THRESHOLD);

  return {
    localConfidenceThreshold: clamp01(parsed || DEFAULT_LOCAL_CONFIDENCE_THRESHOLD),
  };
}
