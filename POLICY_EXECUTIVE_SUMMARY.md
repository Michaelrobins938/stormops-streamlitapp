# StormOps Treatment Policy: Executive Summary

## Three-Policy Framework

StormOps uses **uplift modeling** to predict which properties will respond to outreach vs those that won't. We rank all properties by expected incremental lift and apply one of three policies:

| Policy | When to Use | Treat % | Expected Lift | Incremental Revenue |
|--------|-------------|---------|---------------|---------------------|
| **Moderate** (Default) | Standard storms | 72% | +22 pts | $9.9M per storm |
| **Aggressive** | All-out volume days | 79% | +21 pts | $10.5M per storm |
| **Conservative** | Constrained capacity | 54% | +22 pts | $7.4M per storm |

**All three policies deliver ~21-22 point lift** (45% treatment vs 24% control conversion). The difference is volume: aggressive maximizes revenue, conservative maximizes efficiency, moderate balances both.

---

## Why Moderate is Default

1. **Safety margin:** 28% held out for controls, capacity buffers, and low-value properties
2. **Highest ROI:** 6,369% return (slightly better than aggressive)
3. **Proven threshold:** 15% uplift cutoff is industry-standard for first deployment
4. **Scalable:** Works with typical crew capacity (3,000 properties per storm)

**Bottom line:** Moderate policy delivers $9.9M incremental revenue per storm with 95% statistical confidence, while maintaining experimental integrity and operational flexibility.

---

## Validation Plan

After first live storm under moderate policy:
- Compare actual vs predicted lift (+22 pts expected)
- Validate across segments (ZIP × Persona × SII)
- Measure against universal control baseline
- Adjust threshold if needed (10-20% range)

**Success criteria:** Actual lift within 5 pts of predicted, ROI > 300%

---

## Board-Friendly One-Liner

*"StormOps ranks every roof by predicted incremental lift and treats the top 72% (moderate policy), delivering an expected +22 point conversion advantage and $9.9M incremental revenue per storm with 95% confidence."*

---

## Technical Details (For Operations)

### Policy Implementation
```python
# Moderate policy (default)
if property.expected_uplift >= 0.15:
    decision = "TREAT"
else:
    decision = "HOLD"

# Override: Always hold universal control (9%)
# Override: Follow RCT assignments (36%)
```

### Capacity Management
```python
# If crew capacity < treat count:
treat_list = sort_by_uplift(properties)[:capacity_limit]
# Ensures highest-value properties treated first
```

### Real-Time Monitoring
- Track treatment vs control conversion daily
- Alert if lift < 10 pts (below threshold)
- Escalate if control contamination detected

---

## Policy Switching Guide

**Switch to Aggressive when:**
- Contractor requests max volume
- Crew capacity > 3,500 properties
- Storm severity very high (SII > 100 avg)

**Switch to Conservative when:**
- Crew capacity < 2,500 properties
- Testing new market
- Need to prove concept to skeptical partner

**Stay on Moderate when:**
- Standard storm operations
- Crew capacity 2,500-3,500
- Want balanced risk/reward

---

## Expected Outcomes (Per Storm)

### Moderate Policy
```
Properties: 4,200 total
  - Treat: 3,074 (72%)
  - Hold: 1,187 (28%)

Conversions:
  - Treatment: 1,388 (45.2%)
  - Control: 280 (23.6%)
  - Lift: +21.6 pts (+91.4%)

Economics:
  - Revenue: $25.4M (treatment) vs $15.5M (control baseline)
  - Incremental: $9.9M
  - Cost: $154K (3,074 × $50)
  - ROI: 6,369%
```

### Comparison to Manual (No StormOps)
```
Manual targeting: ~25% conversion (no uplift model)
StormOps moderate: 45% conversion on treated properties
Advantage: +20 pts, +80% relative lift
```

---

## Risk Mitigation

**Experimental Integrity:**
- 378 properties (9%) in universal control (never treated)
- 1,500 properties (36%) in RCT experiments (random assignment)
- Ensures unbiased lift measurement

**Capacity Buffers:**
- 28% held out provides flexibility for crew constraints
- Can reduce to 20% (aggressive) if needed
- Can increase to 46% (conservative) if constrained

**Compliance Monitoring:**
- Log all treatment decisions
- Track adherence to assignments
- Alert on control contamination

---

## Rollout Timeline

**Week 1:** Deploy moderate policy on next storm
**Week 2:** Measure actual vs predicted lift
**Week 3:** Validate by segment, adjust if needed
**Month 2:** Scale to multiple storms, test aggressive/conservative
**Quarter 2:** Optimize thresholds based on real data

---

## Success Metrics

**Primary:**
- Actual lift ≥ 15 pts (vs 22 predicted)
- ROI > 300% (vs 6,369% predicted)
- Treatment > Control at 95% confidence

**Secondary:**
- Crew utilization > 80%
- No control contamination
- Team adoption > 80%

**Validation:**
- Universal control baseline stable
- RCT experiments show similar lift
- High-uplift segments show bigger gaps

---

## Questions & Answers

**Q: Why not treat everyone?**
A: Need controls to measure lift. Also, low-uplift properties waste resources.

**Q: What if actual lift is lower than predicted?**
A: Adjust threshold (e.g., 20% instead of 15%) or retrain model.

**Q: Can we change policies mid-storm?**
A: No—breaks experimental integrity. Choose policy pre-storm.

**Q: What if crew capacity changes?**
A: Use capacity limit parameter to cap at crew size, prioritizing by uplift.

**Q: How do we know the model is working?**
A: Compare treatment vs control. If no difference, model isn't working.
