from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class HistoryContext:
    count: int
    average: float | None
    minimum: float | None
    maximum: float | None
    median: float | None

    @property
    def reliable(self) -> bool:
        return self.count >= 3

    @property
    def confidence(self) -> float:
        if self.count <= 0:
            return 0.0
        if self.count < 3:
            return 0.25
        if self.count < 7:
            return 0.50
        if self.count < 14:
            return 0.75
        return 1.0


def build_history_context(rows) -> HistoryContext:
    prices = [float(row[0]) for row in rows]
    if not prices:
        return HistoryContext(0, None, None, None, None)
    return HistoryContext(
        len(prices),
        sum(prices) / len(prices),
        min(prices),
        max(prices),
        median(prices),
    )


def relative_price(current_price: float, history: HistoryContext) -> dict:
    result = {
        "vs_average_pct": None,
        "vs_minimum_pct": None,
        "is_new_low": False,
    }
    if history.average and history.average > 0:
        result["vs_average_pct"] = (history.average - current_price) / history.average * 100.0
    if history.minimum and history.minimum > 0:
        result["vs_minimum_pct"] = (history.minimum - current_price) / history.minimum * 100.0
        result["is_new_low"] = current_price < history.minimum
    return result
