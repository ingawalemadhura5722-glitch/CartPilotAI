import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import ProductCard from "../components/ProductCard.jsx";
import LoadingState from "../components/LoadingState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import { getCategories, getErrorMessage, getProducts } from "../services/api.js";

const SORT_OPTIONS = [
  { value: "default", label: "Featured" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
  { value: "rating", label: "Top Rated" },
];

export default function Catalog() {
  const [searchParams] = useSearchParams();

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  const [category, setCategory] = useState("All");
  const [sort, setSort] = useState("default");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  // Load categories once. If this fails, the products request below shows the error.
  useEffect(() => {
    getCategories().then(setCategories).catch(() => {});
  }, [reloadKey]);

  // Wait 350ms after the user stops typing before calling the backend.
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch products from FastAPI whenever a filter changes.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getProducts({ q: debouncedSearch, category, sort })
      .then((data) => !cancelled && setProducts(data))
      .catch((err) => !cancelled && setError(getErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [debouncedSearch, category, sort, reloadKey]);

  const clearFilters = () => {
    setSearch("");
    setCategory("All");
    setSort("default");
  };

  return (
    <div className="container page">
      <h1 className="page-title">Product Catalog</h1>
      <p className="page-sub">Browse, search and filter products from the CartPilot backend.</p>

      <div className="toolbar">
        <div className="search-input-wrap">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search products (e.g. wireless, keyboard, camera)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search products"
          />
        </div>
        <select className="select" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort products">
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div className="category-tabs" role="tablist" aria-label="Categories">
        {["All", ...categories].map((c) => (
          <button
            key={c}
            role="tab"
            aria-selected={category === c}
            className={category === c ? "tab active" : "tab"}
            onClick={() => setCategory(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {loading && <LoadingState label="Loading products..." />}
      {error && <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />}

      {!loading && !error && (
        <>
          <p className="results-count">
            Showing {products.length} product{products.length === 1 ? "" : "s"}
          </p>
          {products.length === 0 ? (
            <div className="state-box">
              <p>No products match your filters.</p>
              <button className="btn btn-outline btn-sm" onClick={clearFilters}>
                Clear filters
              </button>
            </div>
          ) : (
            <div className="product-grid">
              {products.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}