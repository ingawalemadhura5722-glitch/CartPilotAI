"""
Demo shopping assistant: simple RULE-BASED logic (no AI / LLM).

How it works:
1. Look for a budget in the message ("under ₹60,000", "below 25k").
2. Look for category words ("laptop", "headphones", ...).
3. Look for use-case words ("programming", "gaming", ...).
4. Filter + score the products in the database and return the best few.

On a later day, this file is where the real Gemini AI call will be added.
"""

import re
from typing import List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.models.product import Product

MAX_RESULTS = 4

# Words that point to each category (single words are matched as whole words).
CATEGORY_KEYWORDS = {
    "Laptops": ["laptop", "notebook", "macbook", "computer", "pc"],
    "Smartphones": ["phone", "smartphone", "mobile", "iphone", "android"],
    "Headphones": ["headphone", "earbud", "earphone", "headset", "airpods", "audio", "music"],
    "Accessories": ["accessory", "accessories", "mouse", "keyboard", "charger", "cable",
                    "backpack", "bag", "power bank", "powerbank"],
    "Smart Devices": ["smartwatch", "watch", "speaker", "camera", "bulb", "alexa", "echo",
                      "smart home", "smart device", "tracker", "band"],
}

# A use case expands to several words we look for in names/descriptions.
USE_CASE_KEYWORDS = {
    "programming": ["programming", "coding", "developer", "16gb", "ryzen"],
    "coding": ["programming", "coding", "developer", "16gb", "ryzen"],
    "gaming": ["gaming", "rtx", "144hz", "bass"],
    "student": ["student", "college", "affordable", "light"],
    "travel": ["travel", "battery", "noise", "compact", "lightweight"],
    "photography": ["camera", "photography", "48mp", "200mp"],
    "music": ["music", "sound", "bass", "audio"],
    "fitness": ["fitness", "heart-rate", "sports", "tracking"],
    "home": ["home", "alexa", "security", "smart"],
}

CHEAP_WORDS = {"cheap", "cheapest", "affordable", "economical", "inexpensive"}
BEST_WORDS = {"best", "top", "rated", "premium", "flagship", "highest"}
GREETINGS = {"hi", "hii", "hello", "hey", "help", "namaste", "yo"}

STOPWORDS = {
    "a", "an", "the", "for", "me", "my", "i", "to", "of", "and", "or", "in", "on", "with",
    "find", "show", "suggest", "get", "want", "need", "looking", "look", "please", "can", "you",
    "some", "good", "is", "are", "that", "this", "it", "under", "below", "less", "than",
    "within", "upto", "up", "max", "maximum", "budget", "friendly", "rs", "inr", "best", "top",
    "recommend", "buy", "give", "which", "what", "do", "have", "any", "around", "about", "n",
    "price", "cost", "new", "latest",
}


def inr(amount: float) -> str:
    """Format a number as Indian Rupees with Indian digit grouping: 114900 -> ₹1,14,900."""
    s = str(int(round(amount)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return f"₹{s}"


def parse_budget(text: str) -> Optional[float]:
    """Find a maximum price in the text. Understands 60000, 60,000, 60k and 1.5 lakh."""
    cleaned = text.replace(",", "")
    pattern = (
        r"(?:under|below|less than|within|upto|up to|max|maximum|budget of|around|about)"
        r"\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s?(k|thousand|lakhs?|lacs?)?\b"
    )
    match = re.search(pattern, cleaned)
    if not match:
        # Fallback: a number written with a currency symbol, e.g. "₹25000".
        match = re.search(r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)\s?(k|thousand|lakhs?|lacs?)?\b", cleaned)
    if not match:
        return None

    value = float(match.group(1))
    suffix = match.group(2)
    if suffix in ("k", "thousand"):
        value *= 1_000
    elif suffix and suffix.startswith(("lakh", "lac")):
        value *= 100_000
    return value


def _tokenize(text: str) -> Set[str]:
    """Split text into lowercase words, also adding singular forms (headphones -> headphone)."""
    raw = re.findall(r"[a-z0-9]+", text)
    tokens = set(raw)
    tokens.update(t[:-1] for t in raw if len(t) > 3 and t.endswith("s"))
    return tokens


def _detect_categories(text: str, tokens: Set[str]) -> List[str]:
    found = []
    for category, words in CATEGORY_KEYWORDS.items():
        for word in words:
            if (" " in word and word in text) or word in tokens:
                found.append(category)
                break
    return found


def _score(product: Product, keywords: List[str]) -> int:
    haystack = f"{product.name} {product.description} {product.category}".lower()
    return sum(1 for k in keywords if k in haystack)


def get_recommendations(db: Session, message: str) -> Tuple[str, List[Product]]:
    """Return (reply_text, list_of_products) for a user message."""
    text = message.lower().strip()
    tokens = _tokenize(text)

    # 1) Greetings / empty intent -> friendly help message, no products.
    if tokens and tokens <= GREETINGS:
        return (
            "Hi! I'm the CartPilot demo assistant. Tell me what you're looking for, "
            "for example: \"Find me a laptop under ₹60,000 for programming\" or "
            "\"Suggest budget-friendly headphones\".",
            [],
        )

    # 2) Understand the request.
    budget = parse_budget(text)
    categories = _detect_categories(text, tokens)
    wants_cheap = bool(tokens & CHEAP_WORDS) or "budget friendly" in text or "budget-friendly" in text
    wants_best = bool(tokens & BEST_WORDS)

    # Use-case words (programming, gaming, ...) expand to extra search words.
    use_case = next((u for u in USE_CASE_KEYWORDS if u in tokens), None)
    keywords: List[str] = list(USE_CASE_KEYWORDS[use_case]) if use_case else []

    # Any other meaningful word (e.g. a brand name like "sony") is also a keyword.
    category_words = {w for words in CATEGORY_KEYWORDS.values() for w in words}
    for token in tokens:
        if (
            token not in STOPWORDS
            and token not in category_words
            and token not in CHEAP_WORDS
            and token not in BEST_WORDS
            and token not in USE_CASE_KEYWORDS
            and not token.isdigit()
            and len(token) > 2
        ):
            keywords.append(token)

    # 3) Start with products that are in stock.
    pool = db.query(Product).filter(Product.stock > 0).all()
    if categories:
        pool = [p for p in pool if p.category in categories]
    elif keywords:
        # No category given: only keep products that match at least one keyword.
        pool = [p for p in pool if _score(p, keywords) > 0]

    # Nothing to go on at all (e.g. "asdf") -> show top rated products.
    if not categories and not keywords and budget is None:
        all_products = db.query(Product).filter(Product.stock > 0).all()
        top = sorted(all_products, key=lambda p: -p.rating)[:MAX_RESULTS]
        return (
            "I'm not sure what you're looking for yet, but here are our top-rated products. "
            "Try mentioning a category (laptop, phone, headphones...) and a budget.",
            top,
        )

    # 4) Apply the budget.
    in_budget = [p for p in pool if budget is None or p.price <= budget]

    if not pool:
        return ("Sorry, I couldn't find anything matching that request in the demo catalog.", [])

    if not in_budget:
        cheapest = sorted(pool, key=lambda p: p.price)[:3]
        label = " / ".join(c.lower() for c in categories) or "products"
        return (
            f"I couldn't find any {label} under {inr(budget)}. "
            f"The most affordable options I have are listed below.",
            cheapest,
        )

    # 5) Rank the results.
    if wants_cheap:
        ranked = sorted(in_budget, key=lambda p: (p.price, -p.rating))
    elif wants_best:
        ranked = sorted(in_budget, key=lambda p: (-p.rating, -_score(p, keywords)))
    else:
        ranked = sorted(in_budget, key=lambda p: (-_score(p, keywords), -p.rating, p.price))
    top = ranked[:MAX_RESULTS]

    # 6) Build a readable reply.
    label = " / ".join(c.lower() for c in categories) or "products"
    reply = f"Here are {len(top)} {label}"
    if budget is not None:
        reply += f" under {inr(budget)}"
    if use_case:
        reply += f" that suit {use_case}"
    reply += "."
    if wants_cheap:
        reply += " I sorted them from the lowest price."
    elif wants_best:
        reply += " I sorted them by rating."
    return reply, top