import axios from "axios";

// The backend address comes from frontend/.env (VITE_API_BASE_URL).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000, // give up after 10 seconds
});

// Turn any Axios error into a friendly message we can show to the user.
export function getErrorMessage(error) {
  if (error.response) {
    const detail = error.response.data?.detail;
    if (typeof detail === "string") return detail;
    // The AI and payment endpoints return { code, message }
    if (detail && !Array.isArray(detail) && typeof detail === "object" && detail.message) {
      return detail.message;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => d.msg).join(", ");
    }
    return `The server returned an error (${error.response.status}).`;
  }
  if (error.code === "ECONNABORTED") {
    return "The request took too long. Please try again.";
  }
  if (error.request) {
    return `Cannot reach the CartPilot backend at ${API_BASE_URL}. Is it running?`;
  }
  return error.message || "Something went wrong.";
}

// GET /api/products  (optional: q, category, sort)
export async function getProducts({ q, category, sort } = {}) {
  const params = {};
  if (q) params.q = q;
  if (category && category !== "All") params.category = category;
  if (sort && sort !== "default") params.sort = sort;
  const response = await client.get("/api/products", { params });
  return response.data;
}

// GET /api/categories
export async function getCategories() {
  const response = await client.get("/api/categories");
  return response.data;
}

// POST /api/chat  (Gemini assistant). history = recent messages for context.
// Gemini makes two calls on the backend, so this request gets a longer timeout.
export async function sendChatMessage(message, history = []) {
  const response = await client.post("/api/chat", { message, history }, { timeout: 60000 });
  return response.data;
}

// POST /api/cart/validate
export async function validateCart(items) {
  const response = await client.post("/api/cart/validate", { items });
  return response.data;
}

// ---------------- Payments (PayPal Sandbox) ----------------
// We only ever send product IDs and quantities. The backend decides every price,
// the total, the conversion rate and the USD amount.

// POST /api/payments/quote : INR total + USD Sandbox amount (creates nothing)
export async function getPaymentQuote(items) {
  const response = await client.post("/api/payments/quote", { items });
  return response.data;
}

// POST /api/payments/create-order : returns the PayPal approval URL
export async function createPaypalOrder(items) {
  const response = await client.post("/api/payments/create-order", { items }, { timeout: 30000 });
  return response.data;
}

// POST /api/payments/capture-order : the backend captures and verifies the payment
export async function capturePaypalOrder({ paypal_order_id, checkout_token }) {
  const response = await client.post(
    "/api/payments/capture-order",
    { paypal_order_id, checkout_token },
    { timeout: 45000 }
  );
  return response.data;
}

// POST /api/payments/cancel-order
export async function cancelPaypalOrder({ paypal_order_id, checkout_token }) {
  const response = await client.post("/api/payments/cancel-order", { paypal_order_id, checkout_token });
  return response.data;
}