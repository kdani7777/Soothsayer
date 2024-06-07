import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

DUMMY_MAP = {
    'CA': 'california', 'FL': 'florida'
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

# Main function
def main():
    base_url = os.getenv('SCRAPING_URL')
    num_pages = 5  # Number of pages to scrape (adjust as needed)

    # Iterate over states
    for state_abbr, state_name in DUMMY_MAP.items():
        state_base_url = f'{base_url}/{state_abbr.lower()}/upcoming'
        state_races = scrape_all_races(state_base_url, num_pages, state_name)

        # Write information to file
        file_name = f'../../data/race_data/{state_name}_race_information.txt'
        with open(file_name, 'w') as file:
            for idx, race in enumerate(state_races, start=1):
                file.write(f'Race {idx}:\n')
                for key, value in race.items():
                    file.write(f'{key}: {value}\n')
                file.write('\n')

if __name__ == "__main__":
    main()
