#!/usr/bin/env python3
"""
HubSpot Sync for Congressional Executive Partners (CEP)
Syncs CALE leads from GitHub issues → HubSpot Contacts + Deals.
"""

import os
import sys
import json
import requests
from datetime import datetime

# Configuration
HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN") or "YOUR_TOKEN_HERE"  # Set via environment variable (never commit real token)
HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

BASE_URL = "https://api.hubapi.com"

def create_or_update_contact(email, first_name, last_name, lead_score, notes):
    """Create or update contact in HubSpot"""
    if not HUBSPOT_ACCESS_TOKEN:
        print("Error: HUBSPOT_ACCESS_TOKEN not set")
        return None
    
    data = {
        "properties": {
            "email": email,
            "firstname": first_name,
            "lastname": last_name,
            "lead_score": str(lead_score),
            "notes": notes,
            "lead_source": "CALE AI Engine"
        }
    }
    
    # Search for existing contact
    search_url = f"{BASE_URL}/crm/v3/objects/contacts/search"
    search_data = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "email",
                "operator": "EQ",
                "value": email
            }]
        }]
    }
    
    try:
        resp = requests.post(search_url, headers=HEADERS, json=search_data)
        results = resp.json().get("results", [])
        
        if results:
            contact_id = results[0]["id"]
            update_url = f"{BASE_URL}/crm/v3/objects/contacts/{contact_id}"
            requests.patch(update_url, headers=HEADERS, json=data)
            print(f"Updated contact: {email}")
            return contact_id
        else:
            create_url = f"{BASE_URL}/crm/v3/objects/contacts"
            resp = requests.post(create_url, headers=HEADERS, json=data)
            contact_id = resp.json().get("id")
            print(f"Created contact: {email}")
            return contact_id
    except Exception as e:
        print(f"HubSpot error: {e}")
        return None

def create_deal(contact_id, deal_name, amount, stage="appointmentscheduled"):
    """Create deal linked to contact"""
    data = {
        "properties": {
            "dealname": deal_name,
            "amount": str(amount),
            "pipeline": "default",
            "dealstage": stage,
            "closedate": (datetime.now().replace(year=datetime.now().year + 1)).isoformat()
        },
        "associations": [{
            "to": {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]
        }]
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/crm/v3/objects/deals", headers=HEADERS, json=data)
        print(f"Created deal: {deal_name}")
        return resp.json().get("id")
    except Exception as e:
        print(f"Deal creation error: {e}")
        return None

if __name__ == "__main__":
    print("CEP HubSpot Sync Tool")
    print("Usage: Set HUBSPOT_ACCESS_TOKEN then run with lead data")
    # Example usage would go here
    print("Ready for CALE → HubSpot sync")