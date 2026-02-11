"""
StormOps Copilot - AI Assistant
Wired to database and provides real insights
"""

import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime


def get_db_data():
    """Fetch real data from database"""
    conn = sqlite3.connect("stormops_cache.db")
    cursor = conn.cursor()

    data = {}

    # Get storm info
    cursor.execute("SELECT name, status FROM storms LIMIT 1")
    storm = cursor.fetchone()
    data["storm"] = {"name": storm[0], "status": storm[1]} if storm else None

    # Get impact zones
    cursor.execute(
        "SELECT COUNT(*), AVG(hail_size_inches), MAX(damage_propensity_score) FROM earth2_impact_zones"
    )
    zones = cursor.fetchone()
    data["impact_zones"] = {
        "count": zones[0],
        "avg_hail": zones[1],
        "max_damage": zones[2],
    }

    # Get leads summary
    cursor.execute(
        "SELECT COUNT(*), AVG(lead_score), COUNT(CASE WHEN priority_tier = 'A' THEN 1 END) FROM leads"
    )
    leads = cursor.fetchone()
    data["leads"] = {"total": leads[0], "avg_score": leads[1], "tier_a": leads[2]}

    # Get routes
    cursor.execute(
        "SELECT COUNT(*), COUNT(CASE WHEN status = 'in_progress' THEN 1 END) FROM routes"
    )
    routes = cursor.fetchone()
    data["routes"] = {"total": routes[0], "active": routes[1]}

    # Get jobs
    cursor.execute(
        "SELECT COUNT(*), SUM(claim_amount) FROM jobs WHERE status = 'completed'"
    )
    jobs = cursor.fetchone()
    data["jobs"] = {"completed": jobs[0], "claims": jobs[1] or 0}

    # Get top leads
    cursor.execute("""
        SELECT lead_score, conversion_probability, address, city, zip_code, 
               hail_size, roof_age, property_value, priority_tier, trigger_description
        FROM leads 
        WHERE lead_score > 90
        ORDER BY lead_score DESC
        LIMIT 10
    """)
    data["top_leads"] = [
        {
            "score": r[0],
            "conv": r[1],
            "address": r[2],
            "city": r[3],
            "zip": r[4],
            "hail": r[5],
            "roof_age": r[6],
            "value": r[7],
            "tier": r[8],
            "trigger": r[9],
        }
        for r in cursor.fetchall()
    ]

    # Get ZIP coverage
    cursor.execute("SELECT DISTINCT zip_code FROM leads ORDER BY zip_code LIMIT 20")
    data["zip_coverage"] = [r[0] for r in cursor.fetchall()]

    conn.close()
    return data


def get_ai_response(prompt, data):
    """Generate AI response based on prompt and real data"""

    prompt_lower = prompt.lower()

    # Context about current data
    context = f"""
    Current StormOps Data:
    - Storm: {data["storm"]["name"] if data["storm"] else "N/A"}
    - Impact Zones: {data["impact_zones"]["count"]}, Avg Hail: {data["impact_zones"]["avg_hail"]:.1f}\", Max Damage: {data["impact_zones"]["max_damage"]:.1%}
    - Total Leads: {data["leads"]["total"]}, A-Tier: {data["leads"]["tier_a"]}, Avg Score: {data["leads"]["avg_score"]:.0f}
    - Routes: {data["routes"]["total"]}, Active: {data["routes"]["active"]}
    - Completed Jobs: {data["jobs"]["completed"]}, Claims: ${data["jobs"]["claims"]:,.0f}
    - ZIP Coverage: {len(data["zip_coverage"])} ZIPs
    """

    # Handle different query types
    if any(w in prompt_lower for w in ["top", "best", "highest score", "a-tier"]):
        response = f"**Top Scoring Leads:**\n\n"
        for i, lead in enumerate(data["top_leads"][:5], 1):
            response += (
                f"{i}. **{lead['address']}**, {lead['city']} (ZIP: {lead['zip']})\n"
            )
            response += f"   Score: {lead['score']:.0f}/100 | Conv: {lead['conv']:.1%} | Tier: {lead['tier']}\n"
            response += f'   Hail: {lead["hail"]}" | Roof: {lead["roof_age"]}yrs | Value: ${lead["value"]:,.0f}\n'
            response += f"   Trigger: {lead['trigger'][:80] if lead['trigger'] else 'N/A'}...\n\n"
        response += f"\n**Recommendation:** Prioritize A-tier leads in ZIPs {', '.join(str(z) for z in data['zip_coverage'][:5])}"

    elif "route" in prompt_lower or "crew" in prompt_lower:
        response = f"""**Route Optimization Analysis:**

Current Status:
- {data["routes"]["total"]} routes total, {data["routes"]["active"]} active
- {data["jobs"]["completed"]} jobs completed, ${data["jobs"]["claims"]:,.0f} in claims

**Recommended Actions:**
1. Assign crews to pending routes in high-damage ZIPs
2. Focus on A-tier leads with scores >95 for immediate outreach
3. Optimize route sequence by property value and hail intensity

**Route Priority Order:**
1. ZIPs with damage >20% and A-tier count >100
2. ZIPs with 15-20% damage and B-tier count >50  
3. Secondary routes for follow-up
"""

    elif "tam" in prompt_lower or "revenue" in prompt_lower or "market" in prompt_lower:
        a_tier_count = data["leads"]["tier_a"]
        avg_value = (
            sum(l["value"] for l in data["top_leads"]) / len(data["top_leads"])
            if data["top_leads"]
            else 0
        )
        response = f"""**Total Addressable Market (TAM) Analysis:**

- Total Leads: {data["leads"]["total"]}
- A-Tier Leads: {data["leads"]["tier_a"]}
- Avg Lead Score: {data["leads"]["avg_score"]:.0f}/100
- Est. Conversion Rate: {data["leads"]["avg_score"] / 1000:.1%}

**Revenue Potential:**
- A-Tier Potential: ${avg_value * a_tier_count * 0.08:,.0f} (assuming 8% conversion at avg value)
- High-Priority ZIPs: {", ".join(str(z) for z in data["zip_coverage"][:8])}

**Recommended Focus:**
- Prioritize A-tier leads in ZIPs with highest hail damage
- Target properties with roof age >20 years
- Focus on high property values for maximum revenue
"""

    elif "hail" in prompt_lower or "damage" in prompt_lower or "impact" in prompt_lower:
        response = f"""**Impact Analysis:**

Hail Events:
- Impact Zones: {data["impact_zones"]["count"]}
- Average Hail Size: {data["impact_zones"]["avg_hail"]:.1f} inches
- Maximum Damage Score: {data["impact_zones"]["max_damage"]:.1%}

**Damage Assessment:**
Properties in high-damage zones (>15%) should be prioritized for:
1. Immediate roof inspections
2. Rapid claim filing
3. Crew dispatch scheduling

**Affected ZIPs:**
{", ".join(str(z) for z in data["zip_coverage"])}
"""

    elif (
        "action" in prompt_lower
        or "recommend" in prompt_lower
        or "what should" in prompt_lower
    ):
        response = f"""**Recommended Actions Based on Current Data:**

1. **Immediate (Today)**
   - Review {data["leads"]["tier_a"]} A-tier leads with scores >90
   - Assign crews to routes in high-damage ZIPs
   - Complete pending jobs with high claim potential

2. **Short-Term (This Week)**
   - Generate routes for remaining {data["leads"]["total"] - data["leads"]["tier_a"]} leads
   - Process claims from {data["jobs"]["completed"]} completed jobs
   - Follow up on warm leads in ZIPs {data["zip_coverage"][0]}, {data["zip_coverage"][1]}

3. **Strategic**
   - Focus on high-value properties (${data["top_leads"][0]["value"]:,.0f}+) for maximum ROI
   - Expand route coverage to {len(data["zip_coverage"])} ZIPs
"""

    else:
        response = f"""**StormOps AI Assistant**

I can help you analyze:

**Data Insights:**
- Impact zones: {data["impact_zones"]["count"]} zones, max damage {data["impact_zones"]["max_damage"]:.1%}
- Leads: {data["leads"]["total"]} total, {data["leads"]["tier_a"]} A-tier ({data["leads"]["avg_score"]:.0f} avg score)
- Routes: {data["routes"]["total"]} total, {data["routes"]["active"]} active
- Jobs: {data["jobs"]["completed"]} completed, ${data["jobs"]["claims"]:,.0f} in claims

**Ask me about:**
- "Show top leads" - Highest scoring opportunities
- "Route optimization" - Crew and route recommendations  
- "TAM analysis" - Revenue potential by ZIP
- "Hail impact" - Damage assessment
- "Recommended actions" - Priority tasks

{context}
"""

    return response


def render_copilot():
    """Render the AI copilot chat interface"""

    st.markdown("### StormOps AI Assistant")

    # Initialize chat history
    if "copilot_messages" not in st.session_state:
        st.session_state.copilot_messages = [
            {
                "role": "assistant",
                "content": "**StormOps AI Ready**\n\nI have access to your real-time data:\n- "
                + str(get_db_data()["leads"]["total"])
                + " scored leads\n- "
                + str(get_db_data()["impact_zones"]["count"])
                + " impact zones\n- "
                + str(get_db_data()["routes"]["total"])
                + " active routes\n\nAsk me about leads, routes, TAM analysis, or recommended actions!",
            }
        ]

    # Display chat messages
    for message in st.session_state.copilot_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about leads, routes, TAM, or actions..."):
        # Add user message
        st.session_state.copilot_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response with real data
        with st.chat_message("assistant"):
            try:
                # Fetch real data from database
                data = get_db_data()

                # Generate contextual response
                response = get_ai_response(prompt, data)

                st.markdown(response)
                st.session_state.copilot_messages.append(
                    {"role": "assistant", "content": response}
                )

            except Exception as e:
                error_msg = f"Error accessing data: {str(e)}"
                st.markdown(error_msg)
                st.session_state.copilot_messages.append(
                    {"role": "assistant", "content": error_msg}
                )


if __name__ == "__main__":
    render_copilot()
