"""
Seed data: 20 sample products across 5 categories.

Prices (in INR) and ratings are illustrative sample data for the demo,
not live store prices.

Images use placehold.co placeholder images with brand colours so the app
never depends on copyrighted photos. Replace image_url values with real
image links whenever you like.

You can also reset the database manually:
    python -m app.services.seed
"""

from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from app.models.product import Product

# One colour per category for the placeholder images (hex without '#').
CATEGORY_COLORS = {
    "Laptops": "4f46e5",
    "Smartphones": "0284c7",
    "Headphones": "7c3aed",
    "Accessories": "059669",
    "Smart Devices": "d97706",
}


def _product(name, category, description, price, rating, stock, label):
    """Small helper that builds one product dictionary."""
    color = CATEGORY_COLORS[category]
    image_url = f"https://placehold.co/600x450/{color}/ffffff?text={quote_plus(label)}"
    return {
        "name": name,
        "category": category,
        "description": description,
        "price": price,
        "rating": rating,
        "stock": stock,
        "image_url": image_url,
    }


SAMPLE_PRODUCTS = [
    # ---------------- Laptops ----------------
    _product(
        "Lenovo IdeaPad Slim 5 (Ryzen 7, 16GB, 512GB SSD)", "Laptops",
        "14-inch lightweight laptop with a Ryzen 7 processor, 16GB RAM and 512GB SSD. A solid choice for programming, coding and everyday multitasking.",
        58990, 4.5, 12, "IdeaPad Slim 5",
    ),
    _product(
        "Acer Aspire Lite (Core i3, 8GB, 512GB SSD)", "Laptops",
        "Affordable 15.6-inch laptop for students and light office work, with a fast SSD and a long-lasting battery.",
        32990, 4.0, 20, "Acer Aspire Lite",
    ),
    _product(
        "ASUS TUF Gaming F15 (Core i5, RTX 3050)", "Laptops",
        "Gaming laptop with a dedicated RTX graphics card and 144Hz display. Also handles video editing and heavy development workloads.",
        69990, 4.4, 8, "ASUS TUF F15",
    ),
    _product(
        "Apple MacBook Air M2 (8GB, 256GB)", "Laptops",
        "Thin and silent premium laptop with the Apple M2 chip. Excellent battery life, great for programming, design and travel.",
        114900, 4.8, 5, "MacBook Air M2",
    ),
    # ---------------- Smartphones ----------------
    _product(
        "Samsung Galaxy S24 FE (8GB, 128GB)", "Smartphones",
        "Flagship-style phone with a bright AMOLED display, a versatile triple camera and long software support.",
        54999, 4.5, 14, "Galaxy S24 FE",
    ),
    _product(
        "Redmi Note 13 Pro 5G (8GB, 256GB)", "Smartphones",
        "Mid-range 5G phone with a 200MP main camera, a smooth AMOLED screen and fast charging. Excellent value for money.",
        23999, 4.4, 30, "Redmi Note 13 Pro",
    ),
    _product(
        "OnePlus Nord CE 4 (8GB, 128GB)", "Smartphones",
        "Clean software, fast 100W charging and a big battery. A great everyday phone for gaming and photography.",
        24999, 4.3, 18, "OnePlus Nord CE 4",
    ),
    _product(
        "Apple iPhone 15 (128GB)", "Smartphones",
        "Dynamic Island, a 48MP main camera and the A16 chip in a premium, durable design.",
        69900, 4.7, 9, "iPhone 15",
    ),
    # ---------------- Headphones ----------------
    _product(
        "Sony WH-1000XM5 Wireless Headphones", "Headphones",
        "Industry-leading noise cancellation, 30-hour battery and rich sound. Ideal for travel, music and focused work.",
        29990, 4.8, 10, "Sony WH-1000XM5",
    ),
    _product(
        "boAt Rockerz 450 Bluetooth Headphones", "Headphones",
        "Budget-friendly on-ear wireless headphones with punchy bass and up to 15 hours of playback. Great for music and casual use.",
        1499, 4.1, 60, "boAt Rockerz 450",
    ),
    _product(
        "JBL Tune 770NC Wireless Headphones", "Headphones",
        "Active noise cancelling headphones with JBL Pure Bass sound and up to 70 hours of battery life.",
        6999, 4.3, 25, "JBL Tune 770NC",
    ),
    _product(
        "Apple AirPods Pro (2nd Gen)", "Headphones",
        "Wireless earbuds with active noise cancellation, transparency mode and a compact charging case.",
        24900, 4.7, 0, "AirPods Pro 2",   # stock 0 on purpose: shows the "out of stock" state
    ),
    # ---------------- Accessories ----------------
    _product(
        "Logitech MX Master 3S Wireless Mouse", "Accessories",
        "Ergonomic wireless mouse with a quiet-click design and a precision scroll wheel. Loved by developers and designers.",
        9995, 4.8, 15, "MX Master 3S",
    ),
    _product(
        "Keychron K2 Mechanical Keyboard", "Accessories",
        "Compact wireless mechanical keyboard that works with Windows and Mac. Comfortable for long programming and typing sessions.",
        8499, 4.6, 11, "Keychron K2",
    ),
    _product(
        "Portronics 20000mAh Power Bank", "Accessories",
        "High-capacity power bank with fast charging. Keeps your phone and tablet running while travelling.",
        2199, 4.2, 40, "Power Bank 20000",
    ),
    _product(
        "Wildcraft Laptop Backpack (30L)", "Accessories",
        "Water-resistant backpack with a padded laptop compartment and plenty of storage for work or college.",
        1799, 4.3, 3, "Laptop Backpack",
    ),
    # ---------------- Smart Devices ----------------
    _product(
        "Amazon Echo Dot (5th Gen) Smart Speaker", "Smart Devices",
        "Compact smart speaker with Alexa, improved bass and smart home controls. Plays music and answers questions.",
        5499, 4.5, 22, "Echo Dot 5",
    ),
    _product(
        "Noise ColorFit Pro 5 Smartwatch", "Smart Devices",
        "AMOLED smartwatch with Bluetooth calling, heart-rate and sleep tracking, and multiple sports modes.",
        3499, 4.2, 35, "ColorFit Pro 5",
    ),
    _product(
        "Mi 360° Home Security Camera (2K)", "Smart Devices",
        "Indoor smart camera with 360° rotation, night vision and motion alerts. Keeps an eye on your home from your phone.",
        2999, 4.3, 17, "Home Security Cam",
    ),
    _product(
        "Wipro 12W Smart Wi-Fi LED Bulb", "Smart Devices",
        "Colour-changing smart bulb you can control from your phone or by voice. Works with Alexa and Google Assistant.",
        799, 4.0, 80, "Smart LED Bulb",
    ),
]


def seed_products(db: Session) -> int:
    """Insert the sample products if the table is empty. Returns how many were added."""
    if db.query(Product).count() > 0:
        return 0  # already seeded, do nothing

    for item in SAMPLE_PRODUCTS:
        db.add(Product(**item))
    db.commit()
    return len(SAMPLE_PRODUCTS)


if __name__ == "__main__":
    # Run:  python -m app.services.seed
    # Drops and recreates the products table, then seeds it again.
    from app.database import Base, SessionLocal, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        count = seed_products(session)
        print(f"Database reset. Seeded {count} products.")
    finally:
        session.close()