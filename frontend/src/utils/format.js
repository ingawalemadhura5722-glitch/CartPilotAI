// Format a number as Indian Rupees, e.g. 58990 -> "₹58,990".
const priceFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function formatPrice(value) {
  return priceFormatter.format(value);
}

// INR with paise when needed (used for payment amounts): "₹58,990" or "₹58,990.50"
const inrExactFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function formatInrAmount(value) {
  return inrExactFormatter.format(Number(value));
}

// US dollars with exactly two decimals: "$694.00"
const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatUsd(value) {
  return usdFormatter.format(Number(value));
}