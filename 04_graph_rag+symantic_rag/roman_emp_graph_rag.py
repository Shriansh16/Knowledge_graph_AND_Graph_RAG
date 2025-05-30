from dotenv import load_dotenv
import os
from langchain_neo4j import Neo4jGraph

from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from pydantic import BaseModel, Field
# from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Tuple, List
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import WikipediaLoader
from langchain.text_splitter import TokenTextSplitter
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer

from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_neo4j.vectorstores.neo4j_vector import remove_lucene_chars

load_dotenv()

AURA_INSTANCENAME = os.environ["AURA_INSTANCENAME"]
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
AUTH = (NEO4J_USERNAME, NEO4J_PASSWORD)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")

chat = ChatOpenAI(api_key=OPENAI_API_KEY, temperature=0, model="gpt-4o-mini")


kg = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
) #database=NEO4J_DATABASE,
# Connects to the Neo4j database where the graph data will be stored.
# # # read the wikipedia page for the Roman Empire
raw_documents = WikipediaLoader(query="The Roman empire").load()

# # # # # Define chunking strategy
text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=24)
documents = text_splitter.split_documents(raw_documents[:3])
print(documents)
'''Retrieves Wikipedia content related to “The Roman Empire.”

Splits into chunks for better LLM handling (512 token chunks, overlapping by 24).'''

# Convert Text to Graph Structure
llm_transformer = LLMGraphTransformer(llm=chat)
graph_documents = llm_transformer.convert_to_graph_documents(documents)
'''Uses LLM to identify entities, relationships, and structure.

Converts text chunks into graph documents.
LLMGraphTransformer uses GPT to convert text chunks into graph structures—identifying nodes (entities) and edges (relations).

These graph docs are then saved into Neo4j.'''

# # store to neo4j
res = kg.add_graph_documents(
     graph_documents,
     include_source=True,
     baseEntityLabel=True,
 )
 '''Stores the graph in Neo4j.

Includes source text and labels for querying later.'''

# # MATCH (n) DETACH DELETE n - use this cyper command to delete the Graphs present in neo4j

# Hybrid Retrieval for RAG
# create vector index
vector_index = Neo4jVector.from_existing_graph(
    OpenAIEmbeddings(),
    search_type="hybrid",
    node_label="Document",
    text_node_properties=["text"],
    embedding_node_property="embedding",
)
'''
Creates a hybrid vector retriever using Neo4jVector.

Stores embeddings (via OpenAIEmbeddings) inside Neo4j.

Allows semantic search over the unstructured chunks.
'''


# Extract entities from text
#Specifies output format of entity extraction
class Entities(BaseModel):
    """Identifying information about entities.
    Uses GPT to extract entities like people and organizations from the user query."""

    names: List[str] = Field(
        ...,
        description="All the person, organization, or business entities that "
        "appear in the text",
    )


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are extracting organization and person entities from the text.",
        ),
        (
            "human",
            "Use the given format to extract information from the following "
            "input: {question}",
        ),
    ]
)
entity_chain = prompt | chat.with_structured_output(Entities)

# # Test it out:
# res = entity_chain.invoke(
#     {"question": "In the year of 123 there was an emperor who did not like to rule"}
# ).names
# print(res)

# Who is Ceaser?
# In the year of 123 there was an emperor who did not like to rule. 

# Retriever
kg.query("CREATE FULLTEXT INDEX entity IF NOT EXISTS FOR (e:__Entity__) ON EACH [e.id]")
# You're creating a search index for all the entity names in your Neo4j database, 
# so you can quickly search for things like “Caesar” or “Roman Empire” later.

def generate_full_text_query(input: str) -> str:
    """
    Generate a full-text search query for a given input string.

    This function constructs a query string suitable for a full-text search.
    It processes the input string by splitting it into words and appending a
    similarity threshold (~2 changed characters) to each word, then combines
    them using the AND operator. Useful for mapping entities from user questions
    to database values, and allows for some misspelings.
    """
    full_text_query = ""
    words = [el for el in remove_lucene_chars(input).split() if el]
    for word in words[:-1]:
        full_text_query += f" {word}~2 AND"
    full_text_query += f" {words[-1]}~2"
    return full_text_query.strip()


# Fulltext index query
def structured_retriever(question: str) -> str:
    """
    Collects the neighborhood of entities mentioned
    in the question
    """
    result = ""
    entities = entity_chain.invoke({"question": question})
    for entity in entities.names:
        print(f" Getting Entity: {entity}")
        response = kg.query(
            """CALL db.index.fulltext.queryNodes('entity', $query, {limit:2})
            YIELD node,score
            CALL {
              WITH node
              MATCH (node)-[r:!MENTIONS]->(neighbor)
              RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output
              UNION ALL
              WITH node
              MATCH (node)<-[r:!MENTIONS]-(neighbor)
              RETURN neighbor.id + ' - ' + type(r) + ' -> ' +  node.id AS output
            }
            RETURN output LIMIT 50
            """,
            {"query": generate_full_text_query(entity)},
        )
        # print(response)
        result += "\n".join([el["output"] for el in response])
    return result
'''
Extracts entities (people, organizations) from the user's question using the entity_chain.

Searches Neo4j for those entities using full-text index and the fuzzy query from the previous function.

Finds their relationships in the graph (what they’re connected to).

Returns text output showing those connections.'''

# print(structured_retriever("Who is Aurelian?"))


# Final retrieval step
def retriever(question: str):
    print(f"Search query: {question}")
    structured_data = structured_retriever(question)
    unstructured_data = [
        el.page_content for el in vector_index.similarity_search(question)
    ]
    final_data = f"""Structured data:
{structured_data}
Unstructured data:
{"#Document ". join(unstructured_data)}
    """
    print(f"\nFinal Data::: ==>{final_data}")
    return final_data

'''Gets structured data using the structured_retriever() → from Neo4j Graph.

Gets unstructured data using vector search from vector_index.similarity_search(question) → from Wikipedia chunks.

Combines both and prints it.'''

# Define the RAG chain
# Condense a chat history and follow-up question into a standalone question
_template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question,
in its original language.
Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question:"""  # noqa: E501
CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)


def _format_chat_history(chat_history: List[Tuple[str, str]]) -> List:
    buffer = []
    for human, ai in chat_history:
        buffer.append(HumanMessage(content=human))
        buffer.append(AIMessage(content=ai))
    return buffer
'''
It converts:
[("Who was the first emperor?", "Augustus was the first emperor.")]
into LangChain messages:
[HumanMessage("Who was..."), AIMessage("Augustus was...")]
'''


_search_query = RunnableBranch(
    # If input includes chat_history, we condense it with the follow-up question
    (
        RunnableLambda(lambda x: bool(x.get("chat_history"))).with_config(
            run_name="HasChatHistoryCheck"
        ),  # Condense follow-up question and chat into a standalone_question
        RunnablePassthrough.assign(
            chat_history=lambda x: _format_chat_history(x["chat_history"])
        )
        | CONDENSE_QUESTION_PROMPT
        | ChatOpenAI(temperature=0)
        | StrOutputParser(),
    ),
    # Else, we have no chat history, so just pass through the question
    RunnableLambda(lambda x: x["question"]),
)

template = """Answer the question based only on the following context:
{context}

Question: {question}
Use natural language and be concise.
Answer:"""
prompt = ChatPromptTemplate.from_template(template)

chain = (
    RunnableParallel(
        {
            "context": _search_query | retriever,
            "question": RunnablePassthrough(),
        }
    )
    | prompt
    | chat
    | StrOutputParser()
)

# # TEST it all out!
# res_simple = chain.invoke(
#     {
#         "question": "How did the Roman empire fall?",
#     }
# )

# print(f"\n Results === {res_simple}\n\n")

res_hist = chain.invoke(
    {
        "question": "When did he become the first emperor?",
        "chat_history": [
            ("Who was the first emperor?", "Augustus was the first emperor.")
        ],
    }
)

print(f"\n === {res_hist}\n\n")