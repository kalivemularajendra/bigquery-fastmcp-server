from google.cloud import bigquery
from google.oauth2 import service_account
import logging
from typing import Any, Optional
import os
import random
import uuid
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "mcp_bigquery_fastmcp_server.log")

# Set up logging to both stdout and file
logger = logging.getLogger('mcp_bigquery_fastmcp_server')
handler_stdout = logging.StreamHandler()
handler_file = logging.FileHandler(LOG_FILE_PATH, mode="w")

# Set format for both handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler_stdout.setFormatter(formatter)
handler_file.setFormatter(formatter)

# Add both handlers to logger
logger.addHandler(handler_stdout)
logger.addHandler(handler_file)

# Set overall logging level
logger.setLevel(logging.DEBUG)

logger.info("Starting FastMCP BigQuery Server")

class BigQueryDatabase:
    def __init__(self, project: str, location: str, key_file: Optional[str]):
        """Initialize a BigQuery database client"""
        logger.info(f"Initializing BigQuery client for project: {project}, location: {location}, key_file: {key_file}")
        if not project:
            raise ValueError("Project is required")
        if not location:
            raise ValueError("Location is required")
        
        credentials: service_account.Credentials | None = None
        if key_file:
            try:
                credentials_path = key_file
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            except Exception as e:
                logger.error(f"Error loading service account credentials: {e}")
                raise ValueError(f"Invalid key file: {e}")

        self.client = bigquery.Client(credentials=credentials, project=project, location=location)

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries"""
        logger.debug(f"Executing query: {query}")
        try:
            if params:
                job = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
            else:
                job = self.client.query(query)
                
            results = job.result()
            rows = [dict(row.items()) for row in results]
            logger.debug(f"Query returned {len(rows)} rows")
            return rows
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            raise
    
    def list_tables(self) -> list[str]:
        """List all tables in the BigQuery database"""
        logger.debug("Listing all tables")

        datasets = list(self.client.list_datasets())
        logger.debug(f"Found {len(datasets)} datasets")

        tables = []
        for dataset in datasets:
            dataset_tables = self.client.list_tables(dataset.dataset_id)
            tables.extend([
                f"{dataset.dataset_id}.{table.table_id}" for table in dataset_tables
            ])

        logger.debug(f"Found {len(tables)} tables")
        return tables

    def describe_table(self, table_name: str) -> list[dict[str, Any]]:
        """Describe a table in the BigQuery database"""
        logger.debug(f"Describing table: {table_name}")

        parts = table_name.split(".")
        if len(parts) != 2 and len(parts) != 3:
            raise ValueError(f"Invalid table name: {table_name}")

        dataset_id = ".".join(parts[:-1])
        table_id = parts[-1]

        query = f"""
            SELECT ddl
            FROM {dataset_id}.INFORMATION_SCHEMA.TABLES
            WHERE table_name = @table_name;
        """
        return self.execute_query(query, params=[
            bigquery.ScalarQueryParameter("table_name", "STRING", table_id),
        ])

    def create_dataset(self, dataset_name: str, location: Optional[str] = None) -> str:
        """Create a new dataset in BigQuery"""
        logger.debug(f"Creating dataset: {dataset_name}")
        
        dataset_ref = self.client.dataset(dataset_name)
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location or "US"
        
        try:
            self.client.create_dataset(dataset)
            logger.info(f"Dataset {dataset_name} created successfully")
            return f"Dataset {dataset_name} created successfully"
        except Exception as e:
            if "Already Exists" in str(e):
                logger.info(f"Dataset {dataset_name} already exists")
                return f"Dataset {dataset_name} already exists"
            else:
                logger.error(f"Error creating dataset: {e}")
                raise

    def create_sample_tables(self, dataset_name: str) -> str:
        """Create sample departments and employees tables"""
        logger.debug(f"Creating sample tables in dataset: {dataset_name}")
        
        # Create departments table
        departments_schema = [
            bigquery.SchemaField("dept_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("dept_name", "STRING", mode="REQUIRED")
        ]
        
        dept_table_ref = self.client.dataset(dataset_name).table("departments")
        dept_table = bigquery.Table(dept_table_ref, schema=departments_schema)
        
        # Create employees table
        employees_schema = [
            bigquery.SchemaField("emp_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("emp_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("dept_id", "STRING", mode="REQUIRED")
        ]
        
        emp_table_ref = self.client.dataset(dataset_name).table("employees")
        emp_table = bigquery.Table(emp_table_ref, schema=employees_schema)
        
        try:
            # Create both tables
            self.client.create_table(dept_table)
            self.client.create_table(emp_table)
            logger.info("Sample tables created successfully")
            return "Sample tables (departments and employees) created successfully"
        except Exception as e:
            if "Already Exists" in str(e):
                return "Sample tables already exist"
            else:
                logger.error(f"Error creating tables: {e}")
                raise

    def insert_sample_data(self, dataset_name: str) -> str:
        """Insert sample data into departments and employees tables"""
        logger.debug(f"Inserting sample data into dataset: {dataset_name}")
        
        # Insert departments
        departments = [
            {"dept_id": f"dept_{i}", "dept_name": f"Department_{i}"}
            for i in range(1, 11)
        ]
        
        errors = self.client.insert_rows_json(
            f"{self.client.project}.{dataset_name}.departments", departments
        )
        if errors:
            logger.error(f"Error inserting departments: {errors}")
            return f"Error inserting departments: {errors}"
        
        # Insert employees
        employees = []
        for i in range(1, 51):
            dept_id = random.choice(departments)["dept_id"]
            emp = {
                "emp_id": f"emp_{uuid.uuid4().hex[:8]}",
                "emp_name": f"Employee_{i}",
                "dept_id": dept_id
            }
            employees.append(emp)
        
        errors = self.client.insert_rows_json(
            f"{self.client.project}.{dataset_name}.employees", employees
        )
        if errors:
            logger.error(f"Error inserting employees: {errors}")
            return f"Error inserting employees: {errors}"
        
        logger.info("Sample data inserted successfully")
        return "Sample data inserted successfully (10 departments, 50 employees)"

    def create_complete_sample(self, dataset_name: str, location: Optional[str] = None) -> str:
        """Create dataset, tables, and insert sample data in one go"""
        logger.info(f"Creating complete sample setup for dataset: {dataset_name}")
        
        result = []
        
        # Step 1: Create dataset
        try:
            dataset_result = self.create_dataset(dataset_name, location)
            result.append(dataset_result)
        except Exception as e:
            return f"Error creating dataset: {e}"
        
        # Step 2: Create tables
        try:
            tables_result = self.create_sample_tables(dataset_name)
            result.append(tables_result)
        except Exception as e:
            return f"Error creating tables: {e}"
        
        # Step 3: Insert data
        try:
            data_result = self.insert_sample_data(dataset_name)
            result.append(data_result)
        except Exception as e:
            return f"Error inserting data: {e}"
        
        return "\n".join(result)

# Initialize the database connection (will be set in main)
db: Optional[BigQueryDatabase] = None

# Initialize FastMCP server
mcp = FastMCP("BigQuery_FastMCP_Server")

@mcp.tool()
def execute_query(query: str) -> str:
    """Execute a SELECT query on the BigQuery database"""
    if not db:
        return "Error: Database not initialized"
    
    try:
        results = db.execute_query(query)
        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def list_tables() -> str:
    """List all tables in the BigQuery database"""
    if not db:
        return "Error: Database not initialized"
    
    try:
        results = db.list_tables()
        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def describe_table(table_name: str) -> str:
    """Get the schema information for a specific table"""
    if not db:
        return "Error: Database not initialized"
    
    try:
        results = db.describe_table(table_name)
        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def create_dataset(dataset_name: str, location: str = "US") -> str:
    """Create a new BigQuery dataset"""
    if not db:
        return "Error: Database not initialized"
    
    try:
        result = db.create_dataset(dataset_name, location)
        return result
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def create_sample_tables(dataset_name: str) -> str:
    """Create sample departments and employees tables in a dataset"""
    if not db:
        return "Error: Database not initialized"
    
    try:
        result = db.create_sample_tables(dataset_name)
        return result
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def insert_sample_data(dataset_name: str) -> str:
    """Insert sample data into departments and employees tables"""
    if not db:
        return "Error: Database not initialized"
    
    try:
        result = db.insert_sample_data(dataset_name)
        return result
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def create_complete_sample(dataset_name: str, location: str = "asia-south1") -> str:
    """Create dataset, sample tables, and insert data in one step"""
    if not db:
        return "Error: Database not initialized"
    
    try:
        result = db.create_complete_sample(dataset_name, location)
        return result
    except Exception as e:
        return f"Error: {str(e)}"

def main(project: str, location: str, key_file: Optional[str], host: str = "127.0.0.1", port: int = 8000):
    """Main function to start the FastMCP server with SSE"""
    global db
    
    logger.info(f"Starting FastMCP BigQuery Server with project: {project} and location: {location}")
    logger.info(f"Server will run on {host}:{port}")
    
    # Initialize database connection
    db = BigQueryDatabase(project, location, key_file)
    
    # Run FastMCP server with SSE transport
    mcp.run(transport="sse", host=host, port=port)

if __name__ == "__main__":
    import argparse
    
    # Get environment variables with defaults
    project = os.getenv('BIGQUERY_PROJECT')
    location = os.getenv('BIGQUERY_LOCATION', 'US')
    key_file = os.getenv('BIGQUERY_KEY_FILE')
    host = os.getenv('HOST', 'localhost')
    port = int(os.getenv('PORT', '8000'))
    
    parser = argparse.ArgumentParser(description='BigQuery FastMCP Server with SSE')
    parser.add_argument('--project', default=project, help='BigQuery project ID')
    parser.add_argument('--location', default=location, help='BigQuery location')
    parser.add_argument('--key-file', default=key_file, help='Path to service account key file')
    parser.add_argument('--host', default=host, help='Host to run the server on')
    parser.add_argument('--port', type=int, default=port, help='Port to run the server on')
    
    args = parser.parse_args()
    
    # Check if project is provided either via env var or command line
    if not args.project:
        logger.error("Project is required. Set BIGQUERY_PROJECT environment variable or use --project argument")
        exit(1)
    
    main(args.project, args.location, args.key_file, args.host, args.port)
