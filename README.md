BigQuery FastMCP ServerThis project provides a robust server for interacting with Google BigQuery using the FastMCP library. It leverages Server-Sent Events (SSE) for communication, offering a modern, scalable, and web-friendly alternative to traditional stdio-based MCP servers. It also includes a sophisticated multi-agent system built with the Google Agent Development Kit (ADK) for intelligent task routing and execution.🚀 OverviewThe core of this project is a Python server that exposes various BigQuery functionalities as tools that can be called remotely. By using FastMCP with SSE, it's designed for easy integration into web applications, enabling real-time, concurrent connections for data discovery and analytics.Key Improvements over traditional MCP servers:HTTP-Based Transport: Uses standard, firewall-friendly SSE instead of stdin/stdout.Scalable by Design: Built to handle multiple simultaneous client connections.Web-Friendly: Simplifies integration with any web front-end or service.Real-Time Streaming: SSE allows for live data streaming from the server to the client.✨ Key DifferencesThe FastMCP approach significantly simplifies the server's code and architecture.Traditional stdio Implementation# Complex asynchronous setup
async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, ...)

# Manual tool registration and handling
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [types.Tool(name="execute-query", ...)]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "execute-query":
        # Logic to execute the tool
Modern FastMCP Implementation# Simple, declarative server setup
mcp = FastMCP("BigQuery_FastMCP_Server")

# Automatic tool registration with function decorators
@mcp.tool()
def execute_query(query: str) -> str:
    """Execute a SELECT query on the BigQuery database"""
    # Tool implementation is the function body

# Single command to start the server
mcp.run(transport="sse", host="127.0.0.1", port=8001)
🤖 Agent Implementation (ADK)The agent.py script implements a multi-agent system using the Google Agent Development Kit (ADK). This system intelligently routes user queries to the appropriate specialized agent.Orchestrator Agent: The main entry point that analyzes the user's request and delegates it to one of the sub-agents.Data Discovery Agent: Specializes in tasks related to schema exploration, data cataloging, and structure analysis. It uses tools like list-tables and describe-table.Data Analytics Agent: Focuses on statistical analysis, business intelligence, and extracting insights from data. It primarily uses the execute-query tool.# agent.py
# Root agent that delegates tasks
root_agent = LlmAgent(
    name="orchestrator",
    model="gemini-2.0-flash",
    instruction=BIGQUERY_PROMPT,
    sub_agents=[
        data_discovery_agent,
        data_analytics_agent,
    ]
)
🌐 ADK Web InterfaceThis agent setup is designed for compatibility with the ADK Web Interface. The agents connect to the running FastMCP server to utilize its tools, effectively bridging the conversational AI front-end with the powerful BigQuery back-end.🛠️ Available ToolsThe server comes with a comprehensive set of tools for managing and querying BigQuery:execute_query(query: str): Executes a SQL SELECT query.list_tables(): Lists all available tables in the project.describe_table(table_name: str): Retrieves the schema for a specified table.create_dataset(dataset_name: str, location: str): Creates a new dataset.create_sample_tables(dataset_name: str): Creates sample departments and employees tables.insert_sample_data(dataset_name: str): Populates the sample tables with data.create_complete_sample(dataset_name: str, location: str): A utility function that creates a dataset, sample tables, and inserts data in one call.⚙️ UsageConfigurationSet up your BigQuery connection using a .env file in the root directory.Note: The server port is set to 8001 to avoid conflicts with the ADK Web Interface, which typically uses port 8000.# .env
BIGQUERY_PROJECT="your-gcp-project-id"
BIGQUERY_LOCATION="your-bigquery-location" # e.g., "US" or "asia-south1"
BIGQUERY_KEY_FILE="/path/to/your/service-account.json" # Optional
HOST="127.0.0.1"
PORT="8001"
Starting the ServerYou can run the server directly from the command line, overriding .env variables if needed.# Basic startup using .env config
python server.py

# Override config with command-line arguments
python server.py \
  --project "your-gcp-project-id" \
  --location "asia-south1" \
  --key-file "/path/to/service-account.json" \
  --host "127.0.0.1" \
  --port 8001
Server EndpointsOnce running, the server exposes the following endpoints:SSE Endpoint: http://127.0.0.1:8001/sse (for MCP client connections)Health Check: http://127.0.0.1:8001/health (returns server status)Client ConnectionConnect to the server using any MCP client that supports the SSE transport.from mcp import Client

# Connect to the FastMCP server
client = Client("sse://127.0.0.1:8001/sse")

# Example: List all tables
result = client.tools.list_tables()
print(result)
📦 DevelopmentAdding new functionality is straightforward. Simply define a new function in server.py and decorate it with @mcp.tool(). FastMCP handles the rest.@mcp.tool()
def my_new_tool(param1: str, param2: int) -> str:
    """
    This is the description for the new tool.
    It will be automatically exposed by the server.
    """
    # Your tool's logic here
    return f"Received {param1} and {param2}"
