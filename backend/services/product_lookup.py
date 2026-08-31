"""
Real product lookup by GTIN/EAN/UPC using free Open*Facts APIs.

Returns FULL catalog details available from the remote product record
(no invented Legal Metrology fields like MRP / consumer care).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = "PackScan-SIH26034/2.0 (local prototype; compliance screening)"

SOURCES: dict[str, str] = {
    "openfoodfacts": "https://world.openfoodfacts.org/api/v2/product/{code}.json",
    "openbeautyfacts": "https://world.openbeautyfacts.org/api/v2/product/{code}.json",
    "openproductsfacts": "https://world.openproductsfacts.org/api/v2/product/{code}.json",
    "openpetfoodfacts": "https://world.openpetfoodfacts.org/api/v2/product/{code}.json",
}

# Open*Facts may answer 404 with "product found with a different product type: X"
PRODUCT_TYPE_TO_SOURCE = {
    "food": "openfoodfacts",
    "beauty": "openbeautyfacts",
    "product": "openproductsfacts",
    "petfood": "openpetfoodfacts",
}

# Default probe order (food first, then beauty / general products / pet)
DEFAULT_SOURCE_ORDER = [
    "openfoodfacts",
    "openbeautyfacts",
    "openproductsfacts",
    "openpetfoodfacts",
]

# Prefer human-readable scalar fields first (order = display order)
DETAIL_FIELDS: list[tuple[str, str]] = [
    ("product_name", "Product name"),
    ("product_name_en", "Product name (EN)"),
    ("generic_name", "Generic name"),
    ("brands", "Brands"),
    ("brand_owner", "Brand owner"),
    ("quantity", "Quantity"),
    ("product_quantity", "Product quantity (numeric)"),
    ("product_quantity_unit", "Quantity unit"),
    ("serving_size", "Serving size"),
    ("countries", "Countries"),
    ("countries_en", "Countries (EN)"),
    ("origins", "Origins"),
    ("origins_en", "Origins (EN)"),
    ("manufacturing_places", "Manufacturing places"),
    ("emb_codes", "Packaging codes (EMB)"),
    ("stores", "Stores"),
    ("categories", "Categories"),
    ("labels", "Labels"),
    ("packaging", "Packaging"),
    ("packaging_text", "Packaging text"),
    ("allergens", "Allergens"),
    ("allergens_from_ingredients", "Allergens (from ingredients)"),
    ("traces", "Traces"),
    ("traces_from_ingredients", "Traces (from ingredients)"),
    ("ingredients_text", "Ingredients"),
    ("ingredients_text_en", "Ingredients (EN)"),
    ("ingredients_n", "Ingredient count"),
    ("additives_n", "Additives count"),
    ("nova_group", "NOVA group"),
    ("nutriscore_grade", "Nutri-Score grade"),
    ("ecoscore_grade", "Eco-Score grade"),
    ("pnns_groups_1", "PNNS group 1"),
    ("pnns_groups_2", "PNNS group 2"),
    ("food_groups", "Food groups"),
    ("product_type", "Product type"),
    ("completeness", "Data completeness"),
    ("link", "Producer link"),
    ("customer_service", "Customer service"),
    ("conservation_conditions", "Conservation conditions"),
    ("preparation", "Preparation"),
    ("warning", "Warning"),
]


def _normalize_code(code: str) -> str:
    digits = re.sub(r"\D", "", code or "")
    if len(digits) == 14 and digits.startswith("0"):
        return digits[1:]
    if len(digits) == 12:
        return "0" + digits
    return digits


def _code_candidates(code: str) -> list[str]:
    """Try common GTIN/EAN/UPC variants so OPF/OBF lookups do not miss."""
    primary = _normalize_code(code)
    digits = re.sub(r"\D", "", code or "")
    out: list[str] = []
    for c in (primary, digits):
        if c and c not in out and len(c) >= 8:
            out.append(c)
    if len(digits) == 12:
        padded = "0" + digits
        if padded not in out:
            out.append(padded)
    if len(digits) in {13, 14} and digits.startswith("0"):
        stripped = digits.lstrip("0") or digits
        if stripped not in out and len(stripped) >= 8:
            out.append(stripped)
    return out


def _http_get_json(url: str, timeout: float = 15.0) -> dict[str, Any] | None:
    """
    GET JSON from Open*Facts.

    Important: these APIs often return HTTP 404 WITH a JSON body such as
    {"status":0,"status_verbose":"product found with a different product type: product"}.
    We must parse that body — otherwise Open Products / Beauty redirects are lost.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if isinstance(data, dict):
                data.setdefault("_http_status", exc.code)
                return data
        except (json.JSONDecodeError, UnicodeError, TypeError):
            return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    return None


def _extract_redirect_source(payload: dict[str, Any]) -> str | None:
    verbose = str(payload.get("status_verbose") or "").lower()
    match = re.search(r"different product type:\s*([a-z_]+)", verbose)
    if not match:
        return None
    return PRODUCT_TYPE_TO_SOURCE.get(match.group(1))


def _as_text(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return "yes" if val else "no"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        text = val.strip()
        return text or None
    if isinstance(val, list):
        parts = []
        for item in val:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                # ingredient objects often have id/text
                t = item.get("text") or item.get("id") or item.get("name")
                if t:
                    parts.append(str(t))
        return ", ".join(parts) if parts else None
    return None


def _pick(product: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        text = _as_text(product.get(key))
        if text:
            return text
    return None


def _tags_to_text(tags: Any) -> str | None:
    if not isinstance(tags, list) or not tags:
        return None
    cleaned = []
    for t in tags:
        s = str(t)
        if s.startswith("en:"):
            s = s[3:].replace("-", " ")
        cleaned.append(s)
    return ", ".join(cleaned)


def _nutrition_rows(nutriments: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(nutriments, dict):
        return []
    # Prefer *_100g keys with readable labels
    preferred = [
        ("energy-kcal_100g", "Energy (kcal / 100g)"),
        ("energy-kj_100g", "Energy (kJ / 100g)"),
        ("fat_100g", "Fat (g / 100g)"),
        ("saturated-fat_100g", "Saturated fat (g / 100g)"),
        ("carbohydrates_100g", "Carbohydrates (g / 100g)"),
        ("sugars_100g", "Sugars (g / 100g)"),
        ("fiber_100g", "Fiber (g / 100g)"),
        ("proteins_100g", "Proteins (g / 100g)"),
        ("salt_100g", "Salt (g / 100g)"),
        ("sodium_100g", "Sodium (g / 100g)"),
    ]
    rows: list[dict[str, str]] = []
    used = set()
    for key, label in preferred:
        if key in nutriments and nutriments[key] not in (None, ""):
            rows.append({"label": label, "value": str(nutriments[key]), "key": key})
            used.add(key)
    # Append remaining scalar nutriment keys alphabetically
    for key in sorted(nutriments.keys()):
        if key in used:
            continue
        if key.endswith("_unit") or key.endswith("_label") or key.endswith("_modifier"):
            continue
        val = nutriments[key]
        if isinstance(val, (int, float, str)) and str(val).strip() != "":
            rows.append({"label": key.replace("_", " "), "value": str(val), "key": key})
    return rows


def _build_details(product: dict[str, Any]) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    seen_labels: set[str] = set()

    def add(group: str, label: str, value: str | None) -> None:
        if not value:
            return
        key = f"{group}:{label}".lower()
        if key in seen_labels:
            return
        seen_labels.add(key)
        details.append({"group": group, "label": label, "value": value})

    for field_key, label in DETAIL_FIELDS:
        add("Product", label, _pick(product, field_key))

    add("Product", "Additives tags", _tags_to_text(product.get("additives_tags")))
    add("Product", "Allergens tags", _tags_to_text(product.get("allergens_tags")))
    add("Product", "Traces tags", _tags_to_text(product.get("traces_tags")))
    add("Product", "Labels tags", _tags_to_text(product.get("labels_tags")))
    add("Product", "Categories tags", _tags_to_text(product.get("categories_tags")))
    add("Product", "Ingredients analysis", _tags_to_text(product.get("ingredients_analysis_tags")))
    add("Product", "Packaging materials", _tags_to_text(product.get("packaging_materials_tags")))
    add("Product", "Packaging shapes", _tags_to_text(product.get("packaging_shapes_tags")))
    add("Product", "States", _as_text(product.get("states")))

    # Any leftover simple string fields (A–Z dump of remaining useful scalars)
    skip_prefixes = ("image_", "last_", "created", "editor", "informers", "photographers", "correctors", "popularity", "data_quality", "languages", "schema", "interface", "rev", "scans", "unique_scans", "update_key", "max_imgid", "misc_tags", "compared_to", "entry_dates", "last_edit", "last_image", "last_modified", "last_updated", "codes_tags", "categories_properties")
    for key in sorted(product.keys()):
        if any(key.startswith(p) for p in skip_prefixes):
            continue
        if key in {f for f, _ in DETAIL_FIELDS}:
            continue
        if key.endswith("_tags") or key.endswith("_hierarchy") or key in {
            "nutriments",
            "nutriscore",
            "ecoscore_data",
            "ingredients",
            "selected_images",
            "images",
            "packagings",
            "packagings_materials",
            "nova_groups_markers",
            "ingredients_analysis",
            "data_quality_dimensions",
        }:
            continue
        val = product.get(key)
        if isinstance(val, (str, int, float)) and str(val).strip():
            add("Additional", key.replace("_", " "), str(val).strip())

    return details


def _map_product(code: str, source: str, payload: dict[str, Any]) -> dict[str, Any]:
    product = payload.get("product") or {}
    name = _pick(product, "product_name", "product_name_en", "generic_name")
    brand = _pick(product, "brands", "brand_owner")
    quantity = _pick(product, "quantity", "product_quantity")
    countries = _pick(product, "countries", "countries_en")
    categories = _pick(product, "categories")
    packaging = _pick(product, "packaging", "packaging_text")
    ingredients = _pick(product, "ingredients_text", "ingredients_text_en")
    allergens = _pick(product, "allergens", "allergens_from_ingredients")
    traces = _pick(product, "traces", "traces_from_ingredients")
    labels = _pick(product, "labels")
    nova = _pick(product, "nova_group", "nova_groups")
    nutriscore = _pick(product, "nutriscore_grade", "nutrition_grades")
    ecoscore = _pick(product, "ecoscore_grade")

    images = {
        "front": _pick(product, "image_front_url", "image_url"),
        "ingredients": _pick(product, "image_ingredients_url"),
        "nutrition": _pick(product, "image_nutrition_url"),
        "packaging": _pick(product, "image_packaging_url"),
    }

    details = _build_details(product)
    nutrition = _nutrition_rows(product.get("nutriments") or {})

    # Compliance merge helpers (full text, not truncated)
    fields: dict[str, str] = {}
    if name:
        fields["product_name"] = name
    if quantity:
        fields["net_quantity"] = quantity
    if brand:
        fields["manufacturer"] = brand
    if countries:
        fields["country_of_origin"] = countries.split(",")[0].strip()
    extras: list[str] = []
    if categories:
        extras.append(f"Categories: {categories}")
    if packaging:
        extras.append(f"Packaging: {packaging}")
    if labels:
        extras.append(f"Labels: {labels}")
    if allergens:
        extras.append(f"Allergens: {allergens}")
    if traces:
        extras.append(f"Traces: {traces}")
    if ingredients:
        extras.append(f"Ingredients: {ingredients}")
    if nova:
        extras.append(f"NOVA: {nova}")
    if nutriscore:
        extras.append(f"Nutri-Score: {nutriscore}")
    if ecoscore:
        extras.append(f"Eco-Score: {ecoscore}")
    if extras:
        fields["other_relevant_declarations"] = "; ".join(extras)

    return {
        "found": True,
        "code": code,
        "source": source,
        "name": name,
        "brand": brand,
        "quantity": quantity,
        "countries": countries,
        "categories": categories,
        "packaging": packaging,
        "image_url": images.get("front"),
        "images": images,
        "ingredients": ingredients,
        "allergens": allergens,
        "traces": traces,
        "labels": labels,
        "nova_group": nova,
        "nutriscore_grade": nutriscore,
        "ecoscore_grade": ecoscore,
        "details": details,
        "nutrition": nutrition,
        "fields": fields,
        "message": f"Full product catalog loaded from {source}.",
        "missing_legal_metrology_note": (
            "Catalog databases usually do NOT include MRP, manufacturing/packing date, "
            "or consumer-care contacts required under Legal Metrology. "
            "Photograph the package back/side label for those declarations."
        ),
    }


def _ean13_checksum_ok(code: str) -> bool | None:
    digits = re.sub(r"\D", "", code or "")
    if len(digits) != 13 or not digits.isdigit():
        return None
    body = digits[:12]
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    expected = (10 - (total % 10)) % 10
    return expected == int(digits[12])


def _gs1_region_hint(code: str) -> str | None:
    digits = re.sub(r"\D", "", code or "")
    if len(digits) < 3:
        return None
    prefix = digits[:3]
    # Common GS1 country prefixes relevant to Indian packaged goods demos
    if prefix.startswith("890"):
        return "GS1 India (890...)"
    if prefix.startswith(("000", "001", "002", "003", "004", "005", "006", "007", "008", "009", "010", "011", "012", "013", "019")):
        return "GS1 US/Canada prefix"
    if prefix.startswith(("30", "31", "32", "33", "34", "35", "36", "37")):
        return "GS1 France prefix"
    return f"GS1 prefix {prefix}"


def _fetch_from_source(source: str, barcode: str) -> dict[str, Any] | None:
    template = SOURCES.get(source)
    if not template:
        return None
    return _http_get_json(template.format(code=barcode))


def lookup_product_by_barcode(code: str) -> dict[str, Any]:
    candidates = _code_candidates(code)
    display_code = candidates[0] if candidates else (code or "")
    empty = {
        "found": False,
        "code": display_code,
        "source": None,
        "fields": {},
        "details": [],
        "nutrition": [],
        "images": {},
        "message": "Product not found in Open Food / Beauty / Products / Pet Food Facts.",
        "missing_legal_metrology_note": (
            "No catalog match. Continue with label OCR for MRP / Net Qty / Manufacturer / Care details."
        ),
    }
    if not candidates:
        empty["message"] = "Barcode too short for product lookup."
        return empty

    tried: list[str] = []
    not_found_sources: list[str] = []
    unreachable_sources: list[str] = []
    other_notes: list[str] = []

    for barcode in candidates:
        # Start with food, but jump immediately when API says product lives elsewhere.
        queue = list(DEFAULT_SOURCE_ORDER)
        seen_sources: set[str] = set()

        while queue:
            source = queue.pop(0)
            if source in seen_sources:
                continue
            seen_sources.add(source)
            tried.append(f"{source}:{barcode}")

            data = _fetch_from_source(source, barcode)
            if not data:
                unreachable_sources.append(source)
                continue

            if int(data.get("status") or 0) == 1 and data.get("product"):
                return _map_product(barcode, source, data)

            redirect = _extract_redirect_source(data)
            if redirect and redirect not in seen_sources:
                queue.insert(0, redirect)
                other_notes.append(f"{source} → {redirect}")
                continue

            verbose = str(data.get("status_verbose") or "").strip().lower()
            http_status = data.get("_http_status")
            if "not found" in verbose or int(data.get("status") or 0) == 0:
                not_found_sources.append(source)
            elif http_status and int(http_status) >= 500:
                unreachable_sources.append(source)
            elif verbose:
                other_notes.append(f"{source}: {verbose}")

    checksum = _ean13_checksum_ok(display_code)
    region = _gs1_region_hint(display_code)
    parts = [
        f"Barcode {display_code} was read correctly",
    ]
    if checksum is True:
        parts.append("EAN-13 checksum is valid")
    elif checksum is False:
        parts.append("EAN-13 checksum is INVALID (re-check digits)")
    if region:
        parts.append(f"prefix maps to {region}")
    parts.append(
        "this GTIN is not listed yet in Open Food / Beauty / Products / Pet Food Facts"
    )
    if not_found_sources:
        parts.append(
            "(confirmed missing in: " + ", ".join(dict.fromkeys(not_found_sources)) + ")"
        )
    if unreachable_sources:
        parts.append(
            "(temporary server issues: "
            + ", ".join(dict.fromkeys(unreachable_sources))
            + " — retry later)"
        )
    parts.append(
        "Many Indian retail SKUs are not crowd-sourced there yet. "
        "This is not a scanner bug - continue with package label OCR for Legal Metrology fields."
    )
    empty["message"] = ". ".join(parts)
    empty["tried"] = tried
    empty["checksum_valid"] = checksum
    empty["gs1_region"] = region
    if other_notes:
        empty["lookup_notes"] = other_notes[-6:]
    return empty


def merge_lookup_into_declarations(
    declarations: list[dict[str, Any]],
    lookup: dict[str, Any],
) -> list[dict[str, Any]]:
    if not lookup.get("found"):
        return declarations
    catalog: dict[str, str] = lookup.get("fields") or {}
    if not catalog:
        return declarations

    out: list[dict[str, Any]] = []
    for row in declarations:
        key = row.get("field_key")
        has_value = bool(row.get("value"))
        status = (row.get("status") or "").upper()
        if key in catalog and (not has_value or status in {"NOT_DETECTED", "NOT_APPLICABLE"}):
            merged = dict(row)
            merged["value"] = catalog[key]
            merged["confidence"] = max(float(row.get("confidence") or 0), 0.7)
            merged["status"] = "DETECTED"
            merged["source"] = f"barcode:{lookup.get('source')}"
            out.append(merged)
        else:
            out.append(row)
    return out
