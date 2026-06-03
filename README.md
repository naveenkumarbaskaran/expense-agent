# Expense Agent AI

An AI-powered expense auditor built with the Anthropic SDK (Claude). It reads expense CSV files, categorizes each transaction, detects policy violations, and generates a detailed markdown audit report.

## Features

- Automatic transaction categorization using Claude
- Policy violation detection:
  - Over per-diem limit
  - Missing receipt flag (transactions above threshold)
  - Disallowed expense category
  - Weekend spend rule enforcement
- Configurable policy via YAML
- Rich CLI with progress display
- Markdown audit report with executive summary, per-transaction table, and recommendations

## Installation

```bash
pip install expense-agent-ai
# or, from source:
pip install -e .
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

### Audit expenses

```bash
# Basic audit with default policy
expense-agent audit expenses.csv

# With custom policy and output path
expense-agent audit expenses.csv --policy policy.yaml --output audit-report.md
```

### Show current policy

```bash
expense-agent show-policy
expense-agent show-policy --policy policy.yaml
```

## CSV Format

The expense CSV must contain these columns (case-insensitive):

| Column | Type | Example |
|-------------|--------|-----------------------------|
| date | string | 2024-01-15 |
| merchant | string | Delta Airlines |
| amount | float | 342.50 |
| description | string | Flight to NYC client meeting |

Example `expenses.csv`:

```csv
date,merchant,amount,description
2024-01-15,Delta Airlines,342.50,Flight to NYC client meeting
2024-01-15,Hilton Hotel,189.00,Hotel stay NYC
2024-01-16,Nobu Restaurant,220.00,Client dinner
2024-01-17,Uber,28.50,Airport transfer
2024-01-20,Amazon,15.99,Office pens and notepads
2024-01-21,Best Buy,899.00,New monitor
```

## Policy Configuration

Create a `policy.yaml` to override defaults:

```yaml
# Per-diem spending limits (USD)
per_diem_limits:
  meals: 75.00
  travel: 500.00
  accommodation: 250.00
  entertainment: 100.00
  office_supplies: 50.00
  software: 200.00
  training: 500.00
  miscellaneous: 25.00

# Permitted expense categories
category_allowlist:
  - meals
  - travel
  - accommodation
  - entertainment
  - office_supplies
  - software
  - training
  - miscellaneous

# Explicitly forbidden categories
disallowed_categories:
  - alcohol
  - gambling
  - personal_care

# Receipt required above this amount (USD)
require_receipt_above: 25.00

# Weekend spending rules
weekend_spend_allowed: false
weekend_spend_categories:
  - meals
  - travel
```

## Architecture

```
expense_agent/
   __init__.py       Package exports
   agent.py          ExpenseAgent with Claude tool-use agentic loop
   policy.py         ExpensePolicy: rules, limits, YAML loader
   cli.py            Click CLI: audit, show-policy commands
```

### How it works

1. The CLI constructs an `ExpenseAgent` with the loaded `ExpensePolicy`.
2. `ExpenseAgent.audit()` sends a task prompt to Claude with three tools available:
   - `read_csv(path)` — loads the expense file and returns rows as JSON
   - `write_file(path, content)` — writes the final markdown report
   - `lookup_policy(category)` — returns policy limits/flags for a category
3. Claude drives an agentic loop: reads the CSV, categorizes each row, looks up policy rules, identifies violations, and writes the report.
4. The loop exits when Claude returns `stop_reason = "end_turn"` (no more tool calls).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy expense_agent/
```

## License

MIT
