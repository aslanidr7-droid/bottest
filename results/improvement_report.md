# Gap analysis vs the video and improvement attempts (2026-11-08)

Rule: every idea fixed up front and judged on TRAINING (2022–2024). Locked test (2025–26) is only a check
(already seen). The real referee is 2007–2021, data never used for any choice.

## What we had skipped from the video — now done
| Item | Module | Result |
|---|---|---|
| P5b VIX + breadth filter | src/p5b_filters.py | Train ret/DD 0.48→0.55, test 2.25→1.64, 2007–21 0.49→0.47 |
| Calm vs wild sizing (half size when SPY vol high) | src/p5b_filters.py | Train DD −28→−23%, but 2007–21 ret/DD 0.49→0.42 |
| VIX dial (<20 full, 20–30 half, >30 zero) | src/p5b_filters.py | Worse everywhere (2007–21 0.34) |
| Video's own sleeve set (QQQ breakout, XLK dip, GLD dip) | src/p5b_filters.py | Train 0.46 vs ours 0.54; test 2.25 vs 1.99 |
| P4b Claude's 10 sleeve ideas (191 candidates) | src/p4b_ideas.py | 26 survivors; best 3 (USO/XLE gapdown, XLK badweek) |
| Extra checks: 2× cost, Monte Carlo, other period, delay | src/robustness.py | Core robust; sleeves add ≈ nothing at 2× cost |
| P4c screener | — | Not done: needs historical S&P 500 membership (survivorship bias) |

## Out-of-sample 2007–2021 (never seen)
| Setup | Annual | Max DD | Ret/DD |
|---|---|---|---|
| Core QQQ/GLD (live rule) | 14.6% | −29.5% | 0.49 |
| Core + QQQ dip | 14.5% | −31.2% | 0.46 |
| Core + QQQ dip + 3 P4b sleeves | 14.1% | −32.8% | 0.43 |
| QQQ buy & hold | 17.0% | −53.4% | 0.32 |

P4b sleeves alone 2007–21: USO gapdown PF 0.96, XLE gapdown PF 0.95 (losers), XLK badweek PF 1.38, QQQ dip PF 1.18.

## Conclusions
1. The core rule is the only real edge, and it is robust (costs, delay, 2007–21, SMA plateau).
   Honest long-run expectation ≈ 12–15%/yr with ≈ −30% drawdown. The 25%/yr of 2025–26 was a good market.
2. Sleeves (ours, the video's, and the 3 new ones) do not add value out of sample; they add margin and cost.
3. None of the video's filters (VIX/breadth, calm/wild, VIX dial) beat the plain core on unseen data.
4. Nothing was changed in the live config. Options need a human decision (see PROGRESS.md).
