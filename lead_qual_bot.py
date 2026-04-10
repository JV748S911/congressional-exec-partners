#!/usr/bin/env python3
"""
CALE Lead Qualification Bot — Congressional Executive Partners
Auto-qualifies leads for DMV luxury residential & commercial brokerage.
Scores on budget, timeline, submarket, buyer segment. Routes to correct broker.
Score > 8.0 triggers immediate alert.

Criteria (from SOUL.md):
- Budget ≥ $1.2M
- Timeline < 12 months
- Key submarkets: McLean, Tysons, Potomac, Ashburn, Alexandria
- Segments: Gov/Fed (VA luxury → Jane), C-suite (Potomac estates), Tech CEOs (Tysons Class A), AI/Data (Ashburn/Loudoun), Multifam investors (Alexandria)

Outputs: score (0-10), qualification level, broker recommendation, structured summary, GitHub issue ready.
"""

import os
import re
import json
import sys
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

# Broker routing
BROKERS = {
    "jane": {"name": "Jane", "specialty": "VA luxury residential", "priority_segments": ["gov_fed", "resi_nongov", "high_end_resi"]},
    "mike": {"name": "Mike", "specialty": "Commercial / Tech / Data centers", "priority_segments": ["com", "tech_ceo", "data_ai"]},
    "sarah": {"name": "Sarah", "specialty": "Multifamily / Investors / Gov", "priority_segments": ["multifam", "investor", "gov"]},
}

KEY_SUBMARKETS = {"mclean", "tysons", "potomac", "ashburn", "alexandria", "loudoun", "dmv"}
HIGH_VALUE_SEGMENTS = {"gov_fed", "tech_ceo", "c_suite", "data_ai", "multifam_investor"}

class LeadQualBot:
    def __init__(self):
        self.repo = "JV748S911/congressional-exec-partners"
        self.gh_token = self._resolve_gh_token()

    def _resolve_gh_token(self) -> Optional[str]:
        """Resolve GH_TOKEN same way gh-issues skill does (env → config files)."""
        token = os.getenv("GH_TOKEN")
        if token:
            return token

        # Check OpenClaw config paths
        paths = [
            os.getenv("OPENCLAW_CONFIG_PATH"),
            os.path.expanduser("~/.openclaw/openclaw.json"),
            "/data/.openclaw/openclaw.json",
            "/data/.clawdbot/openclaw.json"
        ]
        for path in paths:
            if not path or not os.path.exists(path):
                continue
            try:
                with open(path) as f:
                    config = json.load(f)
                    token = config.get("skills", {}).get("entries", {}).get("gh-issues", {}).get("apiKey") or \
                            config.get("github", {}).get("token")
                    if token and token != "YOUR_TOKEN_HERE":
                        return token
            except Exception:
                continue
        return None

    def parse_budget(self, budget_str: str) -> float:
        """Extract budget in millions from string like '$1.5M', '2.2 million', etc."""
        if not budget_str:
            return 0.0
        # Remove $ , and normalize
        cleaned = re.sub(r'[$,\s]', '', str(budget_str).lower())
        # Find numbers, handle M/k
        match = re.search(r'(\d+\.?\d*)', cleaned)
        if not match:
            return 0.0
        val = float(match.group(1))
        if 'm' in cleaned or 'million' in cleaned:
            return val
        elif 'k' in cleaned or 'thousand' in cleaned:
            return val / 1000
        return val if val > 100 else val * 1000  # assume large number is in thousands if <100

    def parse_timeline_months(self, timeline_str: str) -> int:
        """Estimate months from phrases like 'next 6 months', 'Q3 2026', 'within 1 year'."""
        if not timeline_str:
            return 999
        text = str(timeline_str).lower()
        if any(x in text for x in ["asap", "immediate", "now", "this month"]):
            return 1
        if "quarter" in text:
            return 6
        match = re.search(r'(\d+)\s*(?:month|mo|week)', text)
        if match:
            num = int(match.group(1))
            return num if 'week' not in text else num//4
        if any(x in text for x in ["year", "12 months", "annual"]):
            return 12
        return 18  # default conservative

    def detect_segment(self, notes: str, property_type: str = "") -> str:
        """Detect buyer segment from notes and type."""
        text = (notes + " " + property_type).lower()
        if any(k in text for k in ["gov", "federal", "congress", "agency", "ld rep"]):
            return "gov_fed"
        if any(k in text for k in ["tech", "ceo", "c-suite", "capital one", "exec"]):
            return "tech_ceo"
        if any(k in text for k in ["data", "ai", "ashburn", "loudoun", "center"]):
            return "data_ai"
        if any(k in text for k in ["multifam", "apartment", "investor", "50-unit", "portfolio"]):
            return "multifam_investor"
        if any(k in text for k in ["residential", "home", "estate", "potomac", "mclean"]):
            return "resi_nongov"
        return "general"

    def calculate_score(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Core scoring engine. Returns detailed breakdown."""
        budget = self.parse_budget(lead_data.get("budget", ""))
        timeline_months = self.parse_timeline_months(lead_data.get("timeline", ""))
        submarket = str(lead_data.get("location", "") or lead_data.get("submarket", "")).lower()
        segment = self.detect_segment(lead_data.get("notes", ""), lead_data.get("property_type", ""))
        notes = lead_data.get("notes", "")

        # Component scores (0-10)
        budget_score = 10 if budget >= 2.0 else (8 if budget >= 1.2 else (4 if budget >= 0.8 else 1))
        timeline_score = 10 if timeline_months <= 6 else (8 if timeline_months <= 12 else (3 if timeline_months <= 24 else 0))
        
        location_score = 10 if any(m in submarket for m in KEY_SUBMARKETS) else (6 if "va" in submarket or "md" in submarket or "dc" in submarket else 2)
        
        segment_bonus = 3 if segment in HIGH_VALUE_SEGMENTS else 0
        segment_score = 9 if segment in HIGH_VALUE_SEGMENTS else 5

        # Overall weighted score
        overall = round((budget_score * 0.4) + (timeline_score * 0.3) + (location_score * 0.2) + (segment_score * 0.1) + segment_bonus, 1)
        overall = min(10.0, overall)

        qualification = "High" if overall >= 8.0 else ("Medium" if overall >= 5.0 else "Low")
        
        # Broker recommendation
        if segment in ["gov_fed", "resi_nongov"]:
            broker = "jane"
        elif segment in ["tech_ceo", "data_ai", "com"]:
            broker = "mike"
        else:
            broker = "sarah"

        broker_info = BROKERS[broker]

        score_breakdown = {
            "budget": budget_score,
            "timeline": timeline_score,
            "location": location_score,
            "segment": segment_score,
            "overall": overall,
            "qualification": qualification,
            "recommended_broker": broker_info["name"],
            "broker_specialty": broker_info["specialty"],
            "suggested_score_for_crm": overall,
            "alert_immediate": overall >= 8.0
        }

        return {
            "lead": lead_data,
            "score": score_breakdown,
            "summary": self.generate_summary(lead_data, score_breakdown),
            "github_issue_title": f"Lead: {lead_data.get('name', 'Unknown')} — {qualification} Qual ({overall}/10)",
            "action": "Create GitHub issue + HubSpot sync" if overall >= 5.0 else "Nurture / discard"
        }

    def generate_summary(self, lead: Dict, score: Dict) -> str:
        s = score
        return f"""**CALE Lead Qualification Report**
**Lead**: {lead.get('name', 'N/A')} ({lead.get('email', 'no-email@provided.com')})
**Score**: {s['overall']}/10 — **{s['qualification']} Priority**

**Breakdown**:
- Budget: ${lead.get('budget', 'N/A')} → {s['budget']}/10
- Timeline: {lead.get('timeline', 'unspecified')} → {s['timeline']}/10
- Location: {lead.get('location', lead.get('submarket', 'N/A'))} → {s['location']}/10
- Segment: {self.detect_segment(lead.get('notes',''), lead.get('property_type',''))} → {s['segment']}/10

**Recommendation**: Route to **{s['recommended_broker']}** ({s['broker_specialty']}).
**Action**: {'🚨 Immediate broker alert + create ticket' if s['alert_immediate'] else 'Standard pipeline entry'}
**Next**: Sync to HubSpot + create CALE ticket in repo.

*Generated by LeadQualBot @ {datetime.now().strftime('%Y-%m-%d %H:%M')}*"""

    def create_github_issue(self, qual_result: Dict) -> Optional[str]:
        """Create scored CALE ticket in GitHub repo using curl (no extra deps)."""
        if not self.gh_token:
            print("⚠️ GH_TOKEN not set — skipping GitHub issue creation.")
            return None

        score = qual_result["score"]
        labels = ["lead", score["qualification"].lower(), f"score-{score['overall']}"]
        if score.get("alert_immediate", False):
            labels.append("urgent")
        broker = score.get("recommended_broker", "").lower()
        if "jane" in broker:
            labels.append("jane")
        elif "mike" in broker:
            labels.append("mike")
        else:
            labels.append("sarah")

        issue_data = json.dumps({
            "title": qual_result["github_issue_title"],
            "body": qual_result["summary"] + "\n\n**Raw Lead Data**:\n```json\n" + json.dumps(qual_result["lead"], indent=2) + "\n```\n\nCreated by LeadQualBot (wired to CALE CRM).",
            "labels": labels
        })

        try:
            import subprocess
            cmd = [
                "curl", "-s", "-X", "POST",
                "-H", f"Authorization: token {self.gh_token}",
                "-H", "Accept: application/vnd.github.v3+json",
                "-H", "Content-Type: application/json",
                "-d", issue_data,
                f"https://api.github.com/repos/{self.repo}/issues"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            issue_url = data.get("html_url")
            issue_number = data.get("number")
            print(f"✅ CALE ticket #{issue_number} created → {issue_url}")
            print(f"   Labels: {', '.join(labels)}")
            return issue_url
        except subprocess.CalledProcessError as e:
            print(f"❌ GitHub API error: {e.stderr or e.stdout}")
            return None
        except Exception as e:
            print(f"Exception creating issue: {e}")
            return None

    def qualify(self, lead_data: Dict[str, Any], auto_create_issue: bool = False) -> Dict[str, Any]:
        """Main entrypoint."""
        result = self.calculate_score(lead_data)
        print(result["summary"])
        
        if auto_create_issue and result["score"]["overall"] >= 5.0:
            result["github_issue_url"] = self.create_github_issue(result)
        
        # Hook for HubSpot (call hubspot.py functions if desired)
        if result["score"]["overall"] >= 6.0:
            print("📌 Would sync to HubSpot (contact + deal pipeline) — implement via hubspot.py next.")
        
        return result


def main():
    bot = LeadQualBot()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--example":
        example_lead = {
            "name": "Matt DeVille",
            "email": "matt.deville@gov.example.com",
            "budget": "$2.1M",
            "timeline": "next 4 months",
            "location": "McLean, VA",
            "property_type": "luxury residential",
            "notes": "Gov executive relocating from Capitol Hill. Strong VA luxury preference. Pre-approved.",
            "source": "Inbound form"
        }
        print("=== EXAMPLE LEAD QUALIFICATION (Matt DeVille - known high scorer) ===\n")
        bot.qualify(example_lead, auto_create_issue=True)
        return

    # Interactive or JSON input
    print("CALE Lead Qual Bot")
    print("Paste lead data as JSON or use --example")
    try:
        input_data = json.loads(sys.stdin.read())
        bot.qualify(input_data, auto_create_issue=True)
    except:
        print("Usage: echo '{\"name\": \"...\", \"budget\": \"2.5M\", ...}' | ./lead_qual_bot.py")
        print("Or run with --example")


if __name__ == "__main__":
    main()
