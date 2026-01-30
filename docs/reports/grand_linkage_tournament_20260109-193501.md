# Grand Linkage Tournament Report
Generated: 2026-01-09 19:35:01.949810

## PyPortfolioOpt HRP Sensitivity (Target)
| Simulator    |   complete |   single |    ward |
|:-------------|-----------:|---------:|--------:|
| cvxportfolio |    1.26029 |  1.26406 | 1.26029 |

## Full HRP Landscape
|                                    |   complete |   single |    ward |
|:-----------------------------------|-----------:|---------:|--------:|
| ('custom', 'cvxportfolio')         |    1.30749 |  1.30749 | 1.30749 |
| ('cvxportfolio', 'cvxportfolio')   |    1.30749 |  1.30749 | 1.30749 |
| ('pyportfolioopt', 'cvxportfolio') |    1.26029 |  1.26406 | 1.26029 |
| ('skfolio', 'cvxportfolio')        |    1.21397 |  1.21397 | 1.21397 |

## Top 20 Performers (All Configurations)
| Linkage   | Simulator    | Engine         | Profile      |   Sharpe |      Vol |   Return | RunID           |
|:----------|:-------------|:---------------|:-------------|---------:|---------:|---------:|:----------------|
| single    | cvxportfolio | market         | market       |  2.16312 | 0.110997 |  0.2401  | 20260109-193211 |
| ward      | cvxportfolio | market         | market       |  2.16312 | 0.110997 |  0.2401  | 20260109-193249 |
| complete  | cvxportfolio | market         | market       |  2.16312 | 0.110997 |  0.2401  | 20260109-193326 |
| single    | cvxportfolio | cvxportfolio   | hrp          |  1.30749 | 0.883693 |  1.15542 | 20260109-193211 |
| single    | cvxportfolio | custom         | hrp          |  1.30749 | 0.883693 |  1.15542 | 20260109-193211 |
| ward      | cvxportfolio | cvxportfolio   | hrp          |  1.30749 | 0.883693 |  1.15542 | 20260109-193249 |
| complete  | cvxportfolio | custom         | hrp          |  1.30749 | 0.883693 |  1.15542 | 20260109-193326 |
| ward      | cvxportfolio | custom         | hrp          |  1.30749 | 0.883693 |  1.15542 | 20260109-193249 |
| complete  | cvxportfolio | cvxportfolio   | hrp          |  1.30749 | 0.883693 |  1.15542 | 20260109-193326 |
| ward      | cvxportfolio | cvxportfolio   | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193249 |
| complete  | cvxportfolio | custom         | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193326 |
| complete  | cvxportfolio | skfolio        | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193326 |
| single    | cvxportfolio | custom         | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193211 |
| ward      | cvxportfolio | skfolio        | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193249 |
| ward      | cvxportfolio | pyportfolioopt | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193249 |
| ward      | cvxportfolio | cvxportfolio   | min_variance |  1.29394 | 0.894461 |  1.15737 | 20260109-193249 |
| single    | cvxportfolio | skfolio        | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193211 |
| single    | cvxportfolio | pyportfolioopt | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193211 |
| single    | cvxportfolio | cvxportfolio   | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193211 |
| ward      | cvxportfolio | custom         | equal_weight |  1.29394 | 0.894461 |  1.15737 | 20260109-193249 |