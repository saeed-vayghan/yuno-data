"""Pure helper tests: formatters, charts, card text, URL filters, table view."""

from datetime import date

from casarecon.dashboard import cards, charts, filters, tables, theme
from casarecon.dashboard import format as fmt
from casarecon.dashboard.data import Filters
from tests.dashboard import fakes


def test_formatters():
    assert fmt.local(12345, "CLP", 0) == "CLP 12,345"  # CLP: 0 dp from the seed exponent
    assert fmt.local(123456, "MXN", 2) == "MXN 1,234.56"
    assert fmt.local(-58000, "CLP", 0) == "CLP −58,000"
    assert fmt.usd(1234.564) == "$1,234.56" and fmt.usd_compact(127_400) == "$127.4k"
    assert fmt.usd_signed(-62.1) == "−$62.10 under" and fmt.usd_signed(4) == "+$4.00 over"
    assert fmt.delta_pts(1.1) == "▲ +1.1 pts" and fmt.delta_pts(-0.4) == "▼ −0.4 pts"
    assert fmt.delta_usd(1200) == "▲ +$1,200" and fmt.delta_int(-8) == "▼ −8"
    assert fmt.rate(0.142) == "14.2%" and fmt.rate_range(0.213, 0.198, 0.229) == "21.3% [19.8–22.9]"
    assert fmt.week_label("2026-W25", date(2026, 6, 15), date(2026, 6, 21)) == "W25 (Jun 15–21)"
    assert fmt.day_range(date(2026, 5, 29), date(2026, 6, 4)) == "May 29–Jun 4"


def test_charts_cards_filters_tables():
    # charts: open weeks dashed + labelled, PSP colours only, direct end labels, data-built captions
    fig = charts.line_weekly(fakes.weekly_trend(by="psp"))
    assert len([t for t in fig.data if t.line.dash == "dash"]) == 2
    assert {t.line.color for t in fig.data} <= set(theme.PSP_COLORS.values())
    assert {a.text for a in fig.layout.annotations} >= {"PSP_A", "PSP_B", charts.OPEN_NOTE}
    assert charts.bar_weekly(fakes.weekly_trend()).layout.title.text == "Weekly net loss (USD)"
    assert charts.rate_takeaway(fakes.weekly_trend()) == "Highest closed week: W22 at 13.0%."
    # worst-week card text, low sample labelled (never hidden)
    ranked = fakes.worst_week()
    assert cards.worst_headline(ranked.iloc[0]) == (
        "PSP_B · W24 (Jun 8–14) · Net loss $4,210.00 · Gross under $4,900.00")
    assert "PSP_E W26 $900 (low sample)" in cards.next_line(ranked)
    # URL filters: unknown values dropped + reported; scoping; handoff dates clipped to data range
    values, ignored = filters.parse_params({"psp": ["PSP_B", "PSP_Z"]}, fakes.OPTIONS)
    assert values == {"psp": ["PSP_B"]} and ignored == ["Ignored unknown PSP 'PSP_Z'"]
    f = Filters(psp=("PSP_B",), date_from=date(2026, 6, 15), date_to=date(2026, 6, 21))
    assert filters.scoped(f, {"psp"}).date_from is None
    assert filters.clip((date(2026, 3, 30), date(2026, 4, 5)), (date(2026, 4, 1), None)) == (
        date(2026, 4, 1), date(2026, 4, 5))
    # table view: masked customer even if a raw ID slips through; local amounts stay text, USD numeric
    view = tables.outlier_view(fakes.transactions().assign(customer=["cus_8f2a91c07f3a", "x", None]))
    assert view["customer"][0] == "cus_••••7f3a" and view["raw_diff"][0] == "CLP −58,000"
    assert view["residual_usd"].dtype.kind == "f"
