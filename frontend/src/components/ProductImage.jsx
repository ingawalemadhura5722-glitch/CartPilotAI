import { useState } from "react";
import { Package } from "lucide-react";

// Shows the product image. If the image fails to load (e.g. offline), show a neat fallback box.
export default function ProductImage({ src, alt }) {
  const [failed, setFailed] = useState(false);

  if (failed || !src) {
    return (
      <div className="image-fallback" aria-label={alt}>
        <Package size={34} />
      </div>
    );
  }
  return <img className="product-image" src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />;
}