import { createContext, useContext, useEffect, useMemo, useState } from "react";

/*
  The cart lives in React state so every page can read and change it.
  We also save it to localStorage so it survives a page refresh.
  The cart is only a convenience copy: /api/cart/validate re-checks everything on the server.
*/

const CartContext = createContext(null);
const STORAGE_KEY = "cartpilot_cart_v1";

function loadCart() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function CartProvider({ children }) {
  const [items, setItems] = useState(loadCart);

  // Save to localStorage whenever the cart changes.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      /* storage may be unavailable (private mode): ignore */
    }
  }, [items]);

  // Add a product (or increase its quantity), never going above available stock.
  const addItem = (product, quantity = 1) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.id === product.id);
      if (existing) {
        return prev.map((i) =>
          i.id === product.id
            ? { ...i, stock: product.stock, quantity: Math.min(i.quantity + quantity, product.stock) }
            : i
        );
      }
      return [
        ...prev,
        {
          id: product.id,
          name: product.name,
          category: product.category,
          price: product.price,
          image_url: product.image_url,
          stock: product.stock,
          quantity: Math.min(quantity, product.stock),
        },
      ];
    });
  };

  // Change quantity by +1 or -1 (stays between 1 and stock).
  const changeQuantity = (id, delta) => {
    setItems((prev) =>
      prev.map((i) =>
        i.id === id ? { ...i, quantity: Math.max(1, Math.min(i.quantity + delta, i.stock)) } : i
      )
    );
  };

  const removeItem = (id) => setItems((prev) => prev.filter((i) => i.id !== id));

  const clearCart = () => setItems([]);

  // Apply the server's answer from /api/cart/validate: fix prices, clamp quantities, drop dead items.
  const syncWithServer = (lines) => {
    setItems((prev) =>
      prev.flatMap((item) => {
        const line = lines.find((l) => l.product_id === item.id);
        if (!line) return [item];
        if (line.server_price === null || line.server_price === undefined) return []; // product removed
        if (line.available_stock <= 0) return []; // out of stock
        return [
          {
            ...item,
            price: line.server_price,
            stock: line.available_stock,
            quantity: Math.min(item.quantity, line.available_stock),
          },
        ];
      })
    );
  };

  const itemCount = useMemo(() => items.reduce((sum, i) => sum + i.quantity, 0), [items]);
  const subtotal = useMemo(() => items.reduce((sum, i) => sum + i.price * i.quantity, 0), [items]);

  const value = { items, itemCount, subtotal, addItem, changeQuantity, removeItem, clearCart, syncWithServer };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

// Custom hook: const { items, addItem } = useCart();
export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used inside <CartProvider>");
  return context;
}