export function formatPrice(price: number | null): string {
  if (price == null) return "Price on request";
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(price);
}

export function specLabel(key: string): string {
  const overrides: Record<string, string> = {
    iso_sensitivity: "ISO sensitivity",
    lcd_size: "LCD size",
    lcd_resolution: "LCD resolution",
    lcd_type: "LCD type",
    raw_support: "RAW support",
    ibis: "IBIS",
    wifi: "Wi-Fi",
    nfc: "NFC",
    gps: "GPS",
    evf: "EVF",
  };
  if (overrides[key]) return overrides[key];
  const label = key.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}
