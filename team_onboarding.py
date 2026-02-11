"""
Team Onboarding: First Real Contractor
KPIs, training checklist, and feedback collection
"""

# Team Onboarding Checklist
ONBOARDING_CHECKLIST = """
# StormOps Team Onboarding Checklist

## Pre-Onboarding (1 week before)
- [ ] Select contractor/sales team (1-5 people)
- [ ] Configure 1-2 Strategic Plays for their market
- [ ] Set up team accounts and permissions
- [ ] Prepare sample storm data for training

## Day 1: System Overview (2 hours)
- [ ] StormOps philosophy: Physics → Personas → Plays
- [ ] Control plane walkthrough (http://localhost:8501)
- [ ] Attribution dashboard explanation
- [ ] Copilot basics and queries

## Day 2: Hands-On Training (4 hours)
- [ ] Load a storm event (DFW Storm 24 or similar)
- [ ] Review A-tier leads and SII scores
- [ ] Understand persona assignments
- [ ] Execute a Strategic Play
- [ ] Track attribution and conversions

## Day 3: Live Storm Practice (Full day)
- [ ] Monitor real storm event
- [ ] Use next-best-action recommendations
- [ ] Log touches and outcomes
- [ ] Review end-of-day attribution

## Week 1: Supervised Usage
- [ ] Daily check-ins on system usage
- [ ] Answer questions and troubleshoot
- [ ] Collect feedback on UX and trust
- [ ] Adjust plays based on team input

## Week 2: Independent Usage
- [ ] Team operates autonomously
- [ ] Weekly review of KPIs
- [ ] Identify pain points and feature requests
- [ ] Document success stories

## Success Criteria
- [ ] Team uses system for 80%+ of storm leads
- [ ] Conversion rate meets or exceeds baseline
- [ ] Team reports increased confidence in targeting
- [ ] Feedback incorporated into product roadmap
"""

# KPIs for First Team
TEAM_KPIS = {
    "operational": {
        "response_time": {
            "metric": "Hours from storm detection to first door knock",
            "target": "<6 hours",
            "baseline": "24-48 hours (manual)",
            "measurement": "Timestamp of storm load → First logged touch"
        },
        "doors_per_hour": {
            "metric": "Doors knocked per canvassing hour",
            "target": "10-15 doors/hour",
            "baseline": "6-8 doors/hour (manual routing)",
            "measurement": "Total touches / Total canvassing hours"
        },
        "system_adoption": {
            "metric": "% of leads sourced from StormOps",
            "target": ">80%",
            "baseline": "0% (all manual)",
            "measurement": "StormOps leads / Total leads worked"
        }
    },
    "conversion": {
        "lead_to_inspection": {
            "metric": "% of leads that result in inspection",
            "target": "40-60%",
            "baseline": "20-30% (manual)",
            "measurement": "Inspections / Total leads"
        },
        "inspection_to_contract": {
            "metric": "% of inspections that convert to signed contract",
            "target": "50-70%",
            "baseline": "30-40% (manual)",
            "measurement": "Contracts / Inspections"
        },
        "overall_conversion": {
            "metric": "% of leads that convert to contract",
            "target": "30-50%",
            "baseline": "10-15% (manual)",
            "measurement": "Contracts / Total leads"
        }
    },
    "economics": {
        "cac": {
            "metric": "Customer Acquisition Cost",
            "target": "<$1500",
            "baseline": "$2500-3500 (manual)",
            "measurement": "(Labor + Marketing) / Conversions"
        },
        "revenue_per_hour": {
            "metric": "Revenue generated per canvassing hour",
            "target": "$750-1000/hour",
            "baseline": "$300-500/hour (manual)",
            "measurement": "(Contracts × Avg Deal Size) / Canvassing Hours"
        },
        "roi": {
            "metric": "Return on Investment",
            "target": ">300%",
            "baseline": "150-200% (manual)",
            "measurement": "(Revenue - Costs) / Costs"
        }
    },
    "quality": {
        "attribution_accuracy": {
            "metric": "Team confidence in channel attribution",
            "target": "8+/10",
            "baseline": "N/A (no attribution)",
            "measurement": "Weekly survey: 1-10 scale"
        },
        "play_effectiveness": {
            "metric": "Conversion rate by play",
            "target": "Financing_Aggressive: 40%+, Impact_Report: 35%+",
            "baseline": "N/A (no plays)",
            "measurement": "Conversions / Touches per play"
        },
        "sii_predictive_power": {
            "metric": "Correlation between SII and conversion",
            "target": "r > 0.6",
            "baseline": "N/A",
            "measurement": "Pearson correlation(SII_v2, converted)"
        }
    }
}

# Feedback Collection Template
FEEDBACK_TEMPLATE = """
# StormOps Team Feedback - Week {week}

## Team: {team_name}
## Date: {date}
## Completed by: {name}

### 1. System Usage
- How many storm events did you work this week? ___
- What % of your leads came from StormOps? ___%
- Did you use the next-best-action recommendations? Yes / No
- If no, why not? _______________

### 2. Trust & Confidence (1-10 scale)
- I trust the SII scores to identify good leads: ___/10
- I trust the persona assignments: ___/10
- I trust the play recommendations: ___/10
- I trust the attribution data: ___/10

### 3. UX & Usability
- Easiest feature to use: _______________
- Hardest feature to use: _______________
- Most valuable feature: _______________
- Least valuable feature: _______________

### 4. Performance
- Conversion rate this week: ___%
- How does this compare to your baseline? Better / Same / Worse
- Revenue per canvassing hour: $___/hour
- CAC this week: $___

### 5. Pain Points
- What frustrated you most about the system? _______________
- What would you change first? _______________
- What's missing that you need? _______________

### 6. Success Stories
- Best lead from StormOps this week: _______________
- Why was it a good lead? _______________
- Would you have found this lead manually? Yes / No

### 7. Feature Requests
1. _______________
2. _______________
3. _______________

### 8. Overall
- Would you recommend StormOps to another team? Yes / No
- Overall satisfaction (1-10): ___/10
- Will you continue using it next week? Yes / No
"""

def generate_onboarding_package(team_name, plays):
    """Generate complete onboarding package for team."""
    
    import os
    from datetime import datetime
    
    # Create team directory
    team_dir = f'onboarding_{team_name.lower().replace(" ", "_")}'
    os.makedirs(team_dir, exist_ok=True)
    
    # Write checklist
    with open(f'{team_dir}/checklist.md', 'w') as f:
        f.write(ONBOARDING_CHECKLIST)
    
    # Write KPIs
    import json
    with open(f'{team_dir}/kpis.json', 'w') as f:
        json.dump(TEAM_KPIS, f, indent=2)
    
    # Write feedback template
    with open(f'{team_dir}/feedback_template.md', 'w') as f:
        f.write(FEEDBACK_TEMPLATE)
    
    # Write team-specific play config
    play_config = {
        'team': team_name,
        'plays': plays,
        'created': datetime.now().isoformat()
    }
    
    with open(f'{team_dir}/play_config.json', 'w') as f:
        json.dump(play_config, f, indent=2)
    
    print(f"✅ Onboarding package created: {team_dir}/")
    print(f"   • checklist.md - Onboarding steps")
    print(f"   • kpis.json - KPI definitions")
    print(f"   • feedback_template.md - Weekly feedback form")
    print(f"   • play_config.json - Team play configuration")
    
    return team_dir


if __name__ == '__main__':
    print("=" * 60)
    print("TEAM ONBOARDING SETUP")
    print("=" * 60)
    
    # Example: Onboard first team
    team_name = "DFW Elite Roofing"
    plays = [
        {
            "id": "financing_aggressive",
            "name": "Financing Aggressive",
            "channels": ["door_knock", "sms", "call"],
            "message": "0% financing + free inspection + price match guarantee",
            "target_personas": ["Deal_Hunter"],
            "sla_hours": 12
        },
        {
            "id": "impact_report_premium",
            "name": "Impact Report Premium",
            "channels": ["door_knock", "email", "call"],
            "message": "Physics-grade damage assessment with adjuster documentation",
            "target_personas": ["Proof_Seeker"],
            "sla_hours": 24
        }
    ]
    
    package_dir = generate_onboarding_package(team_name, plays)
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print(f"1. Review {package_dir}/checklist.md")
    print(f"2. Schedule Day 1 training (2 hours)")
    print(f"3. Prepare sample storm data")
    print(f"4. Set up team accounts in control plane")
    print(f"5. Begin Week 1 supervised usage")
    print("=" * 60)
