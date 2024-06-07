import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import boto3
import os
import asyncio
import aiohttp

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

# Function to scrape race information from a single page
async def scrape_race_info_async(session, url):
	async with session.get(url) as response:
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
					'Race Date': race_date,
					'Race Name': race_name,
					'Distances Available': race_distances,
					'Location': race_location
				}
				
				if len(race_links) > 1:
					race_info['Race Info'] = race_links[0]
					race_info['Race Signup'] = race_links[1]
				else:
					race_info['Race Info'] = race_links[0]

				race_info_list.append(race_info)
			
			return race_info_list
		else:
			print("Failed to fetch page:", response.status)
			return []
	
def format_date(date_string):
	# Split string by new line character
	date_components = date_string.split('\n')

	# Extract day and date
	date = date_components[0]
	day = date_components[1]

	formatted_date = f"{day} - {date}"
	return formatted_date

def gather_race_links(race_details):
	link_base = os.getenv('LINKS_BASE')
	links = race_details.find_all('a')
	race_info = []
	for link in links:
		full_link = link_base + link.get('href')
		race_info.append(full_link)
	  
	return race_info

def get_race_city(race_location):
	location = race_location.text.strip()
	location_parts = location.split("\n", 1)
	return location_parts[0]

def get_race_distances(race_distances):
	distances = race_distances.find_all('div')[1].text.strip()
	# distances = distances.split(',')
	return distances

# Function to scrape races from multiple pages
async def fetch_all_races(session, base_url, num_pages, state_name):
	all_races = []
	total_races = 0

	with tqdm(total=num_pages, desc=f"Scraping Races for {state_name}") as pbar:
		for page_num in range(1, num_pages + 1):
			url = f"{base_url}/page-{page_num}"
			race_info_list = await scrape_race_info_async(session, url)
			all_races.extend(race_info_list)
			total_races += len(race_info_list)
			pbar.update(1)

	print(f"Scraped {total_races} races for {state_name}")
	return all_races

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


# Main function
async def main():
	base_url = os.environ['SCRAPING_URL']
	num_pages = 3  # Number of pages to scrape (adjust as needed)
	bucket_name = os.environ['S3_BUCKET']
	
	async with aiohttp.ClientSession() as session:
		tasks = []
		# Iterate over states
		for state_abbr, state_name in STATES_MAP.items():
			state_base_url = f'{base_url}/{state_abbr.lower()}/upcoming'
			tasks.append(fetch_all_races(session, state_base_url, num_pages, state_name))
			
		all_races = await asyncio.gather(*tasks)

		for state_name, races in zip(STATES_MAP.values(), all_races):
			text_data = '\n'.join([f"Race {i+1}:\n{race}\n" for i, race in enumerate(races)])
			file_name = f'{state_name}_race_information.txt'
			object_key = f'race-data/{state_name}/{file_name}'
			await upload_text_data_to_s3(text_data, bucket_name, object_key)

def lambda_handler(event, context):
	asyncio.run(main())

if __name__ == "__main__":
	lambda_handler(None, None)