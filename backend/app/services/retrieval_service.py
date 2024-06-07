from langchain_core.vectorstores import VectorStoreRetriever
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.chains.query_constructor.base import AttributeInfo
from langchain_cohere import CohereRerank
from typing import List
import os
import cohere

SEARCH_TYPE = 'similarity'
RETRIEVE_TOP_K = 20
RERANK_TOP_N = 5
COHERE_API_KEY = os.getenv('COHERE_API_KEY')
COHERE_MODEL = 'rerank-english-v3.0'
CROSS_ENCODER_MODEL = 'BAAI/bge-reranker-base'

co = cohere.Client(COHERE_API_KEY)

def get_retriever(vector_store: PineconeVectorStore) -> VectorStoreRetriever:
  """
  Creates a VectorStoreRetriever from a given Pinecone vector store.
  
  Args:
  - vector_store (PineconeVectorStore): The Pinecone vector store to create the retriever from.
  
  Returns:
  - VectorStoreRetriever: The configured retriever.
  """
  retriever = vector_store.as_retriever(
    search_type=SEARCH_TYPE, 
    search_kwargs={"k": RETRIEVE_TOP_K}
  )
  return retriever

def get_selfquery_retriever(llm: BaseLanguageModel, vector_store: VectorStore) -> SelfQueryRetriever:
  """
  Creates and returns a SelfQueryRetriever instance configured with the given
  language model and vector store. This retriever is tailored to handle documents
  containing details about races.

  Args:
  - llm (BaseLanguageModel): A BaseLanguageModel instance used for processing and understanding queries.
  - vector_store (VectorStore): A VectorStore instance where document vectors are stored and retrieved from.

  Returns:
  - A SelfQueryRetriever instance configured with the provided language model and
      vector store.
  """
  document_content_description = "Details of a single race, consisting of the name, date, distances, location and sign up link"
  metadata_field_info = [
    AttributeInfo(
      name="city",
      description="The city in which the race is located.",
      type="string",
    ),
    AttributeInfo(
      name="state",
      description="The state in which the race is located.",
      type="string",
    ),
    AttributeInfo(
      name="distances",
      description="The race distances that are available.",
      type="string",
    ),
    AttributeInfo(
      name="text",
      description="The full details of the race.",
      type="string",
    ),
    AttributeInfo(
      name="month",
      description="The month during which the race takes place.",
      type="string",
    ),
    AttributeInfo(
      name="year",
      description="The year during which the race takes place.",
      type="string",
    ),
  ]
  retriever = SelfQueryRetriever.from_llm(
    llm=llm,
    vectorstore=vector_store,
    document_contents=document_content_description,
    metadata_field_info=metadata_field_info,
    verbose=True
  )
  return retriever


def retrieve_docs(retriever: VectorStoreRetriever, query: str) -> List[Document]:
  """
  Retrieves documents from the vector store based on a query.
  
  Args:
  - retriever (VectorStoreRetriever): The retriever to use for document retrieval.
  - query (str): The query string to search for.
  
  Returns:
  - List[Document]: A list of retrieved documents.
  """
  retrieved_docs = retriever.invoke(query)
  return retrieved_docs

def retrieve_docs_cohere_rerank(retriever: VectorStoreRetriever, query: str) -> List[str]:
  """
  Retrieves documents from the vector store and reranks them using the Cohere Reranker.
  
  Args:
  - retriever (VectorStoreRetriever): The retriever to use for document retrieval.
  - query (str): The query string to search for.
  
  Returns:
  - List[str]: A list of reranked document contents.
  """
  retrieved_docs = retrieve_docs(retriever=retriever, query=query)
  if len(retrieved_docs) == 0:
    return []
  # compressor = CohereRerank()
  # compression_retriever = ContextualCompressionRetriever(
  #   base_compressor=compressor,
  #   base_retriever=retriever)
  # compression_retriever.invoke(query)
  rerank_content = [doc.page_content for doc in retrieved_docs]
  reranked_docs = co.rerank(model=COHERE_MODEL, query=query, 
                            top_n=RERANK_TOP_N, documents=rerank_content,
                            return_documents=True)
  contexts = [doc.document.text for doc in reranked_docs.results]
  return contexts

def retrieve_docs_crossencoder_rerank(retriever: VectorStoreRetriever, query: str) -> List[Document]:
  """
  Retrieves documents from the vector store and reranks them using a CrossEncoder model.
  
  Args:
  - retriever (VectorStoreRetriever): The retriever to use for document retrieval.
  - query (str): The query string to search for.
  
  Returns:
  - List[Document]: A list of reranked documents.
  """
  model = HuggingFaceCrossEncoder(model_name=CROSS_ENCODER_MODEL)
  compressor = CrossEncoderReranker(model=model, top_n=RERANK_TOP_N)
  compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor, base_retriever=retriever
  )
  compressed_docs = compression_retriever.invoke(query)
  return compressed_docs