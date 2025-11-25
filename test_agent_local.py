#!/usr/bin/env python3
"""
Local testing script for the multi-agent system with summarization.
This script uses Databricks authentication to test the agent before deployment.
"""

import os
import sys

# Check for Databricks authentication
DATABRICKS_HOST = os.environ.get('DATABRICKS_HOST')
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
    print("=" * 80)
    print("⚠️  DATABRICKS AUTHENTICATION REQUIRED")
    print("=" * 80)
    print("\nTo test the agent locally, you need to set Databricks credentials:")
    print("\n1. Set your Databricks workspace URL:")
    print("   export DATABRICKS_HOST='https://adb-984752964297111.11.azuredatabricks.net'")
    print("\n2. Set your Databricks token:")
    print("   export DATABRICKS_TOKEN='dapi...'")
    print("\nThen run this script again:")
    print("   python test_agent_local.py")
    print("\n" + "=" * 80)
    sys.exit(1)

print("=" * 80)
print("🧪 TESTING MULTI-AGENT SYSTEM LOCALLY")
print("=" * 80)
print(f"\n✓ Databricks Host: {DATABRICKS_HOST}")
print(f"✓ Token: {'*' * 20} (hidden)")

# Import required libraries
print("\n📦 Importing required libraries...")
try:
    from databricks_langchain import ChatDatabricks, DatabricksFunctionClient, set_uc_function_client
    from databricks_langchain.genie import GenieAgent
    from langchain.agents import create_agent
    from langgraph_supervisor import create_supervisor
    import mlflow
    print("✓ All libraries imported successfully")
except ImportError as e:
    print(f"\n❌ Missing required library: {e}")
    print("\nInstall dependencies:")
    print("   pip install langgraph-supervisor==0.0.30 mlflow[databricks] databricks-langchain")
    sys.exit(1)

# Configuration
print("\n⚙️  Configuration:")
LLM_ENDPOINT = "databricks-meta-llama-3-1-8b-instruct"
GENIE_SPACE_ID = "01f0c9f705201d14b364f5daf28bb639"

print(f"   • LLM Endpoint: {LLM_ENDPOINT}")
print(f"   • Genie Space: {GENIE_SPACE_ID}")

# Initialize clients
print("\n🔧 Initializing clients...")
try:
    client = DatabricksFunctionClient()
    set_uc_function_client(client)
    llm = ChatDatabricks(endpoint=LLM_ENDPOINT)
    print("✓ Databricks clients initialized")
except Exception as e:
    print(f"❌ Failed to initialize clients: {e}")
    sys.exit(1)

# Create Genie agent
print("\n🧠 Creating Genie agent...")
try:
    genie_agent = GenieAgent(
        genie_space_id=GENIE_SPACE_ID,
        genie_agent_name="talent_genie",
        description="Analyzes talent stability, mobility patterns, attrition risk, and workforce trends."
    )
    genie_agent.name = "talent_genie"
    print("✓ Genie agent created")
except Exception as e:
    print(f"❌ Failed to create Genie agent: {e}")
    sys.exit(1)

# Create supervisor prompt
print("\n📝 Creating supervisor with enhanced summarization prompt...")
agent_descriptions = "- talent_genie: Analyzes talent data and provides structured results\n"

prompt = f"""
You are a supervisor in a multi-agent system specialized in workforce analytics.

Your workflow:
1. **Understand the user's request**
2. **Delegate to appropriate agent if needed**
3. **Analyze & Summarize** - When an agent returns data:
   
   **CRITICAL: You MUST provide BOTH:**
   
   a) **Natural Language Summary** (2-4 sentences):
      - State the key finding directly
      - Highlight significant insights with specific numbers
      - Note patterns, outliers, or anomalies
      - Make it actionable
   
   b) **Preserve the structured data** - Keep tables intact

Available agents:
{agent_descriptions}

Remember: Provide actionable insights with specific data points.
"""

try:
    supervisor = create_supervisor(
        agents=[genie_agent],
        model=llm,
        prompt=prompt,
        add_handoff_messages=False,
        output_mode="full_history",
    ).compile()
    print("✓ Supervisor created with enhanced prompt")
except Exception as e:
    print(f"❌ Failed to create supervisor: {e}")
    sys.exit(1)

# Test the agent
print("\n" + "=" * 80)
print("🚀 TESTING AGENT")
print("=" * 80)

test_questions = [
    "What is the total attrition count?",
    # Add more test questions as needed
]

for i, question in enumerate(test_questions, 1):
    print(f"\n📊 Test {i}: {question}")
    print("-" * 80)
    
    try:
        messages = [{"role": "user", "content": question}]
        
        # Stream the response
        print("\n🔄 Agent response:\n")
        for _, events in supervisor.stream({"messages": messages}, stream_mode=["updates"]):
            for node_name, state in events.items():
                if "messages" in state and state["messages"]:
                    for msg in state["messages"]:
                        if hasattr(msg, 'content'):
                            content = msg.content
                            if isinstance(content, str) and content.strip():
                                # Highlight agent transitions
                                if node_name != "supervisor":
                                    print(f"\n{'='*60}")
                                    print(f"➜ Agent: {node_name}")
                                    print(f"{'='*60}")
                                
                                print(content)
                                print()
        
        print("\n✅ Test completed successfully")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("✅ LOCAL TESTING COMPLETE")
print("=" * 80)
print("\n📋 What to do next:")
print("   1. If tests passed, proceed to log and deploy in the notebook")
print("   2. If tests failed, check:")
print("      - Genie Space ID is correct")
print("      - Token has access to Genie Space and LLM endpoint")
print("      - Network connectivity to Databricks")

