import { useState } from "react";
import { Check, ShoppingCart, Star } from "lucide-react";
import ProductImage from "./ProductImage.jsx";
import { useCart } from "../context/CartContext.jsx";
import { formatPrice } from "../utils/format.js";

export default function ProductCard({ product }) {
  const { addItem, items } = useCart();
  const [justAdded, setJustAdded] = useState(false);

  const inCart = items.find((i) => i.id === product.id)?.quantity ?? 0;
  const outOfStock = product.stock <= 0;
  const maxedOut = inCart >= product.stock;

  const handleAdd = () => {
    addItem(product, 1);
    setJustAdded(true);
    setTimeout(() => setJustAdded(false), 1200); // reset the button label after 1.2s
  };

  return (
    <article className="product-card">
      <div className="product-image-wrap">
        <ProductImage src={product.image_url} alt={product.name} />
        <span className="product-category">{product.category}</span>
      </div>

      <div className="product-body">
        <h3 className="product-name">{product.name}</h3>
        <p className="product-desc">{product.description}</p>

        <div className="product-meta">
          <span className="rating">
            <Star size={15} fill="currentColor" /> {product.rating.toFixed(1)}
          </span>
          {outOfStock ? (
            <span className="stock-note out">Out of stock</span>
          ) : product.stock <= 5 ? (
            <span className="stock-note low">Only {product.stock} left</span>
          ) : (
            <span className="stock-note ok">In stock</span>
          )}
        </div>

        <div className="product-footer">
          <span className="price">{formatPrice(product.price)}</span>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleAdd}
            disabled={outOfStock || maxedOut}
          >
            {justAdded ? (
              <>
                <Check size={16} /> Added
              </>
            ) : (
              <>
                <ShoppingCart size={16} /> {maxedOut && !outOfStock ? "Max in cart" : "Add to Cart"}
              </>
            )}
          </button>
        </div>
      </div>
    </article>
  );
}