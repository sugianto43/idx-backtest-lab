const DECIMAL_STRING_PATTERN = /^-?\d+(\.\d+)?$/;

/**
 * Groups the integer part of a decimal *string* with thousands separators
 * for display only. Never parses the value into a JS number, so precision
 * beyond `Number.MAX_SAFE_INTEGER`/float mantissa is never lost. Values that
 * don't look like a plain decimal string are returned unchanged.
 */
export function formatDecimalString(raw: string): string {
  if (!DECIMAL_STRING_PATTERN.test(raw)) {
    return raw;
  }

  const negative = raw.startsWith("-");
  const unsigned = negative ? raw.slice(1) : raw;
  const [integerPart, fractionPart] = unsigned.split(".");
  const grouped = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const result = fractionPart !== undefined ? `${grouped}.${fractionPart}` : grouped;
  return negative ? `-${result}` : result;
}
