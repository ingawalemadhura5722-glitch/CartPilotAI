import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle, CheckCircle2, Info, Loader2, Lock, Minus, Plus, ShoppingBag, Trash2, Wrench,
} from "lucide-react";
import ProductImage from "../components/ProductImage.jsx";
import { useCart } from "../context/CartContext.jsx";
import {
  createPaypalOrder, getErrorMessage, getPaymentQuote, validateCart,
} from "../services/api.js";
import { savePendingCheckout } from "../utils/checkoutStorage.js";
import { formatInrAmount, formatPrice, formatUsd } from "../utils/format.js";

export default function Cart() {
  const { items, subtotal, changeQuantity, removeItem, clearCart, syncWithServer } = useCart();

  const [validation, setValidation] = useState(null); // server response from /api/cart/validate
  const [validating, setValidating] = useState(false);
  const [validationError, setValidationError] = useState("");

  const [quote, setQuote] = useState(null);           // server response from /api/payments/quote
  const [quoteError, setQuoteError] = useState("");

  const [checkingOut, setCheckingOut] = useState(false);
  const [checkoutError, setCheckoutError] = useState("");
  const [checkoutIssues, setCheckoutIssues] = useState([]);

  // Ask the backend to re-check prices/stock whenever the cart changes (after a short pause).
  useEffect(() => {
    if (items.length === 0) {
      setValidation(null);
      setValidationError("");
      setValidating(false);
      return undefined;
    }

    let cancelled = false;
    setValidating(true);

    const timer = setTimeout(async () => {
      try {
        const result = await validateCart(
          items.map((i) => ({ product_id: i.id, quantity: i.quantity, price: i.price }))
        );
        if (!cancelled) {
          setValidation(result);
          setValidationError("");
        }
      } catch (err) {
        if (!cancelled) setValidationError(getErrorMessage(err));
      } finally {
        if (!cancelled) setValidating(false);
      }
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [items]);

  // When the cart is valid, ask the backend for the INR total and the USD Sandbox amount.
  // The rate and the amount come from the server; this page cannot change them.
  useEffect(() => {
    setQuote(null);
    setQuoteError("");
    if (!validation || !validation.valid || items.length === 0) return undefined;

    let cancelled = false;
    getPaymentQuote(items.map((i) => ({ product_id: i.id, quantity: i.quantity })))
      .then((data) => {
        if (!cancelled) setQuote(data);
      })
      .catch((err) => {
        if (!cancelled) setQuoteError(getErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [validation]);

  const handlePayPalCheckout = async () => {
    setCheckoutError("");
    setCheckoutIssues([]);
    setCheckingOut(true);
    try {
      // Only IDs and quantities are sent.
      const order = await createPaypalOrder(items.map((i) => ({ product_id: i.id, quantity: i.quantity })));

      // Remember this checkout so the success/cancel page can verify it came from here.
      savePendingCheckout({
        paypal_order_id: order.paypal_order_id,
        checkout_token: order.checkout_token,
        order_number: order.order_number,
      });

      // Send the customer to the PayPal Sandbox approval page. We stay in the
      // "loading" state because the browser is leaving this page.
      window.location.assign(order.approval_url);
    } catch (err) {
      setCheckoutError(getErrorMessage(err));
      setCheckoutIssues(err.response?.data?.detail?.issues || []);
      setCheckingOut(false);
    }
  };

  if (items.length === 0) {
    return (
      <div className="container page">
        <div className="empty-state">
          <ShoppingBag size={48} />
          <h2>Your cart is empty</h2>
          <p>Browse the catalog or ask the assistant for ideas.</p>
          <div className="empty-actions">
            <Link to="/products" className="btn btn-primary">Browse products</Link>
            <Link to="/assistant" className="btn btn-outline">Ask the assistant</Link>
          </div>
        </div>
      </div>
    );
  }

  const problemLines = validation ? validation.items.filter((l) => !l.valid) : [];
  const total = validation ? validation.total : subtotal;
  const canPay = !validating && validation?.valid && quote && !checkingOut;

  return (
    <div className="container page">
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Shopping Cart</h1>
          <p className="page-sub">Review your items before checkout.</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={clearCart} disabled={checkingOut}>
          <Trash2 size={15} /> Clear cart
        </button>
      </div>

      <div className="cart-layout">
        {/* ---------- Items ---------- */}
        <section className="cart-items">
          {items.map((item) => (
            <article key={item.id} className="cart-item">
              <div className="cart-item-img">
                <ProductImage src={item.image_url} alt={item.name} />
              </div>
              <div className="cart-item-info">
                <span className="product-category-text">{item.category}</span>
                <h3>{item.name}</h3>
                <span className="cart-unit-price">{formatPrice(item.price)} each</span>
              </div>
              <div className="qty-control" aria-label={`Quantity for ${item.name}`}>
                <button onClick={() => changeQuantity(item.id, -1)} disabled={item.quantity <= 1 || checkingOut} aria-label="Decrease quantity">
                  <Minus size={15} />
                </button>
                <span>{item.quantity}</span>
                <button onClick={() => changeQuantity(item.id, 1)} disabled={item.quantity >= item.stock || checkingOut} aria-label="Increase quantity">
                  <Plus size={15} />
                </button>
              </div>
              <div className="cart-line-total">{formatPrice(item.price * item.quantity)}</div>
              <button className="icon-btn" onClick={() => removeItem(item.id)} disabled={checkingOut} aria-label={`Remove ${item.name}`}>
                <Trash2 size={18} />
              </button>
            </article>
          ))}
        </section>

        {/* ---------- Summary ---------- */}
        <aside className="summary-card">
          <h2>Order summary</h2>

          {/* Server verification status */}
          {validationError ? (
            <div className="verify-status warn">
              <AlertTriangle size={16} /> <span>Couldn't verify with the server: {validationError}</span>
            </div>
          ) : validating || !validation ? (
            <div className="verify-status pending">
              <Loader2 size={16} className="spinner" /> <span>Verifying prices and stock...</span>
            </div>
          ) : validation.valid ? (
            <div className="verify-status ok">
              <CheckCircle2 size={16} /> <span>Prices and stock verified by the server</span>
            </div>
          ) : (
            <div className="verify-status warn">
              <AlertTriangle size={16} />
              <div>
                <span>Some items need attention:</span>
                <ul>
                  {problemLines.map((line) => (
                    <li key={line.product_id}>
                      <strong>{line.name || `Product ${line.product_id}`}:</strong> {line.issues.join(" ")}
                    </li>
                  ))}
                </ul>
                <button className="btn btn-outline btn-sm" onClick={() => syncWithServer(validation.items)}>
                  <Wrench size={14} /> Fix my cart
                </button>
              </div>
            </div>
          )}

          <div className="summary-row">
            <span>Subtotal</span>
            <span>{formatPrice(total)}</span>
          </div>
          <div className="summary-row">
            <span>Shipping</span>
            <span>Calculated later</span>
          </div>
          <div className="summary-row summary-total">
            <span>Total (INR)</span>
            <span>{formatPrice(total)}</span>
          </div>

          {/* INR total and the USD Sandbox amount, both calculated by the backend */}
          {quote && (
            <div className="conversion-box">
              <div className="conversion-row">
                <span>Original total (INR)</span>
                <strong>{formatInrAmount(quote.total_inr)}</strong>
              </div>
              <div className="conversion-row">
                <span>PayPal Sandbox amount (USD)</span>
                <strong>{formatUsd(quote.total_usd)}</strong>
              </div>
              <p className="conversion-note">
                <Info size={14} />
                <span>
                  <strong>Sandbox demo conversion:</strong> ₹{quote.inr_per_usd} = $1.00. This fixed rate is
                  for testing only and is <strong>not</strong> a live exchange rate. PayPal Sandbox uses test
                  money, so no real payment is made.
                </span>
              </p>
            </div>
          )}
          {quoteError && (
            <div className="verify-status warn">
              <AlertTriangle size={16} /> <span>Couldn't calculate the USD amount: {quoteError}</span>
            </div>
          )}

          <button className="btn btn-primary btn-block" disabled={!canPay} onClick={handlePayPalCheckout}>
            {checkingOut ? (
              <>
                <Loader2 size={18} className="spinner-white" /> Connecting to PayPal...
              </>
            ) : (
              <>
                <Lock size={18} /> Pay with PayPal (Sandbox)
              </>
            )}
          </button>
          <p className="pay-note">
            You'll be sent to the PayPal Sandbox to approve the payment with a sandbox buyer account.
          </p>

          {checkoutError && (
            <div className="verify-status warn" role="alert">
              <AlertTriangle size={16} />
              <div>
                <span>{checkoutError}</span>
                {checkoutIssues.length > 0 && (
                  <ul>
                    {checkoutIssues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}