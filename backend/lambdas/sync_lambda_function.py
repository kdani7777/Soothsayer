import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import boto3
import os

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
def scrape_race_info(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
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
        print("Failed to fetch page:", response.status_code)
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
def scrape_all_races(base_url, num_pages, state_name):
    all_races_set = set()
    total_races = 0

    with tqdm(total=num_pages, desc=f"Scraping Races for {state_name}") as pbar:
        for page_num in range(1, num_pages + 1):
            url = f"{base_url}/page-{page_num}"
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                races = soup.find_all('tr', class_='')
                total_races += len(races) # Calculate the total number of races to be scraped
                
                for race_info in scrape_race_info(url):
                    # Convert race_info dictionary to a list of tuples (key, value) to make it hashable and then convert to one big tuple
                    race_info_tuple = tuple(race_info.items())
                    # This check will give us better performance if our race_info objects become more complex,
                    # otherwise it's not necessary since we are working with sets already
                    if race_info_tuple not in all_races_set:
                        all_races_set.add(race_info_tuple)
                        # all_races.append(race_info)
                
                pbar.update(1)  # Update progress bar for each page scraped
            else:
                print(f"Failed to fetch page {page_num}:", response.status_code)
                break # stop scraping for this state if the page fails to load

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

def upload_text_data_to_s3(text_data, bucket_name, object_key):
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

        # # Calculate the chunk size
        # chunk_size = 1024  # Adjust as needed
        # chunks = [text_data[i:i+chunk_size] for i in range(0, len(text_data), chunk_size)]

        # # Upload each chunk to S3 bucket
        # for i, chunk in enumerate(chunks):
        #     s3_client.upload_part(Body=chunk, Bucket=bucket_name, Key=object_key, PartNumber=i+1)

        print(f"Text data uploaded to S3 bucket: s3://{bucket_name}/{object_key}")
        return True

    except Exception as e:
        print(f"Error uploading text data to S3 bucket: {e}")
        return False


# Main function
def main():
    base_url = os.environ['SCRAPING_URL']
    num_pages = 3  # Number of pages to scrape (adjust as needed)
    bucket_name = os.environ['S3_BUCKET']
    batch_size = 20
    
    # Iterate over states
    for state_abbr, state_name in STATES_MAP.items():
        state_base_url = f'{base_url}/{state_abbr.lower()}/upcoming'
        state_races = scrape_all_races(state_base_url, num_pages, state_name)

        # Split the list of races into batches
        race_batches = [state_races[i:i+batch_size] for i in range(0, len(state_races), batch_size)]
        
        for batch_idx, race_batch in enumerate(race_batches, start=1):
            # Convert race data to text format
            text_data = ''
            for idx, race in enumerate(race_batch, start=(batch_idx-1)*batch_size + 1):
                text_data += f'Race {idx}:\n'
                for key, value in race.items():
                    text_data += f'{key}: {value}\n'
                text_data += '\n'

            # Upload text data to S3 bucket
            file_name = f'{state_name}_race_information_batch{batch_idx}.txt'
            object_key = f'race-data/{state_name}/{file_name}'
            upload_text_data_to_s3(text_data, bucket_name, object_key)

def lambda_handler(event, context):
    main()

if __name__ == "__main__":
    lambda_handler(None, None)