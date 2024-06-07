from flask import Blueprint
from flask import request, jsonify
from app.services import langchain_service, strava_service
import requests

bp = Blueprint("api", __name__)

@bp.route("/hello")
def hello():
  return "hello world"

@bp.route("/chat", methods=['GET', 'POST'])
def chat():
  if request.method == 'GET':
    pass
  elif request.method == 'POST':
    # process user query and generate a response
    query = request.json['query']
    if not query:
      return jsonify({"error": "No query provided"}), 400
    
    answer = langchain_service.handle_query(query=query)
    return jsonify({ "query": query, "answer": answer })

@bp.route("/recommendations", methods=['POST'])
def recommendations():
  data = request.json
  athlete_id = data.get('id')
  athlete_location = data.get('location')
  print(athlete_id)
  print(athlete_location)
  auth_header = request.headers.get('Authorization')

  if not athlete_id:
    return jsonify({'error': 'Athlete ID is required'}), 400
  
  if not auth_header:
    return jsonify({'error': 'Authorization header is missing'}), 401
  
  # Extract the token from the header
  access_token = auth_header.split(" ")[1] # Might need to handle the token more securely
  
  recommendations = strava_service.get_recommendations(access_token=access_token, athlete_id=athlete_id, athlete_location=athlete_location)
  return jsonify({ "recommendations": recommendations })