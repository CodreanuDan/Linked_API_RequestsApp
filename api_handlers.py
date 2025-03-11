#***********************************************************************
# MODULE: api_handlers
# SCOPE:  Request data from APIs
# REV: 1.0
#
# Created by: Codreanu Dan

#***********************************************************************
# IMPORTS:
import openmeteo_requests
from openai import OpenAI
import requests_cache
import pandas as pd
import os
from retry_requests import retry
import requests
import json
import google.generativeai as genai
from settings_manager import SettingsManager as config

os.environ["CURL_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""

#***********************************************************************
# CONTENT: OpenMeteoHdl
# INFO:    Request data from meteo service: https://open-meteo.com/
class OpenMeteoHdl():
    """
        :Class name: OpenMeteoHdl
        :Descr: Request data from meteo service: https://open-meteo.com/
    """
    def __init__(self, forecast_hours:int):
        """
        Initialize the OpenMeteoHdl instance with necessary parameters.
            :param latitude: Latitude of the location for weather data.
            :param longitude: Longitude of the location for weather data.
            :param forecast_hours: Number of hours to forecast, default is 24.
        """
        # Setup the Open-Meteo API client with cache and retry on error
        self.cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
        self.retry_session = retry(self.cache_session, retries = 5, backoff_factor = 0.2)
        self.openmeteo = openmeteo_requests.Client(session = self.retry_session)
        self.__filename= os.path.join(os.path.dirname(__file__),"data/weather_data.json")
        self.dbg_file_weather =  self.__filename
        self.__location_data= os.path.join(os.path.dirname(__file__), "data/location_data.json")
        self.__open_ai_data = os.path.join(os.path.dirname(__file__), "data/open_ai_data.json")
        
        
        self.latitude = float(self.__get_location_data(location_data= self.__location_data)[0])
        self.longitude = float(self.__get_location_data(location_data= self.__location_data)[1])
        self.forecast_hours = forecast_hours
        
        # Weather parameters
        self.url = config.get_api_url("open-meteo")
        self.params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m",
                       "apparent_temperature", "precipitation_probability", "precipitation",
                       "rain", "showers", "snowfall", "snow_depth",
                       "visibility", "wind_speed_10m", "uv_index",
                       "uv_index_clear_sky", "is_day"],
            "timezone": "auto",
            # Number of hours to forecast
            "forecast_hours": self.forecast_hours  
        }
        
        self.__weekly_forecast = 0
    
    def fetch_weather_data(self):
        """
            Fetch the weather data from the Open-Meteo API.
                :return: DataFrame with hourly weather data
        """
        try:
            responses = self.openmeteo.weather_api(self.url, params=self.params)
            if not responses:
                print("[❌][api_handlers.py/OpenMeteoHdl/fetch_weather_data] --> No weather data returned!")
                return None
            
            # Process first response (you can loop through multiple if needed)
            response = responses[0]
            
            # print(f"[🌥️][api_handlers.py/OpenMeteoHdl/fetch_weather_data] --> Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
            # print(f"[🌥️][api_handlers.py/OpenMeteoHdl/fetch_weather_data] --> Elevation: {response.Elevation()} m asl")
            # print(f"[🌥️][api_handlers.py/OpenMeteoHdl/fetch_weather_data] --> Timezone: {response.Timezone()} {response.TimezoneAbbreviation()}")
            # print(f"[🌥️][api_handlers.py/OpenMeteoHdl/fetch_weather_data] --> Timezone difference to GMT+0: {response.UtcOffsetSeconds()} s")
            
            # Process hourly data
            hourly = response.Hourly()
            hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
            hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
            hourly_dew_point_2m = hourly.Variables(2).ValuesAsNumpy()
            hourly_apparent_temperature = hourly.Variables(3).ValuesAsNumpy()
            hourly_precipitation_probability = hourly.Variables(4).ValuesAsNumpy()
            hourly_precipitation = hourly.Variables(5).ValuesAsNumpy()
            hourly_rain = hourly.Variables(6).ValuesAsNumpy()
            hourly_showers = hourly.Variables(7).ValuesAsNumpy()
            hourly_snowfall = hourly.Variables(8).ValuesAsNumpy()
            hourly_snow_depth = hourly.Variables(9).ValuesAsNumpy()
            hourly_visibility = hourly.Variables(10).ValuesAsNumpy()
            hourly_wind_speed_10m = hourly.Variables(11).ValuesAsNumpy()
            hourly_uv_index = hourly.Variables(12).ValuesAsNumpy()
            hourly_uv_index_clear_sky = hourly.Variables(13).ValuesAsNumpy()
            hourly_is_day = hourly.Variables(14).ValuesAsNumpy()
            
            # Fore openAI data
            average_precipitation = hourly_precipitation.mean()
            self.__weekly_forecast = average_precipitation

            # Prepare data into a DataFrame
            hourly_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                ),
                "temperature_2m": hourly_temperature_2m,
                "relative_humidity_2m": hourly_relative_humidity_2m,
                "dew_point_2m": hourly_dew_point_2m,
                "apparent_temperature": hourly_apparent_temperature,
                "precipitation_probability": hourly_precipitation_probability,
                "precipitation": hourly_precipitation,
                "rain": hourly_rain,
                "showers": hourly_showers,
                "snowfall": hourly_snowfall,
                "snow_depth": hourly_snow_depth,
                "visibility": hourly_visibility,
                "wind_speed_10m": hourly_wind_speed_10m,
                "uv_index": hourly_uv_index,
                "uv_index_clear_sky": hourly_uv_index_clear_sky,
                "is_day": hourly_is_day
            }

            # Create a pandas DataFrame from the hourly data
            hourly_dataframe = pd.DataFrame(data=hourly_data)
            
            # Save to JSON
            weather_data = self.__filename
            openai_data = self.__open_ai_data
            self.__save_to_json(dataframe=hourly_dataframe, filename= weather_data, openai_file=openai_data)
            
            return hourly_dataframe
        
        except Exception as e:
            print(f"[❌][api_handlers.py/OpenMeteoHdl/fetch_weather_data] --> Error while fetching weather data: {e}")
            return None
    
    def __save_to_json(self, dataframe: pd.DataFrame, filename: str, openai_file: str):
        """
            Save the DataFrame to a JSON file.
                :param dataframe: The pandas DataFrame containing weather data.
                :param filename: The name of the file to save the data to.
                :param openai_file: The name of the file to save the data to open ai data.
        """
        try:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"[🗑️][api_handlers.py/OpenMeteoHdl/save_to_json] --> File {filename} deleted before loading new data.")
            dataframe.to_json(filename, orient='records', lines=True)
            print(f"[✅][api_handlers.py/OpenMeteoHdl/save_to_json] --> Wather data saved in: {filename}")
        except Exception as e:
            print(f"[❌][api_handlers.py/OpenMeteoHdl/save_to_json] --> Saving data in JSON file not possible! Error: {e}")
        
        location_data = {
                            "weather": f"Weekly forecast average precipitation: {self.__weekly_forecast:.2f} mm"
                        }
        
        #**********************************************************************************************************
        # SAVE DATA FOR OPEN AI 
        try:
            location_data = {
                "weather": f"Weekly forecast average precipitation: {self.__weekly_forecast:.2f} mm"
            }

            if os.path.exists(openai_file):
                with open(openai_file, "r", encoding="utf-8") as f:
                    existing_location_data = json.load(f)
                    if not isinstance(existing_location_data, list):
                        existing_location_data = [existing_location_data]  
            else:
                existing_location_data = []  

            existing_location_data.append(location_data)

            with open(openai_file, "w", encoding="utf-8") as f:
                json.dump(existing_location_data, f, indent=4)

            print(f"[✅][api_handlers.py/OpenMeteoHdl/save_to_json] --> Weather data saved in: {openai_file}")
        except Exception as e:
            print(f"[❌][api_handlers.py/OpenMeteoHdl/save_to_json] --> Error saving data in OpenAI file: {e}")


    def __get_location_data(self,location_data: str)-> list:
        """
            Load location coord, latitude and longitude from JSON file
                :param location_data: The JSON containing location data.
                :return: list -> [0]:latitude  [1]:longitude
        """
        coord = []
        try:
            if os.path.exists(location_data):
                with open(location_data, 'r', encoding= 'utf-8') as file:
                    data = json.load(file)
                    coord.append(data['latitude'])
                    coord.append(data['longitude'])
                    print(print(f"[✅][api_handlers.py/OpenStreetMapHdl/__get_location_data] -->  lat:{coord[0]} lon: {coord[1]}"))
                    return coord
            else:
                print(print(f"[❌][api_handlers.py/OpenStreetMapHdl/__get_location_data] -->  {location_data} doesn`t exist: {e}"))
        except Exception as e:
            print(f"[❌][api_handlers.py/OpenStreetMapHdl/__get_location_data] -->  Error getting location data: {e}")
        return [0.0, 0.0]
                
                  
#***********************************************************************
# CONTENT: OpenStreetMapHdl
# INFO:    Request data from location api service: "https://nominatim.openstreetmap.org/search"
class OpenStreetMapHdl():
    """
        :Class name: OpenStreetMapHdl
        :Descr: Request data from location api service: "https://nominatim.openstreetmap.org/search"
    """
    def __init__(self, location_name: str):
        """
            Initialize the handler for querying OpenStreetMap.
                :param location_name: Name of the location to be queried.
        """
        
        self.base_url = config.get_api_url("openstreetmap")
        self.__filename = os.path.join(os.path.dirname(__file__),"data/location_data.json")
        self.__open_ai_data = os.path.join(os.path.dirname(__file__), "data/open_ai_data.json")
        self.dbg_file_location = self.__filename
        self.location_name = location_name
        
    def get_location(self):
        """
        Fetches location data based on the name using the OpenStreetMap API.
        
        :return: dict containing location data or error message.
        """
        params = {
            "q": self.location_name,
            "format": "json",
            "limit": 1,  # Limit to the first result
            "addressdetails": 1,  # Include address details
            "extratags": 1,  # Include extra tags
        }

        headers = {
            "User-Agent": "YourAppNames/1.0 (contact@yourdomain.com)"  # Replace with your app's name and contact email
        }

        response = requests.get(self.base_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data:
                result = data[0]

                location_data = {
                    "name": result.get("display_name", "Unknown"),
                    "latitude": result.get("lat", "N/A"),
                    "longitude": result.get("lon", "N/A"),
                    "type": result.get("type", "N/A"),
                    "country_code": result.get("address", {}).get("country_code", "N/A"),
                    "postcode": result.get("address", {}).get("postcode", "N/A"),
                    "bounding_box": result.get("boundingbox", []),
                    "osm_id": result.get("osm_id", "N/A"),
                    "population": result.get("extratags", {}).get("population", "N/A")
                }

                # Save the data to a JSON file
                locationData_file = self.__filename
                openAI_data = self.__open_ai_data
                self.__save_to_json(location_data, filename= locationData_file, file_openai=openAI_data)

                return location_data
            else:
                print(f"[❌][api_handlers.py/OpenStreetMapHdl/get_location] -->  Location not found!")
                return {"[❌][api_handlers.py/OpenStreetMapHdl/get_location]": "Location not found!"}
        else:
            print(f"[❌][api_handlers.py/OpenStreetMapHdl/get_location] --> Request failed with status code {response.status_code}")
            return {"[❌][api_handlers.py/OpenStreetMapHdl/get_location]": f"Request failed with status code {response.status_code}"}

    def __save_to_json(self, location_data:dict, filename, file_openai):
        """
        Save the fetched location data to a JSON file.
        
        :param location_data: The location data to save.
        :param filename: File where we save data from location api
        :param file_openai: File where we save data for openai trip tip
        """
        try:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"[🗑️][api_handlers.py/OpenStreetMapHdl/__save_to_json] --> File {filename} deleted before loading new data.")

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(location_data, f, indent=4)

            print(f"[✅][api_handlers.py/OpenStreetMapHdl/__save_to_json] --> Location data saved in: {filename}")
        except Exception as e:
            print(f"[❌][api_handlers.py/OpenStreetMapHdl/__save_to_json] -->  Error saving location data: {e}")
            
        #**********************************************************************************************************
        # SAVE DATA FOR OPEN AI 
        try:
            location_only_openai = {"location": location_data.get("name", "")}

            if os.path.exists(file_openai):
                with open(file_openai, "r", encoding="utf-8") as f:
                    existing_location_data = json.load(f)
                    if not isinstance(existing_location_data, list):
                        existing_location_data = [existing_location_data] 
            else:
                existing_location_data = [] 

            existing_location_data.append(location_only_openai)

            with open(file_openai, "w", encoding="utf-8") as f:
                json.dump(existing_location_data, f, indent=4)

            print(f"[✅][api_handlers.py/OpenStreetMapHdl/__save_to_json] --> Location data saved in: {file_openai}")
        except Exception as e:
            print(f"[❌][api_handlers.py/OpenStreetMapHdl/__save_to_json] --> Error saving location data: {e}")
     

#***********************************************************************
# CONTENT: PexelApiHdl
# INFO:    Request image for location api service: "https://api.pexels.com/v1/search"
class PexelApiHdl():
    """
        :Class name: PexelApiHdl
        :Descr: Request image for location api service: "https://api.pexels.com/v1/search"
    """
    def __init__(self):
        self.url = config.get_api_url("pexels")
        self.PEXELS_API_KEY = config.get_api_key("PEXELS_API_KEY")
        
    def get_location_image(self,location_name: str) -> str:
        """
            Get image URL for the respective location from Pexels API
                :param: location_name
                :return: image_url|str
        """
        headers = {"Authorization": self.PEXELS_API_KEY}
        params = {"query": location_name, "per_page": 1}
        response = requests.get(self.url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("photos"):
                return data["photos"][0]["src"]["original"]
        return None  
  
  
#***********************************************************************
# CONTENT: OpenAiApiHdl
# INFO:    Request trip tip from OpenAiAPI: https://platform.openai.com
class OpenAiApiHdl():
    """
        :Class name: OpenAiApiHdl
        :Descr: Request trip tip from OpenAiAPI: https://platform.openai.com
    """
    def __init__(self):
        self.__open_ai_data = os.path.join(os.path.dirname(__file__), "data/open_ai_data.json")
        self.__api_key = config.get_api_key("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.__api_key)
        
    def __read_last_trip_data(self) -> dict:
        """
            Reads the last trip data from JSON and extracts location, weather, and person type.
            :return: Dict containing 'location', 'weather', and 'person_type'
        """
        if not os.path.exists(self.__open_ai_data):
            return {"location": "Unknown", "weather": "Unknown", "person_type": "Unknown"}

        with open(self.__open_ai_data, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        location = next((item["location"] for item in reversed(data) if "location" in item), "Unknown")
        weather = next((item["weather"] for item in reversed(data) if "weather" in item), "Unknown")
        person_type = next((item["person_type"] for item in reversed(data) if "person_type" in item), "Unknown")

        return {
            "location": location,
            "weather": weather,
            "person_type": person_type
        }

    def get_response_from_open_ai(self) -> str:
        trip_data = self.__read_last_trip_data()

        prompt = (
            f"Recomandă activități pentru o persoană {trip_data['person_type']} în {trip_data['location']}, "
            f"ținând cont că vremea este: {trip_data['weather']}."
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful travel assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            tip = response.choices[0].message.content.strip()
            return tip
        except Exception as e:
            print(f"[❌][api_handlers.py/OpenAiApiHdl/get_response_from_open_ai] OpenAI API Error: {e}")
            return "Nu am putut genera o recomandare momentan."


#***********************************************************************
# CONTENT: GeminiApiHdl
# INFO:    Request trip tip from GeminiApiHdl: https://aistudio.google.com
class GeminiApiHdl():
    """
        :Class name: GeminiApiHdl
        :Descr: Request trip tip from Google Gemini API https://aistudio.google.com
    """
    def __init__(self):
        self.__gemini_data = os.path.join(os.path.dirname(__file__), "data/open_ai_data.json")
        self.__api_key = config.get_api_key("GEMINI_API_KEY")
        genai.configure(api_key=self.__api_key)
        # self.model = genai.GenerativeModel("gemini-1.5-pro")
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite-001")
        # models = genai.list_models()
        # for model in models:
        #     print(model.name)

    def __read_last_trip_data(self) -> dict:
        """
            Reads the last trip data from JSON and extracts location, weather, and person type.
            :return: Dict containing 'location', 'weather', and 'person_type'
        """
        if not os.path.exists(self.__gemini_data):
            return {"location": "Unknown", "weather": "Unknown", "person_type": "Unknown"}

        with open(self.__gemini_data, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        location = next((item["location"] for item in reversed(data) if "location" in item), "Unknown")
        weather = next((item["weather"] for item in reversed(data) if "weather" in item), "Unknown")
        person_type = next((item["person_type"] for item in reversed(data) if "person_type" in item), "Unknown")

        return {
            "location": location,
            "weather": weather,
            "person_type": person_type
        }

    def get_response_from_gemini(self) -> str:
        trip_data = self.__read_last_trip_data()

        prompt = (
            f"Recomandă activități pentru o persoană {trip_data['person_type']} în {trip_data['location']}, "
            f"ținând cont că vremea este: {trip_data['weather']}, într-un răspuns de doar 4-5 propoziții."
        )

        try:
            response = self.model.generate_content(prompt)    
            return response.text.strip() if response else "Nu am putut genera o recomandare momentan."
        except Exception as e:
            print(f"[❌][api_handlers.py/GeminiApiHdl/get_response_from_gemini] -->  Gemini API Error: {e}")
            return "Nu am putut genera o recomandare momentan."
    
        
#***********************************************************************
# CONTENT: OpenRouteServiceApiHdl
# INFO:    Request trip info from OpenRouteServiceApi: "https://api.openrouteservice.org/v2/directions/driving-car"
class OpenRouteServiceApiHdl():
    """
    :Class name: OpenRouteServiceApiHdl
    :Descr: Request trip information from OpenRouteServiceApi: https://api.openrouteservice.org/v2/directions/driving-car
    """
    def __init__(self):
        self.__api_key = config.get_api_key("OPRTSER_API_KEY")
        self.__url = config.get_api_url("openrouteservice")
        self.__destination = os.path.join(os.path.dirname(__file__), "data/location_data.json")
        self.__start = os.path.join(os.path.dirname(__file__), "data/get_route.json")
    
    def get_route(self) -> tuple:
        """
        Get trip distance and duration between two locations by reading from get_route.json (start) and location_data.json (destination)
        
        :return: Tuple with distance in kilometers and duration in minutes
        """
        try:
            # Load the start location data from get_route.json (user's current location)
            with open(self.__start, 'r', encoding="utf-8") as file:
                start_data = json.load(file)
            start_coords = (float(start_data["latitude"]), float(start_data["longitude"]))  # User's current location (IP location)
            print(f"Start coordinates: {start_coords}")
            
            # Load the destination location data from location_data.json
            with open(self.__destination, 'r') as file:
                destination_data = json.load(file)
            end_coords = (float(destination_data["latitude"]), float(destination_data["longitude"]))  # Destination from location_data.json
            print(f"End coordinates: {end_coords}")

            params = {
                "api_key": self.__api_key,
                "start": f"{start_coords[1]},{start_coords[0]}",  # Longitude, Latitude
                "end": f"{end_coords[1]},{end_coords[0]}"         # Longitude, Latitude
            }
            
            headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            }

            # Request to OpenRouteService API to get directions
            response = requests.get(self.__url, params=params, headers= headers)
            response.raise_for_status()  # Will raise an exception for invalid responses (4xx and 5xx)

            data = response.json()
            
            # Extract distance and duration from the response
            duration = data['features'][0]['properties']['segments'][0]['duration'] / 60  # Duration in minutes
            distance = data['features'][0]['properties']['segments'][0]['distance'] / 1000  # Distance in km
            
            # Print the trip details
            print(f"Trip duration: {duration:.2f} minutes")
            print(f"Trip distance: {distance:.2f} km")
            
            return distance, duration
        except requests.exceptions.RequestException as e:
            print(f"[❌][api_handlers.py/OpenRouteServiceApiHdl/get_route] --> Request error: {e}")
            return None, None
        except KeyError as e:
            print(f"[❌][api_handlers.py/OpenRouteServiceApiHdl/get_route] --> Missing expected data: {e}")
            return None, None


#***********************************************************************
# CONTENT: IpLocationApiHdl
# INFO:    Class for obtaining the user's location based on their IP address using the IPinfo API: "https://ipinfo.io/json"
class IpLocationApiHdl():
    """
    :Class name: IpLocationApiHdl
    :Descr: Class for obtaining the user's location based on their IP address using the IPinfo API: https://ipinfo.io/json
    """
    def __init__(self):
        self.__url = config.get_api_url("location-ip")
        self.__start = os.path.join(os.path.dirname(__file__), "data/get_route.json")

    def get_location_from_ip(self) -> tuple:
        """
        Get the user's location based on their IP address and save it to get_route.json
        
        :return: A tuple containing latitude and longitude
        """
        try:
            response = requests.get(self.__url)
            response.raise_for_status()  # Will raise an exception for invalid responses

            data = response.json()
            location = data.get("loc", "").split(",")
            if len(location) == 2:
                lat, lon = map(float, location)
                print(f"User IP location: {lat}, {lon}")
                
                # Save IP location data to get_route.json (user's start location)
                location_data = {
                    "latitude": str(lat),
                    "longitude": str(lon)
                }
                with open(self.__start, 'w') as file:
                    json.dump(location_data, file, indent=4)

                return lat, lon
            else:
                print(f"[❌][api_handlers.py/IpLocationApiHdl/get_location] --> Location not found in the API response.")
                return None, None
        except requests.exceptions.RequestException as e:
            print(f"[❌][api_handlers.py/IpLocationApiHdl/get_location] --> Error getting IP location: {e}")
            return None, None

#***********************************************************************
# DBG_AREA:
if __name__ == "__main__":
    # # latitude = 52.52
    # # longitude = 13.41
    # forecast_hours = 168  # You can set this to the desired number of hours
    
    # # Instantiate the OpenMeteoHdl class and fetch weather data
    location_handler = OpenStreetMapHdl("Brasov,Romania")
    # meteo_handler = OpenMeteoHdl(forecast_hours)
    # location_data = location_handler.get_location()
    # weather_data = meteo_handler.fetch_weather_data()
    # if weather_data is not None:
    #     print(f"[🪲][DEBUG][<api_handlers.py>] Response from open-meteo.com is saved in json file: {meteo_handler.dbg_file_weather}")
    # if location_data is not None:
    #     print(f"[🪲][DEBUG][<api_handlers.py>] Response from OpenStreetMap is saved in json file: {location_handler.dbg_file_location}")
    ip_location_handler = IpLocationApiHdl()
    route_handler = OpenRouteServiceApiHdl()

    # Get the user's IP location
    ip_location = ip_location_handler.get_location_from_ip()

    # Get the trip route (using the start location from get_route.json and destination from location_data.json)
    if ip_location != (None, None):
        route_handler.get_route()
    else:
        print("Could not retrieve IP location.")