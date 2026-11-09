import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle, CheckCircle2, Info, Loader2, Minus, Plus, ShoppingBag, Trash2, Wrench,
} from "lucide-react";
import ProductImage from "../components/ProductImage.jsx";
import { useCart } from "../context/CartContext.jsx";
import { getErrorMessage, validateCart } from "../services/api.js";
import { formatPrice } from "../utils/format.js";

export default function Cart() {
  const { items, subtotal, changeQuantity, removeItem, clearCart, syncWithServer } = useCart();

  const [validation, setValidation] = useState(null); // server response
  const [validating, setValidating] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [showNotice, setShowNotice] = useState(false);

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
  const checkoutBlocked = validating || !validation || !validation.valid;

  return (
    <div className="container page">
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Shopping Cart</h1>
          <p className="page-sub">Review your items before checkout.</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={clearCart}>
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
                <button onClick={() => changeQuantity(item.id, -1)} disabled={item.quantity <= 1} aria-label="Decrease quantity">
                  <Minus size={15} />
                </button>
                <span>{item.quantity}</span>
                <button onClick={() => changeQuantity(item.id, 1)} disabled={item.quantity >= item.stock} aria-label="Increase quantity">
                  <Plus size={15} />
                </button>
              </div>
              <div className="cart-line-total">{formatPrice(item.price * item.quantity)}</div>
              <button className="icon-btn" onClick={() => removeItem(item.id)} aria-label={`Remove ${item.name}`}>
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
            <span>Total</span>
            <span>{formatPrice(total)}</span>
          </div>

          {/* Placeholder only: no payment is processed anywhere in Day 1. */}
          <button
            className="btn btn-primary btn-block"
            disabled={checkoutBlocked}
            onClick={() => setShowNotice(true)}
          >
            Proceed to Checkout
          </button>

          {showNotice && (
            <div className="notice" role="status">
              <Info size={18} />
              <p>
                Checkout isn't available yet. PayPal Sandbox payment will be added in a later stage.
                No order was placed and no payment was made.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}