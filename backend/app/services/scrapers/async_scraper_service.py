import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import boto3
import os
import asyncio
from aiologger import Logger
from aiologger.handlers.streams import AsyncStreamHandler
from aiologger.formatters.base import Formatter
from aiologger.levels import LogLevel
import aiohttp
import time
import random
import datetime

# Initialize logger
logger = Logger.with_default_handlers(name="race_scraping_logger")

STATES_MAP = {
  'AL': 'alabama', 'AK': 'alaska', 'AZ': 'arizona', 'AR': 'arkansas','CA': 'california', 'CO': 'colorado', 'CT': 'connecticut',
  'DE': 'delaware', 'DC': 'district_of_columbia', 'FL': 'florida','GA': 'georgia', 'HI': 'hawaii', 'ID': 'idaho', 'IL': 'illinois',
  'IN': 'indiana', 'IA': 'iowa', 'KS': 'kansas', 'KY': 'kentucky', 'LA': 'louisiana', 'ME': 'maine', 'MD': 'maryland', "MA": 'massachusetts',
  'MI': 'michigan', 'MN': 'minnesota', 'MS': 'mississippi', 'MO': 'missouri', 'MT': 'montana', 'NE': 'nebraska', 'NV': 'nevada',
  'NH': 'new hampshire', 'NJ': 'new jersey', 'NM': 'new mexico', 'NY': 'new york', 'NC': 'north carolina', 'ND': 'north dakota',
  'OH': 'ohio', 'OK': 'oklahoma', 'OR': 'oregon', 'PA': 'pennsylvania', 'RI': 'rhode_island', 'SC': 'south carolina', 'SD': 'south dakota',
  'TN': 'tennessee', 'TX': 'texas', 'UT': 'utah', 'VT': 'vermont', 'VA': 'virginia', 'WA': 'washington', 'WV': 'west_virginia',
  'WI': 'wisconsin', 'WY': 'wyoming'
}

SMALLER_MAP = {
  'CA': 'california', 'FL': 'florida'
}

USER_AGENTS = [
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
	"Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9",
	"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
  "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1"
]

async def scrape_race_info_async(session, url):
  """
  Scrapes information for all races on a single page

  Args:
  - session (aiohttp.ClientSession): An aiohttp ClientSession object for making HTTP requests.
  - url (str): The URL of the page to scrape.
  
  Returns:
  - list: A list of dictionaries containing race information.
  """
  
	# Use a random user-agent to make the requests for throttling purposes
  user_agent = random.choice(USER_AGENTS) 
  headers = {
    'User-Agent': user_agent, # specifies the browser/application that sent the request
    'Referer': 'https://www.google.com' # specifies the website you were redirected from
  }
  
  async with session.get(url, headers=headers) as response:
    if response.status == 200:
      html = await response.text()
      soup = BeautifulSoup(html, 'html.parser')
      races = soup.find_all('tr', class_='')

      race_info_list = []
      for race in races:
        # Find all race details for each race
        race_details = race.find_all('td')

        # handle Boston Qualifer rows
        if len(race_details[0].find_all('small')) > 0:
          continue

        race_date = format_date(race_details[1].text.strip())
        race_name = race_details[2].find('b').text.strip()
        race_links = gather_race_links(race_details[2])
        race_distances = get_race_distances(race_details[2])
        race_location = get_race_city(race_details[3])

        race_info = {
          "Race Date": race_date,
          "Race Name": race_name,
          "Distances Available": race_distances,
          "Location": race_location
        }
        
        if len(race_links) > 1:
          race_info["Race Info"] = race_links[0]
          race_info["Race Signup"] = race_links[1]
        else:
          race_info["Race Info"] = race_links[0]

        race_info_list.append(race_info)
      
      return race_info_list
    else:
      print("Failed to fetch page:", response.status)
      return []
  
def format_date(date_string):
  """
  Formats the date stirng.
  
	Args:
  - date_string (str): The date string to format.
  
  Returns:
  - str: The formatted date string.
  """
  # Split string by new line character
  date_components = date_string.split('\n')

  # Extract day and date
  date = date_components[0]
  day = date_components[1]

  formatted_date = f"{day} - {date}"
  return formatted_date

def gather_race_links(race_details):
  """
  Gathers race links from race details.
  
  Args:
  - race_details (bs4.element.Tag): The race details.
  
  Returns:
  - list: A list of race links.
	"""
  link_base = os.getenv('LINKS_BASE')
  links = race_details.find_all('a')
  race_info = []
  for link in links:
    full_link = link_base + link.get('href')
    race_info.append(full_link)
    
  return race_info

def get_race_city(race_location):
  """
  Extracts the race city from race location.
  
  Args:
  - race_location (bs4.element.Tag): The race location.
  
  Returns:
  - str: The race city.
  """
  location = race_location.text.strip()
  location_parts = location.split("\n", 1)
  return location_parts[0]

def get_race_distances(race_distances):
  """
  Extracts race distances from race details.
  
  Args:
  - race_distances (bs4.element.Tag): The race distances element.
  
  Returns:
  - str: The race distances.
  """
  distances = race_distances.find_all('div')[1].text.strip()
  # distances = distances.split(',')
  return distances

async def fetch_all_races(session, base_url, num_pages, state_name):
  """
  Fetches all races over multiple pages for a given state.
  
  Args:
  - session (aiohttp.ClientSession): An aiohttp ClientSession object for making HTTP requests.
  - base_url (str): The base URL of the website to scrape.
  - num_pages (int): The number of pages to scrape.
  - state_name (str): The name of the state for which races are being fetched.
  
  Returns:
  - list: A list containing dictionaries of race information.
  """
  all_races_set = set()
  total_races = 0
  start_time = time.time()

  with tqdm(total=num_pages, desc=f"Scraping Races for {state_name}") as pbar:
    for page_num in range(1, num_pages + 1):
      url = f"{base_url}/page-{page_num}"
      await asyncio.sleep(random.uniform(1,5))
      race_info_list = await scrape_race_info_async(session, url)
      total_races += len(race_info_list)

      # remove duplicate race entries
      for race_info in race_info_list:
        race_info_tuple = tuple(race_info.items())
        if race_info_tuple not in all_races_set:
          all_races_set.add(race_info_tuple)
      
      pbar.update(1)

  elapsed_time = time.time() - start_time
  await logger.info(f"Scraped {total_races} races for {state_name}. Elapsed time: {elapsed_time} seconds.")
  # return all_races
  return [dict(race_info_tuple) for race_info_tuple in all_races_set]

def upload_json_data_to_s3(json_data, bucket_name, object_key):
  """
  Uploads JSON data to an Amazon S3 bucket.

  Args:
  - json_data (dict): JSON data to upload.
  - bucket_name (str): Name of the S3 bucket to upload the data to.
  - object_key (str): Key/name of the object in the S3 bucket.

  Returns:
  - bool: True if the upload was successful, False otherwise.
  """
  try:
    # Initialize the S3 client
    s3_client = boto3.client('s3')

    # Convert JSON data to string
    json_string = json.dumps(json_data)

    # Upload JSON data to S3 bucket
    s3_client.put_object(Body=json_string, Bucket=bucket_name, Key=object_key)

    print(f"JSON data uploaded to S3 bucket: s3://{bucket_name}/{object_key}")
    return True

  except Exception as e:
    print(f"Error uploading JSON data to S3 bucket: {e}")
    return False

async def upload_text_data_to_s3(text_data, bucket_name, object_key):
  """
  Uploads text data to an Amazon S3 bucket.

  Args:
  - text_data (str): Text data to upload.
  - bucket_name (str): Name of the S3 bucket to upload the data to.
  - object_key (str): Key/name of the object in the S3 bucket.

  Returns:
  - bool: True if the upload was successful, False otherwise.
  """
  try:
    # Initialize the S3 client
    s3_client = boto3.client('s3')

    # Upload text data to S3 bucket; stream to S3 in chunks as it is being read
    stream = s3_client.put_object(Body=text_data, Bucket=bucket_name, Key=object_key)

    print(f"Text data uploaded to S3 bucket: s3://{bucket_name}/{object_key}")
    return True

  except Exception as e:
    print(f"Error uploading text data to S3 bucket: {e}")
    return False

async def scrape_state_races(session, state_abbr):
  """
  Scrapes races for a specific state.

  Args:
  - session (aiohttp.ClientSession): An aiohttp ClientSession object for making HTTP requests.
  - state_abbr (str): The state to scrape.

  Returns:
  - list: A list containing dictionaries of race information.
  """
  state_name = STATES_MAP[state_abbr]
  base_url = os.environ['SCRAPING_URL']
  state_url = f'{base_url}/{state_abbr.lower()}/upcoming'
  NUM_PAGES = 7

  races = await fetch_all_races(session, state_url, NUM_PAGES, state_name)
  return races

# Main function
async def main():
  """
  The main coroutine.
  """
  states_list = list(STATES_MAP.keys())
  BATCH_SIZE = 3

  # split the states_list into batches
  state_batches = [states_list[i:i + BATCH_SIZE] for i in range(0, len(states_list), BATCH_SIZE)]
  
  async with aiohttp.ClientSession() as session:
    for batch in state_batches:
      tasks = []
      for state in batch:
        tasks.append(scrape_state_races(session, state))
      
      results = await asyncio.gather(*tasks)
      for state, races in zip(batch, results):
        races_json = [json.dumps(race) for race in races]
        text_data = '\n\n'.join(races_json)
        file_name = f'../../../data/race_data_latest/{STATES_MAP[state]}_race_information.txt'

        # Write information to file
        with open(file_name, 'w') as file:
          file.write(text_data)

      # introduce a delay between batches of states
      delay = random.uniform(5,10)
      await asyncio.sleep(delay)
      print(f'Batch Delay: {delay}')

if __name__ == "__main__":
  start = time.time()
  # Create an event loop and run the main coroutine
  asyncio.run(main())
  end = time.time()
  print(f'Total time spent scraping: {str(datetime.timedelta(seconds=(end-start)))}')
