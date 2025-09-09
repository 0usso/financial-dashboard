"""Module de Recherche Opérationnelle / Science de la Décision

Fonctionnalité principale : optimisation de l'allocation d'un volume cible entre
les différentes banques (maker_bank) pour minimiser un coût attendu (taux) tout
en respectant des contraintes de diversification.

Approche : Programmation Linéaire (PuLP)

Variables
---------
 x_m : volume à allouer au maker m

Objectif
--------
 Minimiser  Σ ( (avg_rate_m + risk_aversion * std_rate_m) * x_m )
  - avg_rate_m : taux moyen historique par maker (proxy du coût)
  - std_rate_m : écart type historique (proxy du risque / incertitude)

Contraintes
-----------
 1. Σ x_m = target_volume
 2. min_share * target_volume <= x_m <= max_share * target_volume
 3. x_m <= capacity_m   (capacity_m = percentile historique de volume journalier)

Retour
------
 DataFrame détaillant l'allocation optimale + métriques de coût.

Notes
-----
 - Le modèle est volontairement simple pour rester interprétable.
 - S'il n'y a pas assez de capacité pour satisfaire le volume cible, une erreur explicite est levée.
 - Si PuLP n'est pas installé, une exception claire est renvoyée pour que l'UI puisse afficher un message.
"""

from __future__ import annotations
import pandas as pd
from typing import Tuple

try:
    import pulp  # type: ignore
except Exception as e:  # pragma: no cover - environnement sans pulp
    pulp = None  # UI gèrera ce cas


class OptimizationError(Exception):
    """Erreur spécifique à l'optimisation d'allocation."""


def _prepare_maker_stats(df: pd.DataFrame, capacity_percentile: float = 0.95) -> pd.DataFrame:
    """Calcule les statistiques par maker nécessaires à l'optimisation.

    Parameters
    ----------
    df : DataFrame contenant au moins maker_bank, amount, rate, trade_date
    capacity_percentile : float, percentile utilisé pour estimer la capacité max journalière

    Returns
    -------
    DataFrame indexé par maker_bank avec colonnes:
        avg_rate, std_rate, daily_max_pctile (capacity), total_volume
    """
    needed = {"maker_bank", "amount", "rate", "trade_date"}
    missing = needed - set(df.columns)
    if missing:
        raise OptimizationError(f"Colonnes manquantes pour les stats makers: {', '.join(sorted(missing))}")

    # Moyenne & écart-type des taux
    stats_rate = df.groupby("maker_bank")["rate"].agg(["mean", "std"]).rename(columns={"mean": "avg_rate", "std": "std_rate"})

    # Volume total (pour information / baseline)
    total_vol = df.groupby("maker_bank")["amount"].sum().rename("total_volume")

    # Capacités : calcul du volume quotidien par maker, puis percentile
    daily = df.groupby(["trade_date", "maker_bank"])["amount"].sum().reset_index()
    cap = daily.groupby("maker_bank")["amount"].quantile(capacity_percentile).rename("capacity")

    maker_stats = pd.concat([stats_rate, total_vol, cap], axis=1)
    maker_stats["std_rate"].fillna(0, inplace=True)  # Si un seul point => std NaN
    return maker_stats


def optimize_allocation(
    df: pd.DataFrame,
    target_volume: float,
    min_share: float,
    max_share: float,
    risk_aversion: float = 0.0,
    capacity_percentile: float = 0.95,
) -> Tuple[pd.DataFrame, dict]:
    """Optimise l'allocation d'un volume cible entre makers.

    Parameters
    ----------
    df : historique des transactions
    target_volume : volume à répartir (float > 0)
    min_share : part minimale par maker (0-1) (appliquée uniformément)
    max_share : part maximale par maker (0-1) (appliquée uniformément)
    risk_aversion : pondération de l'écart type (>=0)
    capacity_percentile : pour bornes supérieures basées sur historique

    Returns
    -------
    (alloc_df, meta) où alloc_df contient: maker_bank, avg_rate, std_rate, capacity,
        lower_bound, upper_bound, alloc_volume, alloc_pct, unit_cost, cost
    meta: dict avec objective_value, expected_cost, risk_adjusted_cost
    """
    if pulp is None:
        raise OptimizationError("La librairie PuLP n'est pas installée. Ajoutez 'pulp' à requirements.txt et réinstallez.")

    if target_volume <= 0:
        raise OptimizationError("target_volume doit être > 0")
    if not (0 <= min_share <= max_share <= 1):
        raise OptimizationError("Assurez-vous que 0 <= min_share <= max_share <= 1")

    maker_stats = _prepare_maker_stats(df, capacity_percentile)
    makers = maker_stats.index.tolist()
    if len(makers) < 2:
        raise OptimizationError("Au moins deux makers sont requis pour optimiser.")

    # Bornes
    lower = {m: min_share * target_volume for m in makers}
    upper = {m: min(max_share * target_volume, float(maker_stats.loc[m, "capacity"])) for m in makers}

    # Vérifs faisabilité
    if sum(lower.values()) - 1e-9 > target_volume:
        raise OptimizationError("Somme des bornes inférieures > volume cible (min_share trop élevé).")
    if sum(upper.values()) + 1e-9 < target_volume:
        raise OptimizationError("Capacité totale insuffisante pour le volume cible (augmentez max_share ou cible plus basse).")

    # Modèle
    model = pulp.LpProblem("Optimal_Allocation", pulp.LpMinimize)
    x = {m: pulp.LpVariable(f"x_{m}", lowBound=lower[m], upBound=upper[m]) for m in makers}

    # Coût unitaire ajusté risque
    unit_cost = {m: maker_stats.loc[m, "avg_rate"] + risk_aversion * maker_stats.loc[m, "std_rate"] for m in makers}

    # Objectif
    model += pulp.lpSum(unit_cost[m] * x[m] for m in makers)

    # Contrainte volume total
    model += pulp.lpSum(x[m] for m in makers) == target_volume

    # Résolution
    model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[model.status] != "Optimal":
        raise OptimizationError(f"Solution non optimale: {pulp.LpStatus[model.status]}")

    rows = []
    total_cost = 0.0
    total_risk_adj_cost = 0.0
    for m in makers:
        vol = x[m].value() or 0.0
        avg_r = maker_stats.loc[m, "avg_rate"]
        std_r = maker_stats.loc[m, "std_rate"]
        u_cost = unit_cost[m]
        cost = vol * avg_r
        risk_cost = vol * u_cost
        total_cost += cost
        total_risk_adj_cost += risk_cost
        rows.append({
            "maker_bank": m,
            "avg_rate": avg_r,
            "std_rate": std_r,
            "capacity": maker_stats.loc[m, "capacity"],
            "lower_bound": lower[m],
            "upper_bound": upper[m],
            "alloc_volume": vol,
            "alloc_pct": vol / target_volume if target_volume else 0,
            "unit_cost": u_cost,
            "cost": cost,
            "risk_adj_cost": risk_cost,
        })

    alloc_df = pd.DataFrame(rows).sort_values("alloc_volume", ascending=False).reset_index(drop=True)
    meta = {
        "objective_value": pulp.value(model.objective),
        "expected_cost": total_cost,
        "risk_adjusted_cost": total_risk_adj_cost,
        "status": pulp.LpStatus[model.status],
    }
    return alloc_df, meta


def baseline_allocation_cost(df: pd.DataFrame, target_volume: float) -> float:
    """Coût baseline: alloue selon parts historiques (proportion du volume total)."""
    vols = df.groupby("maker_bank")["amount"].sum()
    rates = df.groupby("maker_bank")["rate"].mean()
    total = vols.sum()
    if total <= 0:
        return 0.0
    cost = 0.0
    for m, vol in vols.items():
        share = vol / total
        cost += (share * target_volume) * rates.get(m, 0.0)
    return float(cost)


__all__ = [
    "optimize_allocation",
    "baseline_allocation_cost",
    "OptimizationError",
]
