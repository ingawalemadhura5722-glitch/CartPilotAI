"""
Database-side product search and ranking.

Gemini never searches or ranks products. It only describes what the user wants
(a ShoppingIntent). This module turns that into a real, deterministic search
over products that exist in the database.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

from app.models.product import Product
from app.models.schemas import ShoppingIntent

MAX_RESULTS = 4

_STOPWORDS = {
    "a", "an", "the", "for", "me", "my", "i", "to", "of", "and", "or", "in", "on", "with",
    "is", "are", "it", "this", "that", "good", "best", "need", "want", "find", "show",
    "under", "below", "above", "than", "very", "more", "most", "any", "some", "also",
}


def format_inr(amount: float) -> str:
    """114900 -> ₹1,14,900 (Indian digit grouping)."""
    s = str(int(round(amount)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups: List[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return f"₹{s}"


def normalize_text(text: str) -> str:
    """Lowercase and glue numbers to units: '16 GB' -> '16gb'."""
    return re.sub(r"(\d)\s+(gb|tb|mb|mp|hz|mah|w|inch)\b", r"\1\2", text.lower())


def text_tokens(text: str) -> Set[str]:
    """Meaningful lowercase words in a text, plus simple singular forms."""
    raw = re.findall(r"[a-z0-9]+", normalize_text(text))
    tokens = {t for t in raw if len(t) >= 2 and t not in _STOPWORDS}
    tokens.update(t[:-1] for t in list(tokens) if len(t) > 3 and t.endswith("s"))
    return tokens


def best_value_first(products: List[Product]) -> List[Product]:
    """Order products by a simple value score: high rating and low price."""
    if len(products) <= 1:
        return list(products)

    prices = [p.price for p in products]
    ratings = [p.rating for p in products]
    p_lo, p_hi, r_lo, r_hi = min(prices), max(prices), min(ratings), max(ratings)

    def norm(value: float, lo: float, hi: float) -> float:
        return 0.5 if hi == lo else (value - lo) / (hi - lo)

    def value_score(p: Product) -> float:
        return 0.6 * norm(p.rating, r_lo, r_hi) + 0.4 * (1 - norm(p.price, p_lo, p_hi))

    return sorted(products, key=lambda p: (-value_score(p), -p.rating, p.price))


@dataclass
class SearchResult:
    products: List[Product] = field(default_factory=list)
    relaxed: List[str] = field(default_factory=list)       # requirements we had to relax
    no_match_facts: Dict = field(default_factory=dict)      # facts for an honest "nothing found" reply


def _within_budget(product: Product, intent: ShoppingIntent) -> bool:
    if intent.min_budget is not None and product.price < intent.min_budget:
        return False
    if intent.max_budget is not None and product.price > intent.max_budget:
        return False
    return True


def _brand_match(product: Product, brands: List[str]) -> bool:
    return any(re.search(rf"\b{re.escape(b)}\b", product.name, re.IGNORECASE) for b in brands)


def _term_weights(intent: ShoppingIntent) -> Dict[str, int]:
    """Words we look for in product text. Explicit specs/features count double."""
    weights: Dict[str, int] = {}
    for phrase in intent.specs + intent.features:
        for token in text_tokens(phrase):
            weights[token] = 2
    if intent.usage:
        for token in text_tokens(intent.usage):
            weights.setdefault(token, 1)
    for keyword in intent.keywords:
        for token in text_tokens(keyword):
            weights.setdefault(token, 1)
    return weights


def _score(product: Product, weights: Dict[str, int]) -> int:
    haystack = text_tokens(f"{product.name} {product.description} {product.category}")
    return sum(weight for token, weight in weights.items() if token in haystack)


def search_products(catalog: List[Product], intent: ShoppingIntent, limit: int = MAX_RESULTS) -> SearchResult:
    """
    Filter by stock, category, budget and brand, then rank.
    Out-of-stock products are never recommended.
    """
    result = SearchResult()

    in_stock = [p for p in catalog if p.stock > 0]
    in_category = [p for p in in_stock if not intent.category or p.category == intent.category]
    in_budget = [p for p in in_category if _within_budget(p, intent)]

    candidates = in_budget

    # Brand: hard filter, but relax it (and say so) if the category has other options.
    if intent.brands and in_budget:
        branded = [p for p in in_budget if _brand_match(p, intent.brands)]
        if branded:
            candidates = branded
        elif intent.category:
            result.relaxed.append("brand")
        else:
            candidates = []  # a brand with no category and no match: show nothing

    # Without a category, only keep products that match at least one keyword.
    weights = _term_weights(intent)
    if not intent.category and not intent.brands and weights:
        candidates = [p for p in candidates if _score(p, weights) > 0]

    if not candidates:
        facts: Dict = {"available_categories": sorted({p.category for p in catalog})}
        if intent.category:
            facts["in_stock_products_in_category"] = len(in_category)
            if in_category:
                cheapest = min(in_category, key=lambda p: p.price)
                priciest = max(in_category, key=lambda p: p.price)
                facts["cheapest_in_category"] = {"name": cheapest.name, "price": format_inr(cheapest.price)}
                facts["priciest_in_category"] = {"name": priciest.name, "price": format_inr(priciest.price)}
                facts["budget_is_the_problem"] = not in_budget
                facts["brands_available_in_category"] = sorted({p.name.split()[0] for p in in_category})
        result.relaxed = []
        result.no_match_facts = facts
        return result

    # Ranking
    if intent.sort_preference == "price_low":
        ranked = sorted(candidates, key=lambda p: (p.price, -_score(p, weights), -p.rating))
    elif intent.sort_preference == "rating":
        ranked = sorted(candidates, key=lambda p: (-p.rating, -_score(p, weights), p.price))
    elif intent.sort_preference == "value":
        ranked = best_value_first(candidates)
    else:
        ranked = sorted(candidates, key=lambda p: (-_score(p, weights), -p.rating, p.price))

    result.products = ranked[:limit]
    return result


def pick_products_to_compare(
    catalog: List[Product], intent: ShoppingIntent, previous: List[Product]
) -> List[Product]:
    """
    Decide which products to compare:
    1. IDs the AI named (only if they were shown earlier in this conversation),
    2. otherwise the products shown in the previous assistant message,
    3. otherwise the top-rated products for the requested category ("best two laptops").
    """
    previous_by_id = {p.id: p for p in previous}

    chosen = [previous_by_id[i] for i in intent.compare_product_ids if i in previous_by_id]

    if not chosen and intent.use_previous_products:
        chosen = list(previous)

    if not chosen and (intent.category or intent.brands or intent.keywords or intent.features):
        top_rated = intent.model_copy(update={"sort_preference": "rating"})
        chosen = search_products(catalog, top_rated, limit=intent.compare_count).products

    return chosen[:MAX_RESULTS]