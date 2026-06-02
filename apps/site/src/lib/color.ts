/** Heatmap color scales for the matrix. Brand-aligned, perceptually monotonic. */

type RGB = [number, number, number];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}
function mix(a: RGB, b: RGB, t: number): RGB {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
}
function css([r, g, b]: RGB): string {
  return `rgb(${Math.round(r)} ${Math.round(g)} ${Math.round(b)})`;
}

// Dark base → brand purple → emerald: low values stay near the surface color,
// high values glow. Two-stop through purple keeps it on-brand, not a rainbow.
const LOW: RGB = [26, 26, 32]; // ~ --surface-2
const MID: RGB = [90, 70, 150]; // muted purple
const HIGH: RGB = [16, 160, 120]; // emerald-ish

/**
 * Map a normalized t∈[0,1] to a heat color. `t` should already be the
 * "higher = better" orientation (invert before calling for cost).
 */
export function heat(t: number): string {
  const c = Math.max(0, Math.min(1, t));
  return css(c < 0.5 ? mix(LOW, MID, c * 2) : mix(MID, HIGH, (c - 0.5) * 2));
}

/** Text color (light/dark) for legibility on a given heat t. */
export function heatText(t: number): string {
  return t > 0.42 ? "#f4f4f6" : "#a8a8b3";
}

/** Normalize a value into [0,1] given a range; `invert` for "lower is better". */
export function norm(
  value: number,
  min: number,
  max: number,
  invert = false
): number {
  if (max <= min) return 0.5;
  const t = (value - min) / (max - min);
  return invert ? 1 - t : t;
}
