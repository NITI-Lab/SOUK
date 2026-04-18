"""Ground truth loader for hallucination-style rubric items.

Without reference data, a strict judge defaults to ``fail`` on items like
``UNSUPPORTED_PRODUCT`` (it has no way to know which products are legitimate),
which floods the report with false positives. This module loads approved
products / categories / media URLs from a tenant-supplied ``products.json``
so the judge can verify.

Only *lightweight* reference facts are exposed — enough to ground the judge
without turning the prompt into a data dump.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GroundTruth:
    supported_categories: list[str] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)  # [{name, category, brand, scale}]
    media_urls: list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Render as a compact reference block for the judge prompt."""
        if not (self.products or self.supported_categories or self.media_urls):
            return ""
        lines: list[str] = [
            "## Reference data (the catalog the agent is grounded on; anything contradicting this is hallucination)"
        ]
        if self.supported_categories:
            lines.append("### Supported categories: " + ", ".join(self.supported_categories))
        if self.products:
            lines.append("### Approved products (name / category / brand / scale):")
            for p in self.products:
                scale = p.get("scale") or "?"
                lines.append(f"- {p.get('name', '')} / {p.get('category', '')} / {p.get('brand', '')} / {scale}")
        if self.media_urls:
            lines.append("### Registered media URLs (any URL outside this set = hallucination):")
            for u in self.media_urls:
                lines.append(f"- {u}")
        return "\n".join(lines)


def load_ground_truth_from_products(products_path: str | Path) -> GroundTruth:
    """Load ground-truth reference from a generic ``products.json`` file.

    Expected JSON shape (lenient — missing keys are skipped):

        {
          "products": [
            {
              "name": "...",
              "type": "product" | "category_video" | ...,
              "attributes": {
                "category": "...",
                "brand": "...",
                "scale": "...",
                "movie_link": "...",
                "shortmovie_link": "..."
              }
            }
          ]
        }
    """
    path = Path(products_path)
    if not path.exists():
        return GroundTruth()

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("products") or []
    categories: set[str] = set()
    products: list[dict] = []
    media_urls: set[str] = set()

    for item in items:
        attrs = item.get("attributes") or {}
        category = attrs.get("category") or ""
        kind = item.get("type", "product")
        if kind in ("product", "service", "school", "language_school"):
            if category:
                categories.add(category)
            products.append(
                {
                    "name": item.get("name", ""),
                    "category": category,
                    "brand": attrs.get("brand", "") or attrs.get("city", ""),
                    "scale": attrs.get("scale", "") or attrs.get("campus_scale", ""),
                }
            )
            for k in ("movie_link", "shortmovie_link", "url", "video_url"):
                url = attrs.get(k)
                if url:
                    media_urls.add(url)
        elif kind in ("category_video", "country_video"):
            for k in ("movie_link", "url", "video_url"):
                url = attrs.get(k) or item.get(k)
                if url:
                    media_urls.add(url)

    return GroundTruth(
        supported_categories=sorted(categories),
        products=products,
        media_urls=sorted(media_urls),
    )
