from flask import request, jsonify
from app.services import langchain_service
import requests

ATHLETES_ENDPOINT = 'https://www.strava.com/api/v3/athletes'

def get_recommendations(access_token: str, athlete_id: str, athlete_location: str):
  athlete_stats_url = f'{ATHLETES_ENDPOINT}/{athlete_id}/stats'
  headers = {
      'Authorization': f'Bearer {access_token}'
  }

  try:
    response = requests.get(athlete_stats_url, headers=headers)

    if response.status_code != 200:
      return jsonify({'error': 'Failed to fetch athlete stats'}), response.status_code
    
    stats = response.json()
    recent_run_totals = stats.get('recent_run_totals')
    ytd_run_totals = stats.get('ytd_run_totals')
    print(f'recent stats: {recent_run_totals}\n')
    print(f'ytd stats: {ytd_run_totals}\n')

    recommendations = langchain_service.get_recommendations(location=athlete_location, recent_stats=recent_run_totals, ytd_stats=ytd_run_totals)
    return recommendations
  except Exception as e:
    print(f'Error fetching athlete stats: {e}')
    return jsonify({'error': 'Internal Server Error'}), 500