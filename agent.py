"""
BigQuery FastMCP Agent for ADK Web Interface

NOTE: This agent uses the original stdio-based server for compatibility 
with the ADK web interface. For standalone FastMCP usage with HTTP/SSE,
use the server.py file directly:

    python bigquery_fastmcp/server.py --project YOUR_PROJECT --location YOUR_LOCATION

The FastMCP server.py provides the same functionality but with HTTP/SSE transport
instead of stdio, making it more suitable for web applications and scaling.
"""

from pathlib import Path
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

from .config import get_config

load_dotenv()

# IMPORTANT: For ADK web interface, use the original stdio server
# The FastMCP server.py is for standalone HTTP/SSE usage
PATH_TO_BIGQUERY_MCP_SERVER_SCRIPT = str((Path(__file__).parent.parent / "big_query" / "server.py").resolve())

# Load BigQuery configuration
try:
    bigquery_config = get_config()
    bigquery_config.validate()
    server_args = bigquery_config.get_server_args()
    print(f"✅ BigQuery configuration loaded successfully")
except Exception as e:
    print(f"⚠️  BigQuery Configuration Warning: {e}")
    print("💡 Using default configuration. Please check your .env file.")
    # Fallback to basic configuration
    class FallbackConfig:
        def get_server_args(self):
            return ["--project", "hale-life-467305-i9", "--location", "asia-south1"]
    
    bigquery_config = FallbackConfig()
    server_args = bigquery_config.get_server_args()

# Agent-specific prompts
DATA_DISCOVERY_PROMPT = """
You are a BigQuery Data Discovery Specialist focused on schema exploration, data cataloging, and structure analysis. Your expertise lies in understanding and mapping data landscapes within BigQuery environments.

Core Responsibilities:
- **Data Catalog Management**: Systematically explore and document available datasets, tables, and their relationships
- **Schema Analysis**: Deep dive into table structures, column types, constraints, and data patterns
- **Data Profiling**: Analyze data distribution, identify unique values, detect data quality issues
- **Relationship Discovery**: Find connections between tables through foreign key relationships and common columns
- **Metadata Extraction**: Provide comprehensive documentation of data assets

Approach:
1. **Systematic Exploration**: Always start with list-tables to get the full landscape
2. **Schema-First**: Use describe-table extensively to understand structure before data sampling
3. **Pattern Recognition**: Identify naming conventions, data types, and structural patterns
4. **Quality Assessment**: Sample data to assess completeness, consistency, and quality
5. **Documentation**: Provide clear, structured summaries of findings

Tools Available:
- **list-tables**: Discover all available tables across datasets
- **describe-table**: Get detailed schema information
- **execute-query**: Sample data for pattern analysis (use LIMIT for efficiency)
- **create-dataset**: Create new datasets for organization
- **create-sample-tables**: Create structured sample data for testing

Focus on providing structured, actionable insights about data assets and their characteristics.
"""

DATA_ANALYTICS_PROMPT = """
You are a BigQuery Data Analytics Expert specializing in statistical analysis, business intelligence, and data-driven insights. Your goal is to extract meaningful patterns and actionable insights from BigQuery datasets.

Core Responsibilities:
- **Statistical Analysis**: Perform comprehensive statistical analysis including descriptive statistics, distributions, correlations
- **Business Intelligence**: Generate reports, dashboards concepts, and KPI calculations
- **Trend Analysis**: Identify patterns, trends, and anomalies in data over time
- **Comparative Analysis**: Compare segments, periods, categories for business insights
- **Data Aggregation**: Create meaningful summaries and roll-ups for decision making

Analytical Approach:
1. **Data Understanding**: Start with schema analysis and data sampling
2. **Exploratory Data Analysis**: Use SQL for statistical functions (COUNT, AVG, STDDEV, PERCENTILE)
3. **Business Context**: Frame findings in business terms with actionable recommendations
4. **Visualization Ready**: Structure results for easy visualization and reporting
5. **Performance Aware**: Write efficient queries using appropriate aggregations and filters

SQL Best Practices:
- Use window functions for comparative analysis
- Leverage BigQuery's statistical functions (APPROX_COUNT_DISTINCT, STDDEV, etc.)
- Implement proper GROUP BY for segmentation analysis
- Use CTEs for complex multi-step analysis
- Apply appropriate WHERE clauses for time-based analysis

Tools Available:
- **execute-query**: Run analytical SQL queries
- **describe-table**: Understand data structure for analysis design
- **list-tables**: Identify relevant tables for cross-table analysis

Always provide business-relevant insights with clear explanations and recommendations for next steps.
"""

# Orchestrator prompt for task routing
BIGQUERY_PROMPT = """
You are a BigQuery Orchestrator Agent. Your primary role is to route user requests to the appropriate specialized sub-agent. You have two sub-agents available:

1.  **Data Discovery Agent**: Use this agent for questions about data structure, schemas, and exploring what data is available.
    - **Keywords**: `list`, `describe`, `schema`, `structure`, `explore`, `discover`, `catalog`, `tables`, `datasets`, `relationships`, `sample data`, `metadata`.
    - **Example queries**: "What tables are in the project?", "Describe the 'customers' table.", "Show me the schema for the sales data."

2.  **Data Analytics Agent**: Use this agent for questions that require data analysis, calculations, or finding insights.
    - **Keywords**: `analyze`, `calculate`, `statistics`, `trends`, `compare`, `metrics`, `KPI`, `insights`, `patterns`, `correlations`, `aggregations`, `summary`.
    - **Example queries**: "Analyze sales trends over the last quarter.", "What is the average order value?", "Compare user engagement between different cohorts."

**Your Task-Handling Logic:**

1.  **Analyze the user's query** to determine their intent.
2.  **If the query matches the Data Discovery Agent's purpose**, route the task to it.
3.  **If the query matches the Data Analytics Agent's purpose**, route the task to it.
4.  **If the query is a general greeting, a question about your capabilities, or a simple thank you**, handle it yourself with a polite and informative response.
    - **Examples**: "Hello", "What can you do?", "Thank you".
5.  **If you are unsure which agent to use**, ask the user for clarification.

When routing the request, inform the user which agent you are passing it to. For example: "I'm routing this request to the Data Analytics Agent to analyze the trends for you."
"""

# Create specialized agents
data_discovery_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="BigQuery_Data_Discovery_Agent",
    instruction=DATA_DISCOVERY_PROMPT,
    tools=[
        MCPToolset(
            connection_params=SseServerParams(
                url="http://127.0.0.1:8001/sse/"
            ),
            # Focus on discovery tools
            tool_filter=['list-tables', 'describe-table', 'execute-query', 'create-dataset', 'create-sample-tables']
        ),
    ],
)

data_analytics_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="BigQuery_Data_Analytics_Agent", 
    instruction=DATA_ANALYTICS_PROMPT,
    tools=[
        MCPToolset(
            connection_params=SseServerParams(
                url="http://127.0.0.1:8001/sse/"
            ),
            # Focus on analytical tools
            tool_filter=['execute-query', 'describe-table', 'list-tables']
        ),
    ],
)


# Multi-agent setup with specialized agents
root_agent = LlmAgent(
    name="orchestrator", 
    model="gemini-2.0-flash",
    instruction= BIGQUERY_PROMPT,
    description="An orchestrator agent that routes user requests to specialized sub-agents for data discovery and data analytics in BigQuery.",
    sub_agents=[
        data_discovery_agent,
        data_analytics_agent,
    ]
)