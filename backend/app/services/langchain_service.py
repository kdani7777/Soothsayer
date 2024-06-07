import os
import json
from langchain_community.document_loaders import S3DirectoryLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
from app.services import pinecone_service, retrieval_service, aws_service
from app.utils.helper_functions import build_prompt, pretty_print_context, format_contexts, get_current_datetime, get_recommendation_prompt
from flask import current_app

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME')
LLM = os.getenv('LLM')
EMBEDDING_MODEL = OpenAIEmbeddings(model=os.getenv('EMBEDDING_MODEL'))

def original_rag(prompt):
  """
  First attempt at implementing a RAG chain.
  """
  # set our llm
  llm = ChatGroq(temperature=0, model_name=LLM)

  # Load the contents of the S3 bucket
  loader = S3DirectoryLoader(bucket=os.getenv('S3_BUCKET'), prefix='race')
  documents = loader.load()

  # Split the document into chunks.
  text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=350, chunk_overlap=100, add_start_index=True
  )
  docs = text_splitter.split_documents(documents)
  
  # Embed and store document splits in a vector store
  # vector_store = PineconeVectorStore.from_documents(docs, EMBEDDING_MODEL, index_name=PINECONE_INDEX_NAME)
  vector_store = PineconeVectorStore.from_existing_index(index_name=PINECONE_INDEX_NAME, embedding=EMBEDDING_MODEL)

  # Initialize a retriever from our vector store
  retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 6})

  # Use a prompt for RAG that is checked into the LangChain prompt hub
  custom_rag_prompt = build_prompt()

  def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)
  
  rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | custom_rag_prompt
    | llm
    | StrOutputParser()
  )

  result = rag_chain.invoke(prompt)
  return result

def load_chunk_embed():
  """
  Load data from S3, process the data, batch upload the generated embeddings.
  """
  # Load the contents of the S3 bucket
  s3_documents = aws_service.load_docs()
  print('Begin upload of embeddings')
  pinecone_service.generate_and_async_batch_upload_embeddings(s3_documents)
  print('Finished upload of embeddings')

# load_chunk_embed()

def handle_query(query):
  """
  Retrieve relevant documents and run the given query through a RAG chain.
  """
  llm = ChatGroq(temperature=0, model_name=LLM)

  print(f"Pinecone Index Name: {PINECONE_INDEX_NAME}")

  retriever = current_app.retriever
  print(f"Retriever Configuration: {retriever}")

  retrieved_docs = retrieval_service.retrieve_docs_cohere_rerank(retriever=retriever, query=query)
  print("Retrieved Documents:")
  pretty_print_context(retrieved_docs)
  print('\n\n')

  prompt = build_prompt()
  curr_datetime = get_current_datetime()
  formatted_context = format_contexts(retrieved_docs)
 
  chain = (
    {'context': lambda x: formatted_context, 'current_datetime': lambda x: curr_datetime, 'query': RunnablePassthrough()}
     | prompt
     | llm
     | StrOutputParser()
  )

  return chain.invoke(query)

def get_recommendations(location: str, recent_stats, ytd_stats):
  """
  Retrieve relevant documents based on user data.
  """
  llm = ChatGroq(temperature=0, model_name=LLM)
  retriever = current_app.retriever
  prompt = get_recommendation_prompt(location=location, recent_stats=recent_stats, ytd_stats=ytd_stats)
  retrieved_docs = retrieval_service.retrieve_docs_cohere_rerank(retriever=retriever, query=prompt)
  race_jsons = [json.loads(json_str) for json_str in retrieved_docs]
  print("Retrieved Documents:")
  pretty_print_context(retrieved_docs)
  print('\n\n')
  return race_jsons