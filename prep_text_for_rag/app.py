from dotenv import load_dotenv
import os
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI

load_dotenv()

AURA_INSTANCENAME = os.environ["AURA_INSTANCENAME"]
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
AUTH = (NEO4J_USERNAME, NEO4J_PASSWORD)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")

chat = ChatOpenAI(api_key=OPENAI_API_KEY)


kg = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
) 
#database=NEO4J_DATABASE,
## Creates a Neo4jGraph object kg, which allows you to query the Neo4j database using LangChain.
kg.query(
    """
     CREATE VECTOR INDEX health_providers_embeddings IF NOT EXISTS
     FOR (hp:HealthcareProvider) ON (hp.comprehensiveEmbedding)
     OPTIONS {
       indexConfig: {
         `vector.dimensions`: 1536,
         `vector.similarity_function`: 'cosine'
       }
     }
     """
 )

'''This creates a vector index named health_providers_embeddings:

On nodes with label HealthcareProvider.

Targets the property comprehensiveEmbedding (expected to be a vector).

Uses cosine similarity for comparing vectors.

1536 is the embedding dimension (typical for OpenAI's embedding models).

This index enables semantic vector search inside Neo4j.'''

 # test to see if the index was created
res = kg.query(
     """
   SHOW VECTOR INDEXES
   """
 )
print(res)
# Runs the Cypher query SHOW VECTOR INDEXES, which lists all vector indexes in the database.
# Prints the result to confirm the vector index was successfully created.

kg.query(
     """
     MATCH (hp:HealthcareProvider)-[:TREATS]->(p:Patient)
     WHERE hp.bio IS NOT NULL
     WITH hp, genai.vector.encode(
         hp.bio,
         "OpenAI",
         {
           token: $openAiApiKey,
           endpoint: $openAiEndpoint
         }) AS vector
     WITH hp, vector
     WHERE vector IS NOT NULL
     CALL db.create.setNodeVectorProperty(hp, "comprehensiveEmbedding", vector)
     """,
     params={
         "openAiApiKey": OPENAI_API_KEY,
         "openAiEndpoint": OPENAI_ENDPOINT,
     },
 )
'''
You're finding all healthcare providers with a non-null bio.

Using genai.vector.encode() to call OpenAI’s embedding API and convert each bio into a vector.

Storing the result in the comprehensiveEmbedding property of each node using db.create.setNodeVectorProperty().

This means each HealthcareProvider node now holds a semantic vector that represents the meaning of their bio.'''

result = kg.query(
     """
     MATCH (hp:HealthcareProvider)
     WHERE hp.bio IS NOT NULL
     RETURN hp.bio, hp.name, hp.comprehensiveEmbedding
     LIMIT 5
     """
 )
 '''Retrieves the bio, name, and comprehensiveEmbedding for 5 healthcare providers.

Useful for debugging to check that embeddings were correctly added.'''
# # loop through the results
for record in result:
     print(f" bio: {record["hp.bio"]}, name: {record["hp.name"]}")

# == Queerying the graph for a healthcare provider
question = "give me a list of healthcare providers in the area of dermatology"

# # Execute the query
result = kg.query(
    """
    WITH genai.vector.encode(
        $question,
        "OpenAI",
        {
          token: $openAiApiKey,
          endpoint: $openAiEndpoint
        }) AS question_embedding
    CALL db.index.vector.queryNodes(
        'health_providers_embeddings',
        $top_k,
        question_embedding
        ) YIELD node AS healthcare_provider, score
    RETURN healthcare_provider.name, healthcare_provider.bio, score
    """,
    params={
        "openAiApiKey": OPENAI_API_KEY,
        "openAiEndpoint": OPENAI_ENDPOINT,
        "question": question,
        "top_k": 3,
    },
)

# # # Print the encoded question vector for debugging
# # print("Encoded question vector:", result)

# # Print the result
for record in result:
    print(f"Name: {record['healthcare_provider.name']}")
    print(f"Bio: {record['healthcare_provider.bio']}")
    # print(f"Specialization: {record['healthcare_provider.specialization']}")
    # print(f"Location: {record['healthcare_provider.location']}")
    print(f"Score: {record['score']}")
    print("---")

'''
This is a content-based search.

You're asking: “Which healthcare provider bios are most semantically similar to this question?”

It's ignoring relationships, and focusing only on the content (bio) + vector similarity.

💡 No actual graph traversal like (a)-[:RELATION]->(b) is involved here.'''