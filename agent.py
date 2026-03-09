# ─────────────────────────────────────────────────────
# Sales Account Briefing Agent
# Gemini Live API + Salesforce REST API
# ─────────────────────────────────────────────────────
from simple_salesforce import Salesforce
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()  # loads credentials from your .env file

# ── CONNECT TO SALESFORCE ─────────────────────────────
sf = Salesforce(
    username=os.environ["SF_USERNAME"],
    password=os.environ["SF_PASSWORD"],
    security_token=os.environ["SF_TOKEN"],
    domain="test"  # "test" = sandbox, never change to "login"
)

# ── SALESFORCE DATA FUNCTION ──────────────────────────
def get_account_briefing(account_name: str) -> str:
    """Fetches full account briefing from Salesforce."""
    try:
        # Search for account by name
        accounts = sf.query(
            f"SELECT Id, Name, Industry, NumberOfEmployees, "
            f"Owner.Name, BillingCity, BillingState "
            f"FROM Account WHERE Name LIKE '%{account_name}%' LIMIT 1"
        )
        if accounts['totalSize'] == 0:
            return f"No account found matching '{account_name}'."

        acct = accounts['records'][0]
        acct_id = acct['Id']
        acct_name = acct['Name']
# Get opportunities
        opps = sf.query(
            f"SELECT Name, StageName, Amount, CloseDate "
            f"FROM Opportunity WHERE AccountId = '{acct_id}' "
            f"ORDER BY CloseDate ASC LIMIT 5"
        )

        # Get recent cases
        cases = sf.query(
            f"SELECT Subject, Status, Priority FROM Case "
            f"WHERE AccountId = '{acct_id}' ORDER BY CreatedDate DESC LIMIT 3"
        )

        # Get contacts
        contacts = sf.query(
            f"SELECT Name, Title FROM Contact "
            f"WHERE AccountId = '{acct_id}' LIMIT 4"
        )

        # Build plain-English briefing
        b = f"Briefing for {acct_name}.\n\n"
        b += "OVERVIEW: "
        if acct.get('Industry'): b += f"{acct['Industry']} company. "
        if acct.get('NumberOfEmployees'): b += f"{acct['NumberOfEmployees']} employees. "
        if acct.get('Owner'): b += f"Owner: {acct['Owner']['Name']}. "
        b += "\n\n"

        opp_list = opps.get('records', [])
        if opp_list:
            open_opps = [o for o in opp_list
                         if o['StageName'] not in ['Closed Won','Closed Lost']]
            total = sum(o.get('Amount',0) or 0 for o in open_opps)
            b += f"OPPORTUNITIES: {len(open_opps)} open worth ${total:,.0f}. "
            if open_opps:
                b += f"Next close: {open_opps[0]['CloseDate']}.\n\n"
        else:
            b += "OPPORTUNITIES: None on record.\n\n"

        case_list = cases.get('records', [])
        open_cases = [c for c in case_list if c['Status'] != 'Closed']
        b += f"SUPPORT: {len(open_cases)} open case(s). "
        if open_cases:
            b += f"{open_cases[0]['Subject']} — {open_cases[0]['Priority']} priority.\n\n"

        contact_list = contacts.get('records', [])
        if contact_list:
            names = [f"{c['Name']} ({c.get('Title','')})" for c in contact_list]
            b += "CONTACTS: " + ', '.join(names) + '.'
        return b

    except Exception as e:
        return f"Error: {str(e)}"

# ── GEMINI AGENT CONFIG ───────────────────────────────
SYSTEM_PROMPT = """
You are an expert sales assistant. When asked for an account briefing,
use the get_account_briefing tool to get live Salesforce data, then
deliver a concise, natural spoken briefing. Lead with what matters most.
"""

tools = [types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="get_account_briefing",
        description="Gets account briefing from Salesforce.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"account_name": types.Schema(
                type=types.Type.STRING,
                description="The Salesforce account name to look up"
            )},
            required=["account_name"]
        )
    )
])]

# ── QUICK TEST ────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Salesforce connection...")
    # Replace with a real account name in your sandbox
    print(get_account_briefing('United Oil & Gas Corp.'))