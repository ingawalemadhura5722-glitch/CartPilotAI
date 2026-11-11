import { useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { XCircle } from "lucide-react";
import { cancelPaypalOrder } from "../services/api.js";
import { loadPendingCheckout } from "../utils/checkoutStorage.js";

// PayPal sends the customer here when they click "Cancel and return" (?token=<PayPal order ID>).
// Nothing is marked as paid, and the cart is left exactly as it was.
export default function PaymentCancel() {
  const [params] = useSearchParams();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const token = params.get("token");
    const pending = loadPendingCheckout();
    if (token && pending && pending.paypal_order_id === token) {
      // Best effort: tell the backend this checkout was cancelled. Failure here is harmless.
      cancelPaypalOrder({
        paypal_order_id: token,
        checkout_token: pending.checkout_token,
      }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="container page">
      <div className="result-card result-cancel">
        <XCircle size={48} />
        <h1>Payment cancelled</h1>
        <p>You cancelled the PayPal payment. No payment was taken and no order was placed.</p>
        <p className="result-muted">Your cart has been kept, so you can try again whenever you're ready.</p>
        <div className="empty-actions">
          <Link to="/cart" className="btn btn-primary">Return to cart</Link>
          <Link to="/products" className="btn btn-outline">Keep shopping</Link>
        </div>
      </div>
    </div>
  );
}