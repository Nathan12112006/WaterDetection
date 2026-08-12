export const MODEL_CLASSES = [
  'pipe burst',
  'water accumulation',
  'water drop',
] as const

export type ModelClass = (typeof MODEL_CLASSES)[number]
