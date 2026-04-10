#!/usr/bin/env python3
"""
CALE Email/Form Ingestion → LeadQualBot → GitHub CALE CRM
Uses gog (Google Workspace CLI) to fetch recent lead-like emails,
parses them, qualifies with LeadQualBot, and creates scored tickets.
"""

import os
import json
import subprocess
import re
from datetime import datetime
from lead_qual_bot import LeadQualBot

class LeadIngestor:
    def __init__(self):
        self.bot = LeadQualBot()
        self.account = os.getenv("GOG_ACCOUNT") or "jesse.congressionalexecpartners@gmail.com"

    def run_gog_command(self, cmd: list) -> dict:
        """Run gog CLI and return parsed JSON if possible."""
        try:
            full_cmd = ["gog"] + cmd + ["--account", self.account, "--json", "--no-input"]
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"raw": result.stdout, "error": "not json"}
            else:
                return {"error": result.stderr.strip() or result.stdout.strip()}
        except FileNotFoundError:
            return {"error": "gog CLI not found. Run: brew install steipete/tap/gogcli"}
        except subprocess.TimeoutExpired:
            return {"error": "gog command timed out"}
        except Exception as e:
            return {"error": str(e)}

    def fetch_recent_lead_emails(self, max_emails: int = 5) -> list:
        """Search Gmail for potential lead/inquiry emails."""
        print(f"🔍 Searching Gmail for recent lead-like messages (account: {self.account})...")

        # Search for common lead signals (unread in inbox)
        search_cmd = ["gmail", "messages", "search", 
                     "in:inbox is:unread (lead OR inquiry OR \"contact form\" OR budget OR timeline OR \"interested in\" OR \"real estate\")",
                     "--max", str(max_emails)]

        data = self.run_gog_command(search_cmd)
        
        if "error" in data:
            if "No tokens stored" in str(data["error"]) or "auth" in str(data["error"]).lower():
                print("\n❌ gog not authenticated yet.")
                print("\nOne-time setup required:")
                print("1. Create Google Cloud project + OAuth client (Gmail API)")
                print("2. Download client_secret.json")
                print("3. gog auth credentials ~/client_secret.json")
                print(f"4. gog auth add {self.account} --services gmail")
                print("5. export GOG_ACCOUNT=jesse.congressionalexecpartners@gmail.com")
                return []
            print(f"❌ gog error: {data['error']}")
            return []

        messages = data if isinstance(data, list) else data.get("messages", []) or []
        print(f"Found {len(messages)} potential lead messages.")
        return messages

    def parse_email_for_lead(self, msg: dict) -> dict:
        """Extract structured lead data from email body/subject/from."""
        # In real use, fetch full message with gog gmail message get <id>
        # For prototype, use available fields + simple regex on snippet/body
        subject = msg.get("subject", "")
        from_addr = msg.get("from", "")
        snippet = msg.get("snippet", "") or msg.get("body", "")
        full_text = f"{subject} {from_addr} {snippet}"

        lead = {
            "name": self.extract_name(from_addr, snippet),
            "email": self.extract_email(from_addr),
            "budget": self.extract_budget(full_text),
            "timeline": self.extract_timeline(full_text),
            "location": self.extract_location(full_text),
            "property_type": self.extract_property_type(full_text),
            "notes": snippet or subject,
            "source": f"Email from {from_addr}",
            "message_id": msg.get("id")
        }
        return lead

    def extract_name(self, from_field: str, body: str) -> str:
        # Simple heuristics
        match = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+)', from_field + " " + body)
        return match.group(1) if match else "Unknown Prospect"

    def extract_email(self, from_field: str) -> str:
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
        return match.group(0) if match else "unknown@example.com"

    def extract_budget(self, text: str) -> str:
        match = re.search(r'(\$|budget:?)\s*(\d+[.,]?\d*)\s*(M|million|k|thousand)?', text, re.I)
        if match:
            return match.group(0)
        return "Unknown"

    def extract_timeline(self, text: str) -> str:
        match = re.search(r'(next|within|in)\s+\d+\s*(month|week|quarter|year|days)', text, re.I)
        return match.group(0) if match else "Unspecified"

    def extract_location(self, text: str) -> str:
        for area in ["McLean", "Tysons", "Potomac", "Ashburn", "Alexandria", "Loudoun", "DMV", "VA", "MD", "DC"]:
            if area.lower() in text.lower():
                return area
        return "DMV Area"

    def extract_property_type(self, text: str) -> str:
        text_lower = text.lower()
        if any(k in text_lower for k in ["office", "commercial", "class a"]):
            return "Commercial"
        if any(k in text_lower for k in ["residential", "home", "estate", "house"]):
            return "Luxury Residential"
        if "multifam" in text_lower or "apartment" in text_lower:
            return "Multifamily"
        if "data" in text_lower or "center" in text_lower:
            return "Data Center Adjacent"
        return "Residential/Commercial"

    def process(self, max_emails: int = 5, dry_run: bool = False, manual_lead: dict = None):
        """Main ingestion loop."""
        print(f"\n🚀 CALE Email Ingestion + Auto-Qualify @ {datetime.now()}")

        if manual_lead:
            print("\n🔧 Using manual lead data (Gmail auth not required for testing)")
            result = self.bot.qualify(manual_lead, auto_create_issue=not dry_run)
            if not dry_run and result["score"]["overall"] >= 5.0:
                print("✅ Ticket created in CALE CRM")
            return

        messages = self.fetch_recent_lead_emails(max_emails)
        
        if not messages:
            print("No new lead emails found or gog not configured.")
            print("\nTip: Use --manual with JSON data to test without Gmail auth.")
            return

        for msg in messages:
            lead = self.parse_email_for_lead(msg)
            print(f"\n--- Processing: {lead['name']} ({lead['email']}) ---")
            
            result = self.bot.qualify(lead, auto_create_issue=not dry_run)
            
            if not dry_run and result["score"]["overall"] >= 5.0:
                print("✅ Ticket created in CALE CRM + broker routing applied.")
            elif dry_run:
                print("🧪 Dry-run mode — no ticket created.")

        print("\nIngestion complete. High-scoring leads are now in your CALE GitHub repo.")


if __name__ == "__main__":
    ingestor = LeadIngestor()
    import sys
    dry = "--dry-run" in sys.argv
    test_mode = "--test" in sys.argv
    manual = None
    if "--manual" in sys.argv:
        try:
            json_str = sys.argv[sys.argv.index("--manual") + 1]
            manual = json.loads(json_str)
        except:
            print("Error: --manual requires valid JSON")
            sys.exit(1)
    if test_mode:
        manual = {
            "name": "Sarah Chen",
            "email": "sarah.chen@techcorp.com",
            "budget": "5.2M",
            "timeline": "next 3 months",
            "location": "McLean VA",
            "property_type": "luxury residential",
            "notes": "Tech executive relocating. Strong preference for VA properties near Tysons. Pre-approved."
        }
    ingestor.process(max_emails=5, dry_run=dry, manual_lead=manual)
