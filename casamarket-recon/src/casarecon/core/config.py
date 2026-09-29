"""Typed, frozen config models for the 3 YAML files + loader. Raises ValueError naming the bad key."""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, PositiveFloat, model_validator

from casarecon.core import paths


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Causes(_Frozen):
    rounding_step_major: PositiveFloat
    fee_min_usd: PositiveFloat
    fee_min_repeats: int
    high_risk_score: PositiveFloat
    partial_tolerance_pct: PositiveFloat


class MoneyLeak(_Frozen):
    warn_pct: PositiveFloat
    crit_pct: PositiveFloat
    weekly_usd: PositiveFloat


class MinSample(_Frozen):
    alerts: int
    worst_week: int


class Thresholds(_Frozen):
    rounding_minor_units: int
    fx_tolerance_pct: PositiveFloat
    large_pct: PositiveFloat
    large_usd: PositiveFloat
    lag_outlier_days: PositiveFloat
    sensitivity_pcts: tuple[float, ...]
    causes: Causes
    money_leak: MoneyLeak
    min_sample: MinSample
    full_run_min_rows: int

    @model_validator(mode="after")
    def _order(self) -> "Thresholds":
        if self.fx_tolerance_pct >= self.large_pct:
            raise ValueError("fx_tolerance_pct must be < large_pct")
        return self


class AlertsConfig(_Frozen):
    slack: dict[str, Any]
    rules: tuple[dict[str, Any], ...]


class GeneratorConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")
    seed: int
    rows: int
    months: int


class Config(_Frozen):
    thresholds: Thresholds
    alerts: AlertsConfig
    generator: GeneratorConfig


def _read(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_config(root: Path | None = None) -> Config:
    """Read config/{thresholds,alerts,generator}.yaml under `root` (default repo root)."""
    cfg_dir = (root / "config") if root else paths.CONFIG_DIR
    return Config(
        thresholds=_read(cfg_dir / "thresholds.yaml"),
        alerts=_read(cfg_dir / "alerts.yaml"),
        generator=_read(cfg_dir / "generator.yaml"),
    )


def dbt_vars(cfg: Config | None = None) -> str:
    """JSON string for `dbt --vars`."""
    cfg = cfg or load_config()
    return json.dumps({"thresholds": cfg.thresholds.model_dump(mode="json")})
