# StormOps Playbook Configuration
# Generated from enriched property graph targeting engine

## Play Definitions

### Financing_Aggressive
**Target:** Deal_Hunter + Very High Risk  
**Message:** "0% financing + free inspection + price match guarantee"  
**SII Boost:** +30  
**Materials:** value_shingles, standard  
**Follow-up SLA:** 12 hours  
**Current Targets:** 12 properties (avg value: $376k)

### Impact_Report_Premium
**Target:** Proof_Seeker + Very High Risk  
**Message:** "Physics-grade damage assessment with adjuster documentation"  
**SII Boost:** +25  
**Materials:** premium_shingles, impact_resistant  
**Follow-up SLA:** 24 hours  
**Current Targets:** 9 properties (avg value: $337k)

### Premium_Showcase
**Target:** Status_Conscious + Very High Risk  
**Message:** "Designer materials + curb appeal + neighborhood showcase"  
**SII Boost:** +28  
**Materials:** designer, premium_shingles  
**Follow-up SLA:** 24 hours  
**Current Targets:** 5 properties (avg value: $272k)

### Safety_Warranty
**Target:** Family_Protector + Very High Risk  
**Message:** "Extended warranty + safety inspection + family protection focus"  
**SII Boost:** +25  
**Materials:** premium_shingles, impact_resistant  
**Follow-up SLA:** 24 hours  
**Current Targets:** 5 properties (avg value: $233k)

### Financing_Standard
**Target:** Deal_Hunter + High Risk  
**Message:** "Low-rate financing + competitive pricing"  
**SII Boost:** +20  
**Materials:** value_shingles  
**Follow-up SLA:** 24 hours  
**Current Targets:** 15 properties (avg value: $319k)

---

## Territory Campaign Plans

### ZIP 75227 - Financing Blitz
- **Properties:** 3 (Deal_Hunter dominant)
- **Avg Priority Score:** 97
- **Avg Value:** $425k
- **Avg Risk:** 71.7
- **Suggested Play:** Financing_Aggressive
- **Action:** Deploy 12hr SLA team, emphasize 0% financing

### ZIP 75224 - Mixed Premium
- **Properties:** 5 (Family_Protector dominant)
- **Avg Priority Score:** 92
- **Avg Value:** $257k
- **Avg Risk:** 74.0
- **Suggested Play:** Premium_Showcase
- **Action:** Multi-persona approach, safety + aesthetics

### ZIP 75238 - High-Value Financing
- **Properties:** 3 (Deal_Hunter dominant)
- **Avg Priority Score:** 89
- **Avg Value:** $371k
- **Avg Risk:** 73.3
- **Suggested Play:** Financing_Aggressive
- **Action:** Price-sensitive high-value targets, fast follow-up

### ZIP 75231 - Technical Documentation
- **Properties:** 5 (Proof_Seeker dominant)
- **Avg Priority Score:** 88
- **Avg Value:** $336k
- **Avg Risk:** 72.0
- **Suggested Play:** Impact_Report_Premium
- **Action:** Lead with physics/engineering, adjuster-grade reports

---

## Operator Filters (StormOps UI)

### High Priority Queue
```sql
SELECT * FROM high_priority_targets 
WHERE priority_score >= 90
ORDER BY follow_up_sla_hours ASC, priority_score DESC;
```
**Use case:** Daily outreach prioritization

### Urgent Follow-ups (12-24hr SLA)
```sql
SELECT * FROM urgent_follow_ups
WHERE follow_up_sla_hours <= 24;
```
**Use case:** Time-sensitive lead management

### Financing Campaign Filter
```sql
SELECT * FROM financing_campaign_targets
WHERE price_sensitivity > 65 AND risk_score > 70;
```
**Use case:** Promo/financing campaign targeting

### Premium Upsell Filter
```sql
SELECT * FROM premium_upsell_targets
WHERE estimated_value > 350000 AND risk_tolerance > 80;
```
**Use case:** High-margin material upsells

### ZIP Territory Planning
```sql
SELECT * FROM zip_campaign_summary
WHERE property_count >= 3 AND avg_priority_score >= 85;
```
**Use case:** Territory assignment and batch campaigns

---

## Model Integration

### SII Feature Engineering
Use these as input features:
- `sii_with_boost` (base SII + play boost)
- `risk_score` (property-level risk)
- `price_sensitivity` (persona-derived)
- `risk_tolerance` (persona-derived)
- `affordability_index` (tract-level SES)

### MOE Priors by Segment
- **High Risk + Deal_Hunter:** MOE prior = 0.35 (price-sensitive, high urgency)
- **High Risk + Proof_Seeker:** MOE prior = 0.28 (documentation-driven, slower close)
- **High Risk + Family_Protector:** MOE prior = 0.30 (warranty-focused, moderate pace)
- **High Risk + Status_Conscious:** MOE prior = 0.25 (premium materials, longer sales cycle)

### Playbook Config Overrides
```json
{
  "Deal_Hunter": {
    "default_materials": ["value_shingles", "standard"],
    "financing_emphasis": true,
    "follow_up_cadence_hours": [12, 36, 72],
    "price_match_enabled": true
  },
  "Proof_Seeker": {
    "default_materials": ["premium_shingles", "impact_resistant"],
    "documentation_level": "adjuster_grade",
    "follow_up_cadence_hours": [24, 72, 168],
    "technical_content": true
  },
  "Family_Protector": {
    "default_materials": ["standard", "premium_shingles"],
    "warranty_emphasis": true,
    "follow_up_cadence_hours": [36, 72, 120],
    "safety_messaging": true
  },
  "Status_Conscious": {
    "default_materials": ["designer", "premium_shingles"],
    "aesthetic_emphasis": true,
    "follow_up_cadence_hours": [24, 96, 168],
    "curb_appeal_focus": true
  }
}
```

---

## Next Actions

1. **Immediate (Today):**
   - Query `high_priority_targets` WHERE `priority_score >= 100`
   - Assign to reps with 12hr SLA capability
   - Deploy Financing_Aggressive play to 7 Deal_Hunter properties

2. **This Week:**
   - Launch ZIP 75227 financing blitz (3 properties, $425k avg)
   - Launch ZIP 75231 technical documentation campaign (5 properties)
   - A/B test Impact_Report_Premium vs Standard messaging

3. **Model Updates:**
   - Retrain SII with `sii_with_boost` as feature
   - Update MOE priors by persona segment
   - Feed play outcomes back to targeting engine

4. **UI Integration:**
   - Add persona filter to property search
   - Add "Suggested Play" column to lead table
   - Add ZIP campaign summary dashboard widget
