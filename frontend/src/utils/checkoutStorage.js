// Remembers the checkout we started, so the success/cancel pages (reached after PayPal
// redirects the browser back) can prove that this browser started it.
// The checkout_token is a random secret created by the backend for ONE checkout.

const KEY = "cartpilot_pending_checkout_v1";

export function savePendingCheckout(info) {
  try {
    localStorage.setItem(KEY, JSON.stringify(info));
  } catch {
    /* storage may be unavailable: ignore */
  }
}

export function loadPendingCheckout() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearPendingCheckout() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}