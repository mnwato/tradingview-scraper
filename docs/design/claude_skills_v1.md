# Design Specification: Claude Skills Integration (v1.0)

**Status**: Planning  
**Created**: 2026-01-21  
**Phase**: 355
**Standard**: [Agent Skills](https://agentskills.io) open standard

## 1. Executive Summary

This document specifies the integration of Claude Code skills into the quantitative portfolio platform. Skills follow the **Agent Skills open standard**, which is portable across Claude Code, OpenCode, and other compatible agents.

### 1.1 Key Insight from Research

The current design in `orchestration_layer_v1.md` proposed Python-based skill implementations:

```python
# CURRENT (Wrong approach)
async def run_selection_skill(profile: str, run_id: str = None):
    from tradingview_scraper.orchestration.sdk import QuantSDK
    context = QuantSDK.run_pipeline("selection.full", ...)
```

**This is incorrect.** Claude Code skills are **not Python functions**. They are:

1. **Markdown files** (`SKILL.md`) with YAML frontmatter
2. **Instructions** that Claude reads and follows
3. **Optional scripts** that Claude can execute

### 1.2 Corrected Architecture

```
.claude/skills/                      # Claude Code discovers skills here
├── quant-select/
│   ├── SKILL.md                     # Instructions for Claude
│   └── scripts/
│       └── run_pipeline.py          # Script Claude executes
├── quant-backtest/
│   ├── SKILL.md
│   └── scripts/
│       └── run_backtest.py
└── quant-discover/
    ├── SKILL.md
    └── scripts/
        └── run_discovery.py
```

## 2. Agent Skills Standard Compliance

### 2.1 Required Structure

Every skill must have:

| Component | File | Purpose |
| :--- | :--- | :--- |
| **Skill Directory** | `.claude/skills/<name>/` | Container matching skill name |
| **SKILL.md** | `SKILL.md` | Instructions + frontmatter (required) |
| **Scripts** | `scripts/*.py` | Executable code (optional) |
| **References** | `references/*.md` | Additional docs (optional) |
| **Assets** | `assets/*` | Templates, schemas (optional) |

### 2.2 SKILL.md Frontmatter

Required fields per Agent Skills spec:

```yaml
---
name: skill-name                    # 1-64 chars, lowercase, hyphens only
description: What this skill does   # 1-1024 chars, when to use it
---
```

Optional fields:

```yaml
---
license: MIT                        # License for the skill
compatibility: Claude Code          # Environment requirements
metadata:
  author: quant-team
  version: "1.0"
allowed-tools: Bash(python:*) Read  # Pre-approved tools (experimental)
---
```

Claude Code extensions (beyond Agent Skills spec):

```yaml
---
disable-model-invocation: true      # Only user can invoke with /name
user-invocable: true                # Shows in / menu
context: fork                       # Run in subagent
agent: Explore                      # Which subagent type
---
```

### 2.3 Naming Convention

Skill names must:
- Be 1-64 characters
- Lowercase alphanumeric and hyphens only (`[a-z0-9]+(-[a-z0-9]+)*`)
- Not start or end with hyphen
- Not contain consecutive hyphens (`--`)
- Match the parent directory name

**Valid**: `quant-select`, `quant-backtest`, `portfolio-optimize`
**Invalid**: `Quant-Select`, `quant--select`, `-quant-select`

## 3. Quant Skills Design

### 3.1 Skill: quant-select

**Purpose**: Run the selection pipeline to identify winner assets.

**File**: `.claude/skills/quant-select/SKILL.md`

```markdown
---
name: quant-select
description: Run the quantitative asset selection pipeline. Use when the user wants to select assets for a portfolio, run HTR filtering, or identify winners from a universe of candidates. Supports crypto, equities, and multi-asset profiles.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: selection
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Selection Pipeline

Run the HTR v3.4 (Hierarchical Threshold Relaxation) selection pipeline to identify high-quality assets for portfolio construction.

## When to use this skill

Use this skill when the user wants to:
- Select assets for a new portfolio
- Run the selection pipeline for a specific profile
- Identify winners from a candidate universe
- Test different selection parameters

## Arguments

The skill accepts a profile name as the primary argument:

- `crypto_long` - Binance spot assets, long-only
- `crypto_short` - Binance spot assets, short-only  
- `binance_spot_rating_ma_long` - MA-based trend following
- `meta_benchmark` - Multi-sleeve meta-portfolio

## How to run

1. **Check available profiles**:
   ```bash
   cat configs/manifest.json | jq '.profiles | keys'
   ```

2. **Run the selection pipeline**:
   ```bash
   python scripts/quant_cli.py stage run selection.full \
     --profile $ARGUMENTS \
     --run-id $(date +%Y%m%d_%H%M%S)
   ```

3. **Check the results**:
   - Winners: `data/artifacts/summaries/latest/portfolio_winners.json`
   - Audit trail: `data/artifacts/summaries/latest/audit.jsonl`

## Example usage

User: "Run selection for crypto long"
→ Execute: `python scripts/quant_cli.py stage run selection.full --profile crypto_long`

User: "Select assets using the MA trend profile"
→ Execute: `python scripts/quant_cli.py stage run selection.full --profile binance_spot_rating_ma_long`

## Output

After successful execution, report:
1. Number of winners selected
2. Relaxation stage reached (1-4)
3. Path to the winners file
4. Any warnings from the audit trail

## Troubleshooting

If selection fails:
1. Check data freshness: `make data-audit`
2. Verify lakehouse exists: `ls data/lakehouse/`
3. Check for toxic data warnings in logs
```

### 3.2 Skill: quant-backtest

**Purpose**: Run backtesting on portfolio weights.

**File**: `.claude/skills/quant-backtest/SKILL.md`

```markdown
---
name: quant-backtest
description: Run backtesting simulation on portfolio weights. Use when the user wants to validate a portfolio, run historical simulation, or analyze backtest results. Supports vectorized and Nautilus simulators.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: validation
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Backtesting Pipeline

Run historical simulation on optimized portfolio weights to validate performance before live deployment.

## When to use this skill

Use this skill when the user wants to:
- Validate portfolio weights with backtesting
- Run walk-forward analysis
- Compare different optimization profiles
- Analyze Sharpe, Sortino, MaxDD metrics

## Arguments

- `run_id` - The run ID containing portfolio weights (required)
- `simulator` - Simulator type: `vectorbt`, `nautilus` (optional, default: vectorbt)

## How to run

1. **List available runs**:
   ```bash
   ls -la data/artifacts/summaries/runs/
   ```

2. **Run backtest**:
   ```bash
   python scripts/backtest_engine.py \
     --run-id $ARGUMENTS \
     --simulator vectorbt
   ```

3. **View results**:
   - Equity curve: `data/artifacts/summaries/runs/<RUN_ID>/backtest_equity.png`
   - Metrics: `data/artifacts/summaries/runs/<RUN_ID>/backtest_metrics.json`

## Example usage

User: "Backtest the latest crypto run"
→ Find latest run, then execute backtest

User: "Run Nautilus simulation on run 20260121_143022"
→ Execute: `python scripts/backtest_engine.py --run-id 20260121_143022 --simulator nautilus`

## Output

Report the following metrics:
- **Sharpe Ratio**: Risk-adjusted return
- **Sortino Ratio**: Downside risk-adjusted return
- **Max Drawdown**: Worst peak-to-trough decline
- **CAGR**: Compound annual growth rate
- **Win Rate**: Percentage of positive returns
```

### 3.3 Skill: quant-discover

**Purpose**: Discover candidate assets from exchanges.

**File**: `.claude/skills/quant-discover/SKILL.md`

```markdown
---
name: quant-discover
description: Discover candidate assets from exchanges and data sources. Use when the user wants to scan for new assets, update the candidate universe, or explore available symbols on Binance, TradingView, or other sources.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: discovery
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Discovery Pipeline

Scan exchanges and data sources to discover candidate assets for the selection pipeline.

## When to use this skill

Use this skill when the user wants to:
- Scan for new assets on Binance
- Update the candidate universe
- Explore available symbols
- Run discovery scanners

## Available scanners

- `binance_spot` - Binance spot pairs (USDT quoted)
- `binance_perp` - Binance perpetual futures
- `tradingview` - TradingView screener results
- `okx_spot` - OKX spot pairs

## How to run

1. **Run a specific scanner**:
   ```bash
   make scan-run SCANNER=binance_spot
   ```

2. **Run all configured scanners**:
   ```bash
   make scan-run
   ```

3. **Check discovered candidates**:
   ```bash
   cat data/export/latest/candidates.json | jq '. | length'
   ```

## Example usage

User: "Discover Binance spot assets"
→ Execute: `make scan-run SCANNER=binance_spot`

User: "How many candidates do we have?"
→ Check: `cat data/export/latest/candidates.json | jq '. | length'`

## Output

Report:
1. Number of candidates discovered
2. Exchanges/sources scanned
3. Path to candidates file
```

### 3.4 Skill: quant-optimize

**Purpose**: Run portfolio optimization.

**File**: `.claude/skills/quant-optimize/SKILL.md`

```markdown
---
name: quant-optimize
description: Run portfolio optimization on selected assets. Use when the user wants to optimize portfolio weights, run HRP/MinVar/MaxSharpe, or generate allocation recommendations.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: allocation
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Portfolio Optimization

Run convex optimization to determine optimal portfolio weights from selected assets.

## When to use this skill

Use this skill when the user wants to:
- Optimize portfolio weights
- Run HRP, MinVar, or MaxSharpe optimization
- Generate allocation recommendations
- Compare different risk profiles

## Optimization profiles

- `hrp` - Hierarchical Risk Parity (default, most robust)
- `min_variance` - Minimum Variance
- `max_sharpe` - Maximum Sharpe Ratio
- `equal_weight` - Equal weight baseline
- `risk_parity` - Risk Parity (ERC)

## How to run

1. **Run optimization with default profile (HRP)**:
   ```bash
   make port-optimize RUN_ID=$ARGUMENTS
   ```

2. **Run with specific profile**:
   ```bash
   python scripts/optimize_portfolio.py \
     --run-id $ARGUMENTS \
     --profile hrp
   ```

3. **View results**:
   ```bash
   cat data/artifacts/summaries/runs/<RUN_ID>/portfolio_optimized.json
   ```

## Example usage

User: "Optimize the latest run with HRP"
→ Execute: `make port-optimize RUN_ID=<latest>`

User: "Run min variance optimization"
→ Execute: `python scripts/optimize_portfolio.py --run-id <run_id> --profile min_variance`
```

## 4. Progressive Disclosure Pattern

Skills should minimize context usage through progressive disclosure:

### 4.1 Context Budget

| Level | Content | Token Budget |
| :--- | :--- | :--- |
| **Discovery** | `name` + `description` only | ~100 tokens/skill |
| **Activation** | Full `SKILL.md` body | <5000 tokens |
| **Execution** | Referenced files as needed | On-demand |

### 4.2 Best Practices

1. **Keep SKILL.md under 500 lines** - Move detailed docs to `references/`
2. **Use file references** - `See [reference](references/REFERENCE.md) for details`
3. **Bundle scripts** - Put executable code in `scripts/`, not inline
4. **Specific descriptions** - Include keywords users would naturally say

## 5. Integration with QuantSDK

Skills invoke the `QuantSDK` via scripts, not directly:

### 5.1 Script Pattern

**File**: `.claude/skills/quant-select/scripts/run_pipeline.py`

```python
#!/usr/bin/env python3
"""Script invoked by quant-select skill."""
import argparse
import sys
sys.path.insert(0, ".")  # Ensure project root is in path

from tradingview_scraper.orchestration.sdk import QuantSDK

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    
    context = QuantSDK.run_pipeline(
        "selection.full",
        params={"profile": args.profile},
        run_id=args.run_id
    )
    
    print(f"Selected {len(context.winners)} winners")
    print(f"Relaxation stage: {context.params.get('relaxation_stage', 'N/A')}")
    print(f"Audit trail: {len(context.audit_trail)} events")

if __name__ == "__main__":
    main()
```

### 5.2 CLI Integration

The `quant_cli.py` provides a unified interface that skills can invoke:

```bash
# Skills use CLI for consistency
python scripts/quant_cli.py stage run selection.ingestion --profile crypto_long
python scripts/quant_cli.py stage list --tag selection
python scripts/quant_cli.py pipeline run selection.full --profile crypto_long
```

## 6. Directory Structure

```
.claude/
├── skills/
│   ├── quant-select/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── run_pipeline.py
│   ├── quant-backtest/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── run_backtest.py
│   ├── quant-discover/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── run_discovery.py
│   ├── quant-optimize/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── run_optimize.py
│   └── quant-report/
│       ├── SKILL.md
│       └── scripts/
│           └── generate_report.py
└── commands/                        # Legacy (still works)
    └── ...
```

## 7. Invocation Patterns

### 7.1 User Invocation (Slash Command)

```
/quant-select crypto_long
/quant-backtest 20260121_143022
/quant-discover binance_spot
```

### 7.2 Model Invocation (Automatic)

When user says: "Select assets for crypto"
Claude automatically loads `quant-select` skill and follows instructions.

### 7.3 Subagent Invocation

For long-running tasks, use `context: fork`:

```yaml
---
name: quant-deep-analysis
description: Run comprehensive portfolio analysis
context: fork
agent: general-purpose
---
```

## 8. TDD Test Plan

### 8.1 Skill Validation Tests

```python
# tests/test_claude_skills.py
import yaml
from pathlib import Path

def test_skill_frontmatter_valid():
    """Verify all skills have valid frontmatter."""
    skills_dir = Path(".claude/skills")
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), f"Missing SKILL.md in {skill_dir}"
        
        content = skill_file.read_text()
        assert content.startswith("---"), f"Missing frontmatter in {skill_file}"
        
        # Extract frontmatter
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        
        # Required fields
        assert "name" in frontmatter
        assert "description" in frontmatter
        
        # Name validation
        name = frontmatter["name"]
        assert name == skill_dir.name, f"Name mismatch: {name} vs {skill_dir.name}"
        assert len(name) <= 64
        assert name.islower() or "-" in name
        assert not name.startswith("-")
        assert not name.endswith("-")
        assert "--" not in name

def test_skill_description_quality():
    """Verify descriptions are actionable."""
    skills_dir = Path(".claude/skills")
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        
        description = frontmatter.get("description", "")
        assert len(description) >= 50, f"Description too short in {skill_dir}"
        assert len(description) <= 1024, f"Description too long in {skill_dir}"
        
        # Should include action keywords
        action_keywords = ["use when", "run", "execute", "select", "analyze"]
        has_action = any(kw in description.lower() for kw in action_keywords)
        assert has_action, f"Description lacks action keywords in {skill_dir}"

def test_skill_scripts_executable():
    """Verify bundled scripts are valid Python."""
    import ast
    
    skills_dir = Path(".claude/skills")
    for skill_dir in skills_dir.iterdir():
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            continue
        
        for script in scripts_dir.glob("*.py"):
            content = script.read_text()
            try:
                ast.parse(content)
            except SyntaxError as e:
                raise AssertionError(f"Invalid Python in {script}: {e}")
```

### 8.2 Integration Tests

```python
# tests/test_skill_integration.py
import subprocess

def test_quant_select_skill_invocation():
    """Test that quant-select skill script runs."""
    result = subprocess.run(
        ["python", ".claude/skills/quant-select/scripts/run_pipeline.py",
         "--profile", "test_profile", "--run-id", "test_run"],
        capture_output=True,
        text=True
    )
    # May fail due to missing data, but should at least parse args
    assert result.returncode == 0 or "No candidates" in result.stderr
```

## 9. Implementation Order

| Step | Task | Effort |
| :--- | :--- | :--- |
| 1 | Create `.claude/skills/` directory structure | 0.5 day |
| 2 | Write `quant-select` SKILL.md and script | 0.5 day |
| 3 | Write remaining skills (backtest, discover, optimize) | 1 day |
| 4 | Create TDD tests for skill validation | 0.5 day |
| 5 | Update `quant_cli.py` to support skill invocations | 0.5 day |
| 6 | Documentation and examples | 0.5 day |

## 10. Success Criteria

- [ ] All skills pass `skills-ref validate` (Agent Skills standard)
- [ ] Skills discoverable via `/` menu in Claude Code
- [ ] `quant-select crypto_long` executes selection pipeline
- [ ] `quant-backtest <run_id>` executes backtesting
- [ ] TDD tests pass for frontmatter validation
- [ ] Skills follow progressive disclosure (< 5000 tokens each)

## 11. References

- [Agent Skills Specification](https://agentskills.io/specification)
- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [OpenCode Skills Documentation](https://opencode.ai/docs/skills/)
