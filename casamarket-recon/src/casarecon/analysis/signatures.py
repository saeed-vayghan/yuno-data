"""Q5 signature table (pure): systematic clusters vs random noise."""

import pandas as pd

SIGNATURE = ["psp", "country", "likely_cause", "direction", "rounding_flag"]
MIN_N = 30
MIN_CONCENTRATION = 1.5


def signature_table(fct: pd.DataFrame, min_n: int = MIN_N,
                    min_concentration: float = MIN_CONCENTRATION) -> pd.DataFrame:
    """Group non-exact settled rows by psp x country x cause x direction x rounding_flag.

    share_of_cause_in_country = n / rows with the same signature minus psp, in that country;
    psp_share_of_country_volume = psp rows / all settled rows in the country;
    concentration = share_of_cause / psp_share; `systematic` if n >= min_n and concentration >= min.
    """
    volume = fct.groupby(["country", "psp"]).size()
    psp_share = (volume / volume.groupby(level="country").transform("sum")).rename("psp_share")
    nx = fct[fct["likely_cause"].notna()].assign(_loss=-fct["residual_usd"])
    if nx.empty:
        return pd.DataFrame(columns=[*SIGNATURE, "n", "share_of_cause_in_country",
                                     "psp_share_of_country_volume", "concentration", "usd", "label"])
    g = nx.groupby(SIGNATURE, dropna=False).agg(n=("_loss", "size"), usd=("_loss", "sum"))
    g = g.reset_index()
    rest = [c for c in SIGNATURE if c != "psp"]
    g["share_of_cause_in_country"] = g["n"] / g.groupby(rest, dropna=False)["n"].transform("sum")
    g = g.merge(psp_share.reset_index(), on=["country", "psp"], how="left")
    g = g.rename(columns={"psp_share": "psp_share_of_country_volume"})
    g["concentration"] = g["share_of_cause_in_country"] / g["psp_share_of_country_volume"]
    systematic = (g["n"] >= min_n) & (g["concentration"] >= min_concentration)
    g["label"] = systematic.map({True: "systematic", False: "random"})
    order = ["label", "usd", "n", "psp", "country", "likely_cause"]
    return g.sort_values(order, ascending=[False, False, False, True, True, True], ignore_index=True)
