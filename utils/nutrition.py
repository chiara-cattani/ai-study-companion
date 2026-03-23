"""
Nutrition data lookup via OpenFoodFacts API.
Adapted from AI-food-tracker for integration into Study Companion AI.
"""
import time
import functools
from difflib import SequenceMatcher

import requests

SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

FALLBACK_NUTRITION = {
    "kcal": 150.0,
    "protein": 8.0,
    "fat": 5.0,
    "carbs": 18.0,
}


def _normalize(name: str) -> str:
    return " ".join(name.lower().strip().split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _score_product(product: dict, query: str) -> float:
    n = product.get("nutriments", {})
    name = product.get("product_name", "")
    sim = _similarity(query, name) if name else 0.0
    fields = ["energy-kcal_100g", "proteins_100g", "fat_100g", "carbohydrates_100g"]
    present = sum(1 for f in fields if n.get(f) is not None)
    completeness = present / len(fields)
    has_kcal = 1.0 if (n.get("energy-kcal_100g") or n.get("energy_100g")) else 0.0
    return sim * 0.4 + completeness * 0.4 + has_kcal * 0.2


@functools.lru_cache(maxsize=512)
def search_nutrition(food_name: str) -> tuple:
    """Query OpenFoodFacts for nutrition data per 100g.

    Returns (nutrition_dict, matched_product_name | None, source_string).
    nutrition_dict keys: kcal, protein, fat, carbs (all per 100g).
    source_string is 'openfoodfacts' or 'fallback'.
    """
    normalized = _normalize(food_name)
    params = {
        "search_terms": normalized,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5,
        "fields": "product_name,nutriments",
    }

    data = None
    for attempt in range(2):
        try:
            resp = requests.get(SEARCH_URL, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            break
        except (requests.RequestException, ValueError):
            if attempt < 1:
                time.sleep(0.5)

    if data is None:
        return (dict(FALLBACK_NUTRITION), None, "fallback")

    products = data.get("products", [])
    if not products:
        return (dict(FALLBACK_NUTRITION), None, "fallback")

    scored = [(p, _score_product(p, normalized)) for p in products]
    scored.sort(key=lambda x: x[1], reverse=True)

    for product, _score in scored:
        n = product.get("nutriments", {})
        kcal = n.get("energy-kcal_100g") or n.get("energy_100g")
        if kcal is None:
            continue
        return (
            {
                "kcal": float(kcal),
                "protein": float(n.get("proteins_100g") or 0),
                "fat": float(n.get("fat_100g") or 0),
                "carbs": float(n.get("carbohydrates_100g") or 0),
            },
            product.get("product_name", ""),
            "openfoodfacts",
        )

    return (dict(FALLBACK_NUTRITION), None, "fallback")


def build_food_item(
    food_name: str,
    grams: float,
    status: str = "manually_added",
    confidence: float = 1.0,
) -> dict:
    """Build a food item dict with nutrition looked up from OpenFoodFacts.

    The item stores both per-100g values (for gram adjustments) and
    pre-computed serving values.
    """
    nutrition, _matched, source = search_nutrition(food_name)
    return {
        "food_name": food_name,
        "grams": grams,
        "kcal_per_100g": nutrition["kcal"],
        "protein_per_100g": nutrition["protein"],
        "fat_per_100g": nutrition["fat"],
        "carbs_per_100g": nutrition["carbs"],
        "calories": round(nutrition["kcal"] * grams / 100, 1),
        "protein": round(nutrition["protein"] * grams / 100, 1),
        "fat": round(nutrition["fat"] * grams / 100, 1),
        "carbs": round(nutrition["carbs"] * grams / 100, 1),
        "status": status,
        "confidence": confidence,
        "nutrition_source": source,
    }


def recompute_nutrition(item: dict) -> dict:
    """Recompute serving nutrition in-place from per-100g values and current grams."""
    grams = item["grams"]
    item["calories"] = round(item["kcal_per_100g"] * grams / 100, 1)
    item["protein"] = round(item["protein_per_100g"] * grams / 100, 1)
    item["fat"] = round(item["fat_per_100g"] * grams / 100, 1)
    item["carbs"] = round(item["carbs_per_100g"] * grams / 100, 1)
    return item
