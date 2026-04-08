import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from agents.discovery import discovery_agent
from agents.personalize import personalize_agent
from agents.outreach import outreach_agent
from agents.nurture import nurture_agent
from agents.score import score_agent
from utils.state import LeadState

load_dotenv()

graph = StateGraph(LeadState)

# Nodes
graph.add_node('discovery', discovery_agent)
graph.add_node('personalize', personalize_agent)
graph.add_node('outreach', outreach_agent)
graph.add_node('nurture', nurture_agent)
graph.add_node('score', score_agent)

# Edges
graph.set_entry_point('discovery')
graph.add_edge('discovery', 'personalize')
graph.add_edge('personalize', 'outreach')
graph.add_conditional_edges('outreach', lambda s: 'hot' if s.score > 0.8 else 'nurture', {'hot': 'score', 'nurture': 'nurture'})
graph.add_edge('nurture', 'score')
graph.add_edge('score', END)

app = graph.compile()

if __name__ == '__main__':
    # Cron-like: run daily
    result = app.invoke({'triggers': 'daily_scan'})
    print(result)
