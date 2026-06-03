"""ExpenseAgent: categorizes transactions and detects policy violations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anthropic
import pandas as pd

from .policy import ExpensePolicy

MODEL = "claude-sonnet-4-6"


class ExpenseAgent:
    """AI-powered expense auditor.

    Uses Claude with tool use to:
    1. Read an expense CSV.
    2. Categorize each transaction.
    3. Flag policy violations.
    4. Write a markdown audit report.
    """

    def __init__(self, policy: ExpensePolicy | None = None) -> None:
        self.policy = policy or ExpensePolicy()
        self.client = anthropic.Anthropic()
        self._tools = self._build_tools()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def audit(self, csv_path: str, output_path: str) -> str:
        """Run a full expense audit.

        Parameters
        ----------
        csv_path:
            Path to the expense CSV file (columns: date, merchant, amount, description).
        output_path:
            Where to write the markdown audit report.

        Returns
        -------
        The path to the generated report.
        """
        system_prompt = self._build_system_prompt()
        user_message = (
            f"Please audit the expenses in '{csv_path}'. "
            f"Use the read_csv tool to load the data, categorize every row, "
            f"check each transaction against the policy, "
            f"then write a complete markdown audit report to '{output_path}' "
            f"using the write_file tool."
        )

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]

        # Agentic loop
        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=system_prompt,
                tools=self._tools,
                messages=messages,
            )

            # Append assistant turn
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                tool_results = self._handle_tool_calls(response.content)
                messages.append({"role": "user", "content": tool_results})
                continue

            # Any other stop reason — bail
            break

        return output_path

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def _handle_tool_calls(
        self, content_blocks: list[Any]
    ) -> list[dict[str, Any]]:
        """Execute all tool_use blocks and return tool_result blocks."""
        results: list[dict[str, Any]] = []
        for block in content_blocks:
            if block.type != "tool_use":
                continue
            tool_input: dict[str, Any] = block.input
            try:
                if block.name == "read_csv":
                    output = self._tool_read_csv(tool_input["path"])
                elif block.name == "write_file":
                    output = self._tool_write_file(
                        tool_input["path"], tool_input["content"]
                    )
                elif block.name == "lookup_policy":
                    output = self._tool_lookup_policy(tool_input["category"])
                else:
                    output = f"Unknown tool: {block.name}"
                is_error = False
            except Exception as exc:  # noqa: BLE001
                output = f"Error: {exc}"
                is_error = True

            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error,
                }
            )
        return results

    def _tool_read_csv(self, path: str) -> str:
        """Read a CSV and return its contents as JSON."""
        df = pd.read_csv(path)
        # Normalise column names
        df.columns = [c.strip().lower() for c in df.columns]
        required = {"date", "merchant", "amount", "description"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")
        records = df.to_dict(orient="records")
        return json.dumps(records, default=str)

    def _tool_write_file(self, path: str, content: str) -> str:
        """Write content to a file."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return f"File written successfully: {path} ({len(content)} characters)"

    def _tool_lookup_policy(self, category: str) -> str:
        """Return policy details for a specific category."""
        cat = category.lower().strip()
        limit = self.policy.per_diem_limits.get(cat)
        allowed = cat in [c.lower() for c in self.policy.category_allowlist]
        disallowed = cat in [c.lower() for c in self.policy.disallowed_categories]

        info: dict[str, Any] = {
            "category": cat,
            "allowed": allowed and not disallowed,
            "disallowed": disallowed,
            "per_diem_limit_usd": limit,
            "receipt_required_above_usd": self.policy.require_receipt_above,
            "weekend_spend_allowed": (
                self.policy.weekend_spend_allowed
                or cat in [c.lower() for c in self.policy.weekend_spend_categories]
            ),
        }
        return json.dumps(info)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return f"""You are an expert expense auditor. Your job is to:
1. Read expense CSV data using the read_csv tool.
2. Categorize each transaction into one of the allowed expense categories.
3. Check each transaction against the company expense policy.
4. Flag any violations (over-limit spend, missing receipt flag, disallowed category, 
   suspicious weekend spend, etc.).
5. Generate a comprehensive markdown audit report and save it with write_file.

The report must include:
- An executive summary with total spend, violation count, and compliance rate.
- A per-transaction table with columns: Date, Merchant, Amount, Category, Status, Issues.
- A violations section listing each violation with details.
- A category breakdown with totals.
- Recommendations.

Use the lookup_policy tool whenever you need policy details for a specific category.

{self.policy.to_prompt_description()}

Be thorough, accurate, and professional."""

    def _build_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "read_csv",
                "description": (
                    "Read an expense CSV file and return its rows as JSON. "
                    "The CSV must have columns: date, merchant, amount, description."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Filesystem path to the CSV file.",
                        }
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write text content to a file at the given path.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Destination file path (created if it does not exist).",
                        },
                        "content": {
                            "type": "string",
                            "description": "Text content to write.",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "lookup_policy",
                "description": (
                    "Look up expense policy details for a specific category. "
                    "Returns JSON with allowed status, per-diem limit, receipt requirements, "
                    "and weekend rules."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Expense category name (e.g. 'meals', 'travel').",
                        }
                    },
                    "required": ["category"],
                },
            },
        ]
