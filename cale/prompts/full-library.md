# Full Prompt Library for CALE Agents

## 1. Discovery Agent
```
Scan public DC/DMV sources for luxury move triggers ($1.5M+ res, premium comm).
Sources: FEC new filers/lobbyists, Congress.gov assignments/term ends, property records (Kalorama, McLean), exec news.
Date range: {date_range}
Output JSON: [{name, role, trigger_event, neighborhood, public_email, raw_data}]
Propensity hint only - score next.
Public data ONLY.
```

## 2. Scoring Agent
```
Score {lead_json}:
Factors (weighted): Trigger recency (30%), role prestige (20%), policy RE impact (20%), past moves (15%), income proxy (15%).
Score 0-1. Thresholds: >0.8 hot, 0.5-0.8 warm.
JSON: {score, category, rationale}
```

## 3. Personalization Agent
```
Personalize for {lead}:
Message type: {email/sms/voice}
Public facts only: {lead.trigger, lead.role}.
Example: 'Congrats on {trigger}! With {policy}, {neighborhood} is hot.'
Compliant footer.
Jinja template output.
```

(4-6 similar: Outreach, Nurture, Handoff)

Full 6 ready—expand as built.
