import os
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import json
import re
from typing import Iterable, List, Dict, Any
import uuid
from dotenv import load_dotenv
import itertools

# Load environment variables from .env file
load_dotenv()

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME')
EMBEDDING_MODEL = OpenAIEmbeddings(model=os.getenv('EMBEDDING_MODEL'))

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

def print_index_name() -> None:
  """Print the name of the Pinecone index being used."""
  print(PINECONE_INDEX_NAME)

def _chunk_docs_manually(documents: Iterable[Document]) -> List[Document]:
  """
  Manually split given documents into chunks via '\n\n'.

  Args:
  - documents (Iterable[Document]): The documents to split.

  Returns:
  - List[Document]: A list of chunked documents.
  """
  chunked_docs = []
  texts, metadatas = [], []
  for doc in documents:
    texts.append(doc.page_content)
    metadatas.append(doc.metadata)

  for i, text in enumerate(texts):
    race_list = text.split('\n\n')
    for race in race_list:
      new_doc = Document(page_content=race, metadata=metadatas[i].copy())
      chunked_docs.append(new_doc)
  
  return chunked_docs

def _chunk_docs_recursively(documents: Iterable[Document]) -> List[Document]:
  """
  Recursively split the given documents into smaller chunks.

  Args:
  - documents (Iterable[Document]): The documents to split.

  Returns:
  - List[Document]: A list of chunked documents.
  """
  CHUNK_SIZE = 400 # experiment using https://chunkviz.up.railway.app/#explanation
  CHUNK_OVERLAP = 0

  # Initialize our text splitter
  splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
    add_start_index=True
  )

  chunked_docs = splitter.split_documents(documents)
  return chunked_docs

def _generate_vectors(chunks: List[Document]) -> List[List[float]]:
  """
  Generate vector representations for each given chunk.

  Args:
  - chunks (List[Document]): The chunks to vectorize.

  Returns:
  - List[List[float]]: A list of vectors corresponding to the chunks.
  """
  page_contents = [chunk.page_content for chunk in chunks]
  vectors = EMBEDDING_MODEL.embed_documents(page_contents)
  print("Successfully generated vectors.")
  return vectors

def _extract_metadata(chunk: Document) -> Dict[str, Any]:
  """
  Extract and process metadata from a given document chunk.

  Args:
  - chunk (Document): The document chunk to process.

  Returns:
  - Dict[str, Any]: The processed metadata.
  """
  metadata_dict = chunk.metadata
  json_content = json.loads(chunk.page_content)

  # process date
  race_date = json_content['Race Date']
  # check for cancelled race and short circuit if true
  if "Cancelled" in race_date:
    metadata_dict['month'] = "Cancelled"
    metadata_dict['year'] = "Cancelled"
    return metadata_dict
  day_of_week, rest = race_date.split(' - ')
  # Check for "tentative" race date
  print(rest)
  #TODO: handle "Unknown Year" adequately
  if "Tentative" in rest or "TBD" in rest or "Unknown Year" in rest or "Past Date" in rest:
    metadata_dict['month'] = "Tentative"
    metadata_dict['year'] = "Tentative"
    return metadata_dict
  month_and_day, year = rest.split(', ')
  month, day = month_and_day.split(' ')

  # process location
  race_location = json_content['Location']
  try:
    city, state = race_location.split(', ')
  except Exception as e:
    #TODO: fix scraping script to handle races such as Badwater Ultramarathon that has different start and finish
    city = "check"
    state = "details"

  # process available distances
  race_distances = json_content['Distances Available']
  # match one or more digits, optional dot, optional more digits, optional whitespace, one or more distance units
  distance_list = list(set(re.findall(r'\d+\.?\d*\s*(?:M|K)', race_distances)))

  metadata_dict = chunk.metadata
  metadata_dict['city'] = city
  metadata_dict['state'] = state
  metadata_dict['distances'] = distance_list
  metadata_dict['text'] = chunk.page_content
  metadata_dict['month'] = month
  metadata_dict['year'] = year    
  
  return metadata_dict

def generate_embeddings(documents: Iterable[Document]) -> List[Dict[str, Any]]:
  """
  Generate embeddings with metadata for the given documents.

  Args:
  - documents (Iterable[Document]): The documents to process and upload.
  """
  polished_embeddings = []
  chunks = _chunk_docs_manually(documents)
  vectors_list = _generate_vectors(chunks)
  chunk_num = 0
  print(f'Number of chunks: {len(chunks)}')

  for chunk in chunks:
    # process chunk metadata
    metadata = _extract_metadata(chunk)

    # create full embedding
    embedding = {
      'id': str(uuid.uuid4()),
      'values': vectors_list[chunk_num],
      'metadata': metadata
    }

    polished_embeddings.append(embedding)
    chunk_num += 1
  
  return polished_embeddings


def generate_and_upload_embeddings(documents: Iterable[Document]) -> None:
  """
  Generate embeddings with metadata for given documents and upload to Pinecone index.

  Args:
  - documents (Iterable[Document]): The documents to process and upload.
  """
  polished_embeddings = generate_embeddings(documents=documents)
  if len(polished_embeddings) > 0:
    index.upsert(polished_embeddings)
    print(f'Uploaded embeddings to {PINECONE_INDEX_NAME}')
  else:
    print('No embeddings to upload.')

def batches(iterable: Iterable[Any], batch_size: int = 100) -> Iterable[tuple]:
  """
  Helper function to break an iterable into chunks of a specified batch size.

  Args:
  - iterable (Iterable[Any]): The iterable to break into chunks.
  - batch_size (int, optional): The size of each chunk. Defaults to 100.

  Yields:
  - Iterable[tuple]: Chunks of the input iterable.
  """
  it = iter(iterable)
  batch = tuple(itertools.islice(it, batch_size))

  while batch:
    yield batch
    batch = tuple(itertools.islice(it, batch_size))

def generate_and_batch_upload_embeddings(documents: Iterable[Document]) -> None:
  """
  Generate embeddings with metadata for given documents and **batch** upload to Pinecone index.

  Args:
  - documents (Iterable[Document]): The documents to process and upload.
  """
  polished_embeddings = generate_embeddings(documents=documents)
  
  # batch upsert
  for embedding_batch in batches(polished_embeddings, batch_size=100):
    index.upsert(vectors=embedding_batch)

def generate_and_async_batch_upload_embeddings(documents: Iterable[Document]) -> None:
  """
  Generate embeddings with metadata for given documents and (asynchronously) **batch** upload to Pinecone index.

  Args:
  - documents (Iterable[Document]): The documents to process and upload.
  """
  polished_embeddings = generate_embeddings(documents=documents)

  # Batch upsert data with 100 vectors per upsert request asynchronously
  with pc.Index(PINECONE_INDEX_NAME, pool_threads=30) as index:
    # Send requests in parallel
    async_results = [
      index.upsert(vectors=embedding_batch, async_req=True)
      for embedding_batch in batches(polished_embeddings, batch_size=100)
    ]
    # Wait for and retrieve responses (this raises in case of error)
    [async_result.get() for async_result in async_results]


def upload_docs(chunks: List[Document], index_name: str) -> PineconeVectorStore:
  """
  Embed docs directly into a Pinecone index.

  Args:
  - chunks (List[Document]): The document chunks to embed and upload.
  - index_name (str): The name of the Pinecone index.

  Returns:
  - PineconeVectorStore: The vector store containing the embedded documents.
  """
  vector_store = PineconeVectorStore.from_documents(documents=chunks, embedding=EMBEDDING_MODEL, index_name=index_name)
  return vector_store

def load_index() -> PineconeVectorStore:
  """
  Load a pre-indexed collection of embeddings.

  Returns:
  - PineconeVectorStore: The loaded vector store.
  """
  vector_store = PineconeVectorStore.from_existing_index(index_name=PINECONE_INDEX_NAME, embedding=EMBEDDING_MODEL)
  return vector_store

def delete_index(index_name: str) -> None:
  """
  Delete a Pinecone index.

  Args:
  - index_name (str): The name of the Pinecone index to delete.
  """
  pc.delete_index(index_name)
  print(f'Deleted {index_name} successfully.')