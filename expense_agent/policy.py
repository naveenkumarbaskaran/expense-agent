"""Expense policy rules and configuration."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Default per-diem limits in USD
DEFAULT_LIMITS: dict[str, float] = {
    "meals": 75.0,
    "travel": 500.0,
    "accommodation": 250.0,
    "entertainment": 100.0,
    "office_supplies": 50.0,
    "software": 200.0,
    "training": 500.0,
    "miscellaneous": 25.0,
}

# Default allowed categories
DEFAULT_ALLOWLIST: list[str] = [
    "meals",
    "travel",
    "accommodation",
    "entertainment",
    "office_supplies",
    "software",
    "training",
    "miscellaneous",
]


@dataclass
class ExpensePolicy:
    """Configurable expense policy rules.

    Attributes:
        per_diem_limits: Maximum allowed spend per category (USD).
        category_allowlist: Categories that are permitted.
        disallowed_categories: Categories that are explicitly forbidden.
        require_receipt_above: Require receipt flag for amounts above this threshold.
        weekend_spend_allowed: Whether weekend transactions are allowed.
        weekend_spend_categories: Categories allowed on weekends even if weekend_spend_allowed=False.
    """

    per_diem_limits: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_LIMITS))
    category_allowlist: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWLIST))
    disallowed_categories: list[str] = field(default_factory=list)
    require_receipt_above: float = 25.0
    weekend_spend_allowed: bool = True
    weekend_spend_categories: list[str] = field(default_factory=lambda: ["meals", "travel"])

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ExpensePolicy":
        """Load policy from a YAML file."""
        with open(path, "r") as fh:
            data: dict[str, Any] = yaml.safe_load(fh) or {}

        policy = cls()

        if "per_diem_limits" in data:
            policy.per_diem_limits = {k: float(v) for k, v in data["per_diem_limits"].items()}

        if "category_allowlist" in data:
            policy.category_allowlist = [str(c) for c in data["category_allowlist"]]

        if "disallowed_categories" in data:
            policy.disallowed_categories = [str(c) for c in data["disallowed_categories"]]

        if "require_receipt_above" in data:
            policy.require_receipt_above = float(data["require_receipt_above"])

        if "weekend_spend_allowed" in data:
            policy.weekend_spend_allowed = bool(data["weekend_spend_allowed"])

        if "weekend_spend_categories" in data:
            policy.weekend_spend_categories = [str(c) for c in data["weekend_spend_categories"]]

        return policy

    def to_prompt_description(self) -> str:
        """Return a human-readable description of the policy for use in prompts."""
        lines = ["EXPENSE POLICY RULES:"]

        lines.append("\nPer-diem limits (USD):")
        for cat, limit in self.per_diem_limits.items():
            lines.append(f"  {cat}: ${limit:.2f}")

        lines.append("\nAllowed categories: " + ", ".join(self.category_allowlist))

        if self.disallowed_categories:
            lines.append("Disallowed categories: " + ", ".join(self.disallowed_categories))

        lines.append(f"\nReceipt required for transactions above: ${self.require_receipt_above:.2f}")
        lines.append(f"Weekend spending allowed: {self.weekend_spend_allowed}")
        if not self.weekend_spend_allowed:
            lines.append(
                "Weekend exceptions: " + ", ".join(self.weekend_spend_categories)
            )

        return "\n".join(lines)
