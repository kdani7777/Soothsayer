import os
from langchain_community.document_loaders import S3DirectoryLoader

S3_BUCKET = os.getenv('S3_BUCKET')
PREFIX = 'short'

def load_docs():
  """
  Load the contents of the S3 bucket.
  """
  loader = S3DirectoryLoader(bucket=S3_BUCKET, prefix=PREFIX)
  documents = loader.load()
  return documents