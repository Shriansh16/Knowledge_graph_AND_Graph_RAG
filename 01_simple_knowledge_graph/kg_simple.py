from dotenv import load_dotenv
import os
from neo4j import GraphDatabase

load_dotenv()

AURA_INSTANCENAME = os.environ["AURA_INSTANCENAME"]
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
AUTH = (NEO4J_USERNAME, NEO4J_PASSWORD)
 
driver = GraphDatabase.driver(NEO4J_URI, auth=AUTH) #This initializes a driver that will be used to send queries to the Neo4j database.

def connect_and_query():
    """
    This function connects to a Neo4j database, runs a query to count all the nodes,
     prints the count, handles any errors that occur, and then closes the database connection."""
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n)")
            count = result.single().value()
            print(f"Number of nodes: {count}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()

def create_entities(tx):
    """
    This function creates nodes in a Neo4j database for Albert Einstein, the subject Physics,the Nobel Prize
    in Physics, and the countries Germany and USA using the MERGE statement to ensure no duplicates are created."""
    # Create Albert Einstein node
    tx.run("MERGE (a:Person {name: 'Albert Einstein'})")

    # Create other nodes
    tx.run("MERGE (p:Subject {name: 'Physics'})")
    tx.run("MERGE (n:NobelPrize {name: 'Nobel Prize in Physics'})")
    tx.run("MERGE (g:Country {name: 'Germany'})")
    tx.run("MERGE (u:Country {name: 'USA'})")

def create_relationships(tx):
    """
    This function creates relationships in a Neo4j database between Albert Einstein and other entities. It links 
    him to Physics (studied), the Nobel Prize in Physics (won), Germany (born in), and the USA (died in), using 
    MERGE to avoid duplicate relationships."""
    # Create studied relationship
    tx.run(
        """
    MATCH (a:Person {name: 'Albert Einstein'}), (p:Subject {name: 'Physics'})
    MERGE (a)-[:STUDIED]->(p)
    """
    )

    # Create won relationship
    tx.run(
        """
    MATCH (a:Person {name: 'Albert Einstein'}), (n:NobelPrize {name: 'Nobel Prize in Physics'})
    MERGE (a)-[:WON]->(n)
    """
    )

    # Create born in relationship
    tx.run(
        """
    MATCH (a:Person {name: 'Albert Einstein'}), (g:Country {name: 'Germany'})
    MERGE (a)-[:BORN_IN]->(g)
    """
    )

    # Create died in relationship
    tx.run(
        """
    MATCH (a:Person {name: 'Albert Einstein'}), (u:Country {name: 'USA'})
    MERGE (a)-[:DIED_IN]->(u)
    """
    )

# Function to connect and run a simple Cypher query
def query_graph_simple(cypher_query):
    """
    This function connects to a Neo4j database, runs a provided Cypher query, and prints the value of the name 
    field from each result. It handles errors gracefully and ensures the database connection is closed afterward."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=AUTH)
    try:
        with driver.session() as session: #database=NEO4J_DATABASE
            result = session.run(cypher_query)
            for record in result:
                print(record["name"])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()

# Function to connect and run a Cypher query
def query_graph(cypher_query):
    """
    This function connects to a Neo4j database, executes a given Cypher query, and prints the path field from each 
    result. It includes error handling and ensures the database connection is properly closed after execution."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=AUTH)
    try:
        with driver.session() as session: #database=NEO4J_DATABASE
            result = session.run(cypher_query)
            for record in result:
                print(record["path"])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()

def build_knowledge_graph():
    """
    This function builds a knowledge graph in a Neo4j database. It opens a session, calls two functions to create 
    entities (nodes) and their relationships, handles any errors that occur, and ensures the database connection is 
    closed afterward."""
    # Open a session with the Neo4j database

    try:
        with driver.session() as session: #database=NEO4J_DATABASE
            # Create entities
            session.execute_write(create_entities)
            # Create relationships
            session.execute_write(create_relationships)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()

# Cypher query to find paths related to Albert Einstein
einstein_query = """
MATCH path=(a:Person {name: 'Albert Einstein'})-[:STUDIED]->(s:Subject)
RETURN path
UNION
MATCH path=(a:Person {name: 'Albert Einstein'})-[:WON]->(n:NobelPrize)
RETURN path
UNION
MATCH path=(a:Person {name: 'Albert Einstein'})-[:BORN_IN]->(g:Country)
RETURN path
UNION
MATCH path=(a:Person {name: 'Albert Einstein'})-[:DIED_IN]->(u:Country)
RETURN path
"""

# Simple Cypher query to find all node names
simple_query = """
MATCH (n)
RETURN n.name AS name
"""

if __name__ == "__main__":
    # Build the knowledge graph
    build_knowledge_graph()

    query_graph_simple(
        simple_query)
    query_graph(einstein_query)