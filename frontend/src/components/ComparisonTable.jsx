import { Check, Minus, ShoppingCart, Star, Trophy } from "lucide-react";
import ProductImage from "./ProductImage.jsx";
import { useCart } from "../context/CartContext.jsx";
import { formatPrice } from "../utils/format.js";

// Side-by-side comparison. Prices, ratings and stock come from the database;
// the advantages / disadvantages text was written by the AI.
export default function ComparisonTable({ comparison, products }) {
  const { addItem, items: cartItems } = useCart();
  const productsById = Object.fromEntries(products.map((p) => [p.id, p]));

  return (
    <div className="compare-card">
      <div className="compare-head">
        <strong>Comparison</strong>
        <span>Criterion: {comparison.criterion}</span>
      </div>

      <div className="compare-scroll">
        <table className="compare-table">
          <thead>
            <tr>
              <th className="row-label" />
              {comparison.items.map((item) => (
                <th key={item.product_id} className={item.is_winner ? "compare-th winner" : "compare-th"}>
                  {item.is_winner && (
                    <span className="winner-badge">
                      <Trophy size={13} /> Best pick
                    </span>
                  )}
                  <div className="compare-thumb">
                    <ProductImage src={productsById[item.product_id]?.image_url} alt={item.name} />
                  </div>
                  <span className="compare-name">{item.name}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="row-label">Price</td>
              {comparison.items.map((item) => (
                <td key={item.product_id} className="compare-price">
                  {formatPrice(item.price)}
                </td>
              ))}
            </tr>
            <tr>
              <td className="row-label">Rating</td>
              {comparison.items.map((item) => (
                <td key={item.product_id}>
                  <span className="rating">
                    <Star size={14} fill="currentColor" /> {item.rating.toFixed(1)}
                  </span>
                </td>
              ))}
            </tr>
            <tr>
              <td className="row-label">Availability</td>
              {comparison.items.map((item) => (
                <td key={item.product_id}>
                  {item.in_stock ? (
                    <span className="stock-note ok">In stock ({item.stock})</span>
                  ) : (
                    <span className="stock-note out">Out of stock</span>
                  )}
                </td>
              ))}
            </tr>
            <tr>
              <td className="row-label">Key specs</td>
              {comparison.items.map((item) => (
                <td key={item.product_id}>
                  {item.key_specs.length > 0 ? (
                    <ul className="compare-list plain">
                      {item.key_specs.map((spec) => (
                        <li key={spec}>{spec}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="compare-muted">Not listed</span>
                  )}
                </td>
              ))}
            </tr>
            <tr>
              <td className="row-label">Advantages</td>
              {comparison.items.map((item) => (
                <td key={item.product_id}>
                  <ul className="compare-list pros">
                    {item.advantages.length > 0 ? (
                      item.advantages.map((a) => (
                        <li key={a}>
                          <Check size={14} /> <span>{a}</span>
                        </li>
                      ))
                    ) : (
                      <li className="compare-muted">None noted</li>
                    )}
                  </ul>
                </td>
              ))}
            </tr>
            <tr>
              <td className="row-label">Disadvantages</td>
              {comparison.items.map((item) => (
                <td key={item.product_id}>
                  <ul className="compare-list cons">
                    {item.disadvantages.length > 0 ? (
                      item.disadvantages.map((d) => (
                        <li key={d}>
                          <Minus size={14} /> <span>{d}</span>
                        </li>
                      ))
                    ) : (
                      <li className="compare-muted">None noted</li>
                    )}
                  </ul>
                </td>
              ))}
            </tr>
            <tr>
              <td className="row-label">Best for</td>
              {comparison.items.map((item) => (
                <td key={item.product_id}>{item.best_for || <span className="compare-muted">—</span>}</td>
              ))}
            </tr>
            <tr>
              <td className="row-label" />
              {comparison.items.map((item) => {
                const product = productsById[item.product_id];
                const inCart = cartItems.find((c) => c.id === item.product_id)?.quantity ?? 0;
                const disabled = !product || !item.in_stock || inCart >= item.stock;
                return (
                  <td key={item.product_id}>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={disabled}
                      onClick={() => addItem(product, 1)}
                    >
                      <ShoppingCart size={15} /> {inCart > 0 ? `Add (in cart: ${inCart})` : "Add to Cart"}
                    </button>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="compare-note">
        Price, rating and stock come from the store database. Specs are limited to what the product listing states.
      </p>
    </div>
  );
}