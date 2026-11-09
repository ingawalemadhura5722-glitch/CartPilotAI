import { useState } from "react";
import { Search, Sparkles } from "lucide-react";

// A natural-language search box. Calls onSubmit(text) when the user presses Enter or the button.
export default function SearchBar({ placeholder, buttonLabel = "Ask CartPilot", onSubmit }) {
  const [value, setValue] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault(); // stop the page from reloading
    const trimmed = value.trim();
    if (trimmed) onSubmit(trimmed);
  };

  return (
    <form className="hero-search" onSubmit={handleSubmit}>
      <Search size={20} className="hero-search-icon" />
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        aria-label="Describe what you want to buy"
      />
      <button type="submit" className="btn btn-primary">
        <Sparkles size={16} /> {buttonLabel}
      </button>
    </form>
  );
}