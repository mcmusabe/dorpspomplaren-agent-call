#!/usr/bin/env python3
"""
Test script om states te valideren voordat ze naar Retell worden gestuurd
"""

import os
import re
from dotenv import load_dotenv
from tools import get_states_with_tools, get_tools_config

load_dotenv()

# Get webhook URL from env or config (without requiring RETELL_API_KEY)
# Read directly from config.py file to avoid import error
CONFIG_WEBHOOK_URL = None
try:
    with open("config.py", "r") as f:
        content = f.read()
        # Extract WEBHOOK_URL value using regex
        match = re.search(r'WEBHOOK_URL\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            CONFIG_WEBHOOK_URL = match.group(1)
except Exception as e:
    print(f"⚠️  Could not read config.py: {e}")

WEBHOOK_URL = os.getenv("RETELL_WEBHOOK_URL") or CONFIG_WEBHOOK_URL

print("=" * 60)
print("STATES VALIDATION TEST")
print("=" * 60)
print()

# Get states
print(f"📡 Webhook URL: {WEBHOOK_URL or 'None'}")
print()

states = get_states_with_tools(WEBHOOK_URL)
tools = get_tools_config(WEBHOOK_URL)

print(f"📊 TOOLS:")
print(f"   Total tools: {len(tools)}")
for tool in tools:
    print(f"   - {tool['name']} ({tool['type']})")
print()

print(f"📊 STATES:")
print(f"   Total states: {len(states)}")
print(f"   Starting state: S0_GREETING")
print()

for i, state in enumerate(states):
    print(f"   State {i+1}: {state['name']}")
    print(f"      Prompt length: {len(state.get('state_prompt', ''))} chars")
    
    edges = state.get('edges', [])
    print(f"      Edges: {len(edges)}")
    for edge in edges:
        print(f"         → {edge['destination_state_name']}: {edge['description']}")
    
    state_tools = state.get('tools', [])
    print(f"      Tools: {len(state_tools)}")
    if state_tools:
        for tool in state_tools:
            tool_type = tool.get('type', 'unknown')
            tool_name = tool.get('name', 'unknown')
            has_params = 'parameters' in tool
            print(f"         - {tool_name} ({tool_type}){' [has params]' if has_params else ' [NO params]'}")
    else:
        print(f"         (no tools)")
    print()

# Validate starting state exists
starting_state = "S0_GREETING"
state_names = [s['name'] for s in states]
if starting_state not in state_names:
    print(f"❌ ERROR: Starting state '{starting_state}' not found!")
    print(f"   Available states: {', '.join(state_names)}")
else:
    print(f"✅ Starting state '{starting_state}' found")

# Validate all edges point to existing states
print()
print("🔍 Validating edges...")
all_valid = True
for state in states:
    for edge in state.get('edges', []):
        dest = edge['destination_state_name']
        if dest not in state_names:
            print(f"❌ ERROR: State '{state['name']}' has edge to non-existent state '{dest}'")
            all_valid = False

if all_valid:
    print("✅ All edges point to valid states")

print()
print("=" * 60)
print("VALIDATION COMPLETE")
print("=" * 60)
