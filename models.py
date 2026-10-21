from dataclasses import dataclass
from typing import Optional


@dataclass
class Offer:
    source: str
    external_id: str
    title: str
    current_price: float
    reference_price: Optional[float]
    url: str
    affiliate_url: str
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    category: Optional[str] = None
    product_id: Optional[int] = None
    brand: Optional[str] = None

    @property
    def discount_pct(self) -> Optional[float]:
        if self.reference_price is None or self.reference_price <= 0:
            return None
        if self.current_price >= self.reference_price:
            return None
        return (self.reference_price - self.current_price) / self.reference_price * 100.0
