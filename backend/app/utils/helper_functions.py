from langchain_core.prompts import PromptTemplate
from datetime import datetime
from langchain_core.documents import Document
from typing import List

PROMPT_TEMPLATE = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
The current date and time is: {current_datetime}

You are an elite endurance athlete coach who specializes in recommending races to people based
on their fitness and preferences. Recommend races and include corrresponding signup/info links.
Format your response so it is easy to read in a chat interface.

{context}

Question: {query}

Helpful Answer:"""

def build_prompt() -> PromptTemplate:
  """
  Build a prompt template for the application.

  Args:
  - context (str, optional): The context to include in the prompt. Defaults to an empty string.
  - query (str, optional): The query to include in the prompt. Defaults to an empty string.

  Returns:
  - PromptTemplate: The constructed prompt template.
  """
  prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)
  return prompt

def get_recommendation_prompt(location, recent_stats, ytd_stats) -> str:

  current_datetime = get_current_datetime()

  # recent stats
  recent_meters = recent_stats.get('distance')
  recent_distance = convert_meters_to_miles(recent_meters)
  recent_moving_time = recent_stats.get('moving_time')
  recent_run_count = recent_stats.get('count')
  recent_elevation_gain = round(convert_meters_to_feet(recent_stats.get('elevation_gain')), 2)
  recent_average_pace = calculate_average_pace(recent_meters, recent_moving_time)

  # ytd stats
  ytd_meters = ytd_stats.get('distance')
  ytd_distance = convert_meters_to_miles(ytd_meters)
  ytd_moving_time = ytd_stats.get('moving_time')
  ytd_run_count = ytd_stats.get('count')
  ytd_elevation_gain = round(convert_meters_to_feet(ytd_stats.get('elevation_gain')), 2)
  ytd_average_pace = calculate_average_pace(ytd_meters, ytd_moving_time)

  prompt = f"""
  
  Here is the fitness data of a runner.
  
  The runner is located in: {location}
  The current date and time is: {current_datetime}

  **Recent Activity stats (Last 4 weeks):**
  - Total distance ran: {recent_distance} miles
  - Total runs: {recent_run_count}
  - Total elevation gain: {recent_elevation_gain} ft
  - Average pace: {recent_average_pace}

  **Year-To-Date Activity stats:**
  - Total distance ran: {ytd_distance} miles
  - Total runs: {ytd_run_count}
  - Total elevation gain: {ytd_elevation_gain} ft
  - Average pace: {ytd_average_pace}

  What upcoming local races would you recommend this runner participate in?
  """

  print(prompt)
  return prompt


def pretty_print_docs(docs: (List[Document])) -> None:
  """
  Helper function for printing Documents in a readable format.

  Args:
  - docs (List[Document]): A list of Document objects to print.
  """
  print(
      f"\n{'-' * 100}\n".join(
          [f"Document {i+1}:\n\n" + d.page_content for i, d in enumerate(docs)]
      )
  )

def format_docs(docs: (List[Document])) -> str:
  """
  Format Documents to be used as context in a prompt.
  
  Args:
  - docs (List[Document]): A list of Document objects to format.

  Returns:
  - str: A formatted string representation of the Documents.
  """
  return "\n\n".join(doc.page_content for doc in docs)

def pretty_print_context(contexts: List[str]) -> None:
  """
  Helper function for printing contexts in a readable format.

  Args:
  - contexts (List[str]): A list of contexts to print.
  """
  print(
      f"\n{'-' * 100}\n".join(
          [f"Document {i+1}:\n\n" + context for i, context in enumerate(contexts)]
      )
  )

def format_contexts(contexts: (List[str])) -> str:
  """
  Format contexts to be used as context in a prompt.
  
  Args:
  - contexts (List[str]): A list of contexts to format.

  Returns:
  - str: A formatted string representation of the contexts.
  """
  return "\n\n".join(contexts)

def get_current_datetime() -> str:
  """
  Get the current date and time formatted as a string.

  Returns:
  - str: The current date and time formatted as "Day, Month Day, Year Hour:Minute AM/PM".
  """
  current_datetime = datetime.now()
  formatted_datetime = current_datetime.strftime("%A, %B %d, %Y %I:%M %p")
  return formatted_datetime

def convert_meters_to_miles(meters: float) -> float:
  """
  Convert a distance from meters to miles, rounded to two decimal places.

  Args:
  - meters (float): The distance in meters that needs to be converted to miles.

  Returns:
  - float: The distance in miles, rounded to two decimal places.

  Example:
  >>> meters_run = 5000.0
  >>> miles_run = meters_to_miles(meters_run)
  >>> print(f"{meters_run} meters is approximately {miles_run} miles.")
  5000.0 meters is approximately 3.11 miles.
  """
  # There are 1609.344 meters in a mile
  miles = meters / 1609.344
  # Limit the result to two decimal places
  miles_rounded = round(miles, 2)
  return miles_rounded

def convert_meters_to_feet(meters: float) -> float:
  """
  Convert a distance from meters to feet.

  Args:
  - meters (float): The distance in meters that needs to be converted to feet.

  Returns:
  - float: The distance in feet.

  Example:
  >>> meters = 10.0
  >>> feet = meters_to_feet(meters)
  >>> print(f"{meters} meters is approximately {feet} feet.")
  10.0 meters is approximately 32.81 feet.

  Notes:
  - 1 meter is equivalent to approximately 3.28084 feet.
  """
  # Conversion factor from meters to feet
  meters_to_feet_conversion_factor = 3.28084
  # Convert meters to feet
  feet = meters * meters_to_feet_conversion_factor
  return feet


def calculate_average_pace(distance_meters: float, elapsed_time_seconds: float) -> str:
  """
  Calculate the average pace per mile given the elapsed time and distance covered.

  Args:
  elapsed_time_seconds (float): The elapsed time in seconds.
  distance_meters (float): The distance covered in meters.

  Returns:
  str: The average pace per mile in the format 'MM:SS' (minutes:seconds).

  Example:
  >>> elapsed_time_seconds = 1800.0
  >>> distance_meters = 1609.344 * 3  # Assuming 3 miles
  >>> pace = pace_per_mile(elapsed_time_seconds, distance_meters)
  >>> print(f"The average pace per mile is: {pace}")
  The average pace per mile is: 10:00

  Notes:
  - 1 mile is equivalent to 1609.344 meters.
  """
  # Convert elapsed time to minutes
  elapsed_time_minutes = elapsed_time_seconds / 60
  # Calculate total miles covered
  miles_covered = convert_meters_to_miles(distance_meters)
  # Calculate pace per mile in minutes
  pace_per_mile_minutes = elapsed_time_minutes / miles_covered
  # Convert pace to MM:SS format
  pace_minutes = int(pace_per_mile_minutes)
  pace_seconds = int((pace_per_mile_minutes - pace_minutes) * 60)
  pace_formatted = f"{pace_minutes:02d}:{pace_seconds:02d}/mile"
  return pace_formatted