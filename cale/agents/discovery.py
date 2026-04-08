from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import requests  # for APIs

llm = ChatGroq(model='grok-4-1-fast', api_key=os.getenv('XAI_API_KEY'))

prompt = PromptTemplate.from_template("""
Scan public sources for DMV real estate triggers:
- FEC filings: New lobbyists/execs
- Congress.gov: Committee assignments, term ends
- Property records: Recent sales in Kalorama/Georgetown
- News: Exec relocations

Query: {query}
Output JSON: [{'name': str, 'role': str, 'trigger': str, 'propensity': 0-1, 'email': str}]
""")

def discovery_agent(state):
    # Mock API calls
    sources = [
        requests.get('https://api.congress.gov/...'),  # TODO: real endpoints
    ]
    chain = prompt | llm
    leads = chain.invoke({'query': state['triggers']})
    state['leads'] = leads
    return state
