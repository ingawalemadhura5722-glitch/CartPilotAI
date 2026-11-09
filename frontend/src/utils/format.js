// Format a number as Indian Rupees, e.g. 58990 -> "₹58,990".
const priceFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function formatPrice(value) {
  return priceFormatter.format(value);
}