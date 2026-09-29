# Alerts: 2026-W25

As of 2026-06-30 23:58:00 (data time). Last closed week 2026-W25, compared with 2026-W24.

**Open SEV2:** 2 · **Open SEV3:** 3 · **Insufficient data:** 0

## Alerts

| Severity | Status | Rule | Segment | Owner | Message |
|---|---|---|---|---|---|
| SEV2 | ONGOING | peer | PSP_B\|AR | PSP ops | PSP_B flags 17.4% of AR rows vs 14.9% for other PSPs (+2.4 pts, q = 0.025; 95% CI 15.8%-19.1%). |
| SEV2 | ONGOING | peer | PSP_C\|ALL | PSP ops | PSP_C flags more than other PSPs in 4 countries: AR 17.8% (+2.8 pts), CL 16.5% (+2.8 pts), CO 16.9% (+3.3 pts), MX 16.1% (+2.3 pts). Same PSP everywhere points to a PSP-side cause (fee, rounding, policy). |
| SEV2 | RESOLVED | peer | PSP_E\|CO | PSP ops | Resolved: PSP_E flags 16.4% of CO rows vs 13.6% for other PSPs (+2.7 pts, q = 0.039; 95% CI 14.3%-18.8%). |
| SEV3 | ONGOING | change | PSP_C\|AR | PSP ops | PSP_C\|AR flag rate 20.0% in 2026-W25 is above the control limit 18.9% (baseline 13.8%). |
| SEV3 | ONGOING | large_rows | ALL | PSP ops | 429 large rows ($16,323.14 absolute) in 2026-W25; top: PSP_A\|MX $1,825.25, PSP_D\|MX $1,723.42, PSP_C\|MX $1,372.68. |
| SEV3 | ONGOING | settle_lag | CO\|200+ | PSP ops | 17.5% of CO\|200+ rows settle after 7 days (limit 6.0%). |

## Money

| | 2026-W24 | 2026-W25 |
|---|---|---|
| Gross under | $17,005.41 | $20,115.97 |
| Gross over | $28.46 | $31.08 |
| Net | $16,976.95 | $20,084.89 |

Reference line: $9,800.00 a week (the CFO's quarterly loss / 13).

## Week over week (flag rate)

| PSP | Country | Prev | Last | Change |
|---|---|---|---|---|
| PSP_C | CL | 15.5% | 20.1% | ▲ +4.6 pts (worse) |
| PSP_B | CO | 12.2% | 16.0% | ▲ +3.8 pts (worse) |
| PSP_D | AR | 10.6% | 14.5% | ▲ +3.8 pts (worse) |
| PSP_E | CO | 10.8% | 14.3% | ▲ +3.5 pts (worse) |
| PSP_E | AR | 12.1% | 15.5% | ▲ +3.3 pts (worse) |
| PSP_D | MX | 13.0% | 16.0% | ▲ +3.0 pts (worse) |
| PSP_B | CL | 13.2% | 15.4% | ▲ +2.2 pts (worse) |
| PSP_E | CL | 15.3% | 17.5% | ▲ +2.1 pts (worse) |
| PSP_C | MX | 14.6% | 16.3% | ▲ +1.7 pts (worse) |
| PSP_C | CO | 15.9% | 17.2% | ▲ +1.3 pts (worse) |

## Insufficient data

<details><summary>0 segments not evaluated</summary>

None.

</details>
