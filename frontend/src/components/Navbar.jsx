import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Bot, LayoutGrid, Menu, Home, ShoppingCart, Sparkles, X } from "lucide-react";
import { useCart } from "../context/CartContext.jsx";

export default function Navbar() {
  const [open, setOpen] = useState(false); // mobile menu open/closed
  const { itemCount } = useCart();

  const close = () => setOpen(false);
  const linkClass = ({ isActive }) => (isActive ? "nav-link active" : "nav-link");

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <Link to="/" className="logo" onClick={close}>
          <span className="logo-mark">
            <Sparkles size={18} />
          </span>
          <span>
            CartPilot <span className="logo-ai">AI</span>
          </span>
        </Link>

        <nav className={open ? "nav-links open" : "nav-links"}>
          <NavLink to="/" end className={linkClass} onClick={close}>
            <Home size={17} /> Home
          </NavLink>
          <NavLink to="/products" className={linkClass} onClick={close}>
            <LayoutGrid size={17} /> Products
          </NavLink>
          <NavLink to="/assistant" className={linkClass} onClick={close}>
            <Bot size={17} /> AI Assistant
          </NavLink>
        </nav>

        <div className="nav-actions">
          <Link to="/cart" className="cart-link" onClick={close} aria-label={`Cart with ${itemCount} items`}>
            <ShoppingCart size={21} />
            {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
          </Link>
          <button
            className="menu-toggle"
            onClick={() => setOpen((o) => !o)}
            aria-label="Toggle menu"
          >
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>
    </header>
  );
}