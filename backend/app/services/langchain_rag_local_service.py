from langchain_openai import ChatOpenAI
import bs4
import os
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

LLM = "gpt-3.5-turbo-0125"
FILE_LOADER_TYPE = TextLoader
EMBEDDING_MODEL = OpenAIEmbeddings()

PROMPT_TEMPLATE = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Use three sentences maximum and keep the answer as concise as possible.
Always say "thanks for asking!" at the end of the answer.

{context}

Question: {question}

Helpful Answer:"""

SAMPLE_USER_QUERY = "I typically run 1 mile a day. I want to race at the end of April. I live in LA. What race should I sign up for? Please provide a link as well"

def run_rag(prompt):
  # set our llm
  llm = ChatOpenAI(model=LLM, api_key=OPENAI_API_KEY)

  # Load the contents of the race_information.txt file (MUST BE LOCAL)
  loader = DirectoryLoader('./', glob="**/race_information.txt", loader_cls=FILE_LOADER_TYPE)
  docs = loader.load()

  # Split the document into chunks.
  text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, chunk_overlap=100, add_start_index=True
  )
  all_splits = text_splitter.split_documents(docs)

  # Embed and store document splits in a vector store
  vector_store = Chroma.from_documents(documents=all_splits, embedding=EMBEDDING_MODEL)

  # Initialize a retriever from our vector store
  retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 6})

  # Use a prompt for RAG that is checked into the LangChain prompt hub
  custom_rag_prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)

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

print(run_rag(SAMPLE_USER_QUERY))