import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { useCart } from "../context/CartContext.jsx";
import { capturePaypalOrder, getErrorMessage } from "../services/api.js";
import { loadPendingCheckout } from "../utils/checkoutStorage.js";
import { formatInrAmount, formatUsd } from "../utils/format.js";

// PayPal sends the customer here after approval (?token=<PayPal order ID>&PayerID=...).
// Coming back from PayPal does NOT mean the payment succeeded. This page asks the backend
// to capture and verify it, and only shows "confirmed" after the backend says so.
export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const { clearCart } = useCart();
  const [phase, setPhase] = useState("verifying"); // verifying | success | error
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // React dev mode runs effects twice: only start once
    started.current = true;

    const token = params.get("token"); // PayPal order ID
    const pending = loadPendingCheckout();

    if (!token) {
      setErrorMessage("This page was opened without a PayPal order reference.");
      setPhase("error");
      return;
    }
    if (!pending || pending.paypal_order_id !== token) {
      setErrorMessage(
        "We couldn't match this payment to a checkout started in this browser, so it was not verified. " +
          "Open the app at http://localhost:5173 and try again."
      );
      setPhase("error");
      return;
    }

    capturePaypalOrder({ paypal_order_id: token, checkout_token: pending.checkout_token })
      .then((data) => {
        setResult(data);
        setPhase("success");
        clearCart(); // only now that the backend verified the payment
      })
      .catch((err) => {
        setErrorMessage(getErrorMessage(err));
        setPhase("error");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (phase === "verifying") {
    return (
      <div className="container page">
        <div className="result-card">
          <Loader2 size={44} className="spinner" />
          <h1>Verifying your payment...</h1>
          <p>Please wait while we confirm the payment with PayPal. Don't close this page.</p>
        </div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="container page">
        <div className="result-card result-error">
          <AlertTriangle size={44} />
          <h1>Payment not confirmed</h1>
          <p>{errorMessage}</p>
          <p className="result-muted">Your order was not marked as paid and your cart has been kept.</p>
          <div className="empty-actions">
            <Link to="/cart" className="btn btn-primary">Back to cart</Link>
            <Link to="/products" className="btn btn-outline">Keep shopping</Link>
          </div>
        </div>
      </div>
    );
  }

  const { order } = result;
  return (
    <div className="container page">
      <div className="result-card result-success">
        <CheckCircle2 size={48} />
        <h1>Payment confirmed</h1>
        <p>
          Thank you! PayPal Sandbox confirmed the payment and our server verified the amount.
          {result.already_captured && " (This payment was already verified earlier.)"}
        </p>

        <div className="result-grid">
          <div><span>Order number</span><strong>{order.order_number}</strong></div>
          <div><span>Payment status</span><strong><span className="status-pill paid">{order.status}</span></strong></div>
          <div><span>PayPal order ID</span><strong className="mono">{order.paypal_order_id}</strong></div>
          <div><span>Transaction (capture) ID</span><strong className="mono">{order.paypal_capture_id}</strong></div>
          <div><span>Original total (INR)</span><strong>{formatInrAmount(order.total_inr)}</strong></div>
          <div><span>PayPal Sandbox amount (USD)</span><strong>{formatUsd(order.total_usd)}</strong></div>
        </div>

        <h2 className="result-subtitle">Purchased products</h2>
        <div className="result-table-wrap">
          <table className="result-table">
            <thead>
              <tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Total</th></tr>
            </thead>
            <tbody>
              {order.items.map((item) => (
                <tr key={item.product_id}>
                  <td>{item.name}</td>
                  <td>{item.quantity}</td>
                  <td>{formatInrAmount(item.unit_price_inr)}</td>
                  <td>{formatInrAmount(item.line_total_inr)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="result-muted">{order.conversion_notice}</p>

        <div className="empty-actions">
          <Link to="/products" className="btn btn-primary">Continue shopping</Link>
          <Link to="/assistant" className="btn btn-outline">Ask the assistant</Link>
        </div>
      </div>
    </div>
  );
}