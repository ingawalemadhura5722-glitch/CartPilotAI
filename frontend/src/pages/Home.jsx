import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Bot, Package, ShieldCheck, ShoppingCart, Star, Tag, Zap } from "lucide-react";
import SearchBar from "../components/SearchBar.jsx";
import ProductCard from "../components/ProductCard.jsx";
import LoadingState from "../components/LoadingState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import { getErrorMessage, getProducts } from "../services/api.js";
import { useCart } from "../context/CartContext.jsx";

const EXAMPLES = [
  "Find me a laptop under ₹60,000 for programming.",
  "Suggest budget-friendly headphones.",
  "Best smartphone under ₹25,000",
];

export default function Home() {
  const navigate = useNavigate();
  const { itemCount } = useCart();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getProducts()
      .then((data) => !cancelled && setProducts(data))
      .catch((err) => !cancelled && setError(getErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // The natural-language search hands the sentence to the AI Assistant page.
  const askAssistant = (text) => navigate(`/assistant?q=${encodeURIComponent(text)}`);

  // Everything below is calculated from the products the backend returned.
  const featured = useMemo(
    () => [...products].sort((a, b) => b.rating - a.rating).slice(0, 4),
    [products]
  );
  const recommended = useMemo(() => {
    const featuredIds = new Set(featured.map((p) => p.id));
    return products
      .filter((p) => !featuredIds.has(p.id) && p.stock > 0 && p.rating >= 4.3)
      .sort((a, b) => a.price - b.price)
      .slice(0, 4);
  }, [products, featured]);

  const stats = useMemo(() => {
    const categories = new Set(products.map((p) => p.category));
    const avg = products.length ? products.reduce((s, p) => s + p.rating, 0) / products.length : 0;
    return { total: products.length, categories: categories.size, avg: avg.toFixed(1) };
  }, [products]);

  return (
    <>
      {/* ---------- Hero ---------- */}
      <section className="hero">
        <div className="container hero-inner">
          <span className="hero-pill">
            <Zap size={14} /> Smart shopping, simplified
          </span>
          <h1>
            Your Intelligent <span className="gradient-text">Shopping Agent</span>
          </h1>
          <p>
            Describe what you need in plain English. CartPilot finds, compares and organizes products for you.
          </p>
          <SearchBar
            placeholder='Try: "A laptop under ₹60,000 for programming"'
            onSubmit={askAssistant}
          />
          <div className="chips">
            {EXAMPLES.map((example) => (
              <button key={example} className="chip" onClick={() => askAssistant(example)}>
                {example}
              </button>
            ))}
          </div>
          <p className="hero-note">The assistant is a demo that uses simple rules. Real AI arrives in a later stage.</p>
        </div>
      </section>

      <div className="container">
        {/* ---------- Stats ---------- */}
        <section className="stats-grid" aria-label="Shopping highlights">
          <div className="stat-card">
            <span className="stat-icon"><Package size={20} /></span>
            <div>
              <div className="stat-value">{loading ? "…" : stats.total}</div>
              <div className="stat-label">Products in catalog</div>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-icon"><Tag size={20} /></span>
            <div>
              <div className="stat-value">{loading ? "…" : stats.categories}</div>
              <div className="stat-label">Categories</div>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-icon"><Star size={20} /></span>
            <div>
              <div className="stat-value">{loading ? "…" : stats.avg}</div>
              <div className="stat-label">Average rating</div>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-icon"><ShoppingCart size={20} /></span>
            <div>
              <div className="stat-value">{itemCount}</div>
              <div className="stat-label">Items in your cart</div>
            </div>
          </div>
        </section>

        {loading && <LoadingState label="Loading products from the CartPilot backend..." />}
        {error && <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />}

        {/* ---------- Featured ---------- */}
        {!loading && !error && (
          <>
            <section className="section">
              <div className="section-header">
                <div>
                  <h2 className="section-title">Featured products</h2>
                  <p className="section-sub">Our top-rated picks across the catalog.</p>
                </div>
                <Link to="/products" className="link-arrow">
                  View all <ArrowRight size={16} />
                </Link>
              </div>
              <div className="product-grid">
                {featured.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            </section>

            {/* ---------- Recommended ---------- */}
            <section className="section">
              <div className="section-header">
                <div>
                  <h2 className="section-title">Recommended for you</h2>
                  <p className="section-sub">
                    Highly rated picks that are easy on the budget. (Demo recommendations, not personalized yet.)
                  </p>
                </div>
              </div>
              <div className="product-grid">
                {recommended.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            </section>
          </>
        )}

        {/* ---------- How it works ---------- */}
        <section className="section">
          <h2 className="section-title">What CartPilot does</h2>
          <div className="feature-grid">
            <div className="feature-card">
              <Bot size={26} />
              <h3>Ask in plain language</h3>
              <p>Describe a product and a budget; the demo assistant suggests matches from the catalog.</p>
              <span className="badge badge-live">Available (demo)</span>
            </div>
            <div className="feature-card">
              <ShoppingCart size={26} />
              <h3>Smart cart</h3>
              <p>Manage quantities and let the server double-check prices and stock for you.</p>
              <span className="badge badge-live">Available</span>
            </div>
            <div className="feature-card">
              <ShieldCheck size={26} />
              <h3>Secure checkout</h3>
              <p>PayPal Sandbox checkout is planned for a later stage. No payments happen today.</p>
              <span className="badge badge-soon">Coming soon</span>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}