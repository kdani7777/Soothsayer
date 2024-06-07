import os
from flask import Flask
from flask_cors import CORS
from app.services import pinecone_service, retrieval_service

def create_app(test_config=None):
  # create and configure the app
  app = Flask(__name__, instance_relative_config=True)
  
  # Enable CORS for all routes
  CORS(app)

  # Initialize global variables
  vector_store = pinecone_service.load_index()
  retriever = retrieval_service.get_retriever(vector_store)
  
  # Store in current_app
  app.vector_store = vector_store
  app.retriever = retriever

  if test_config is None:
    # load the instance config, if it exists, when not testing
    app.config.from_pyfile('config.py', silent=True)
  else:
    app.config.from_mapping(test_config)
  
  # ensure the instance folder exists
  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass

  # register api blueprint
  from app.api import routes
  app.register_blueprint(routes.bp)

  return app