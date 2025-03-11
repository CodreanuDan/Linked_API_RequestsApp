#***********************************************************************
# MODULE: graphical_interface
# SCOPE:  GUI interface for current project
# REV: 1.0
#
# Created by: Codreanu Dan

#***********************************************************************
# IMPORTS:
from datetime import datetime as dt
from api_handlers import PexelApiHdl as pexel    
from api_handlers import OpenMeteoHdl as openmeteo
from api_handlers import OpenStreetMapHdl as openmap
from api_handlers import OpenAiApiHdl as chatgpt
from api_handlers import GeminiApiHdl as gemini
from api_handlers import IpLocationApiHdl as ip_location
from api_handlers import OpenRouteServiceApiHdl as open_route
from tenacity import retry, stop_after_attempt
import streamlit as st
import pandas as pd
import json
import os



# ***********************************************************************
# CONTENT: Streamlit_GUI_HandleOpenMeteoData
# INFO: Aux class for project GUI, handles data from OpenMeteo API https://open-meteo.com/ 
class Streamlit_GUI_HandleOpenMeteoData():
    """
        :Class name: Streamlit_GUI_HandleOpenMeteoData
        :Descr:  Aux class for project GUI, handles data from OpenMeteo API https://open-meteo.com/ 
    """
    def __init__(self):
        self.w_json_file =  os.path.join(os.path.dirname(__file__), "data/weather_data.json")
        self.__html_file_path = os.path.join(os.path.dirname(__file__), "html/forecast.html")
        self.__style_css_path = os.path.join(os.path.dirname(__file__), "styles/weekly_forecast_style.css")
    
    def __load_weather_data(self, json_file):
        """ 
            Load weather data from JSON file 
                :param: filename -> weather data JSON file
                :type: str
        """
        try:
            with open(json_file, "r") as file:
                data = [json.loads(line) for line in file]
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"[❌][graphical_interface.py/Streamlit_GUI_HandleOpenMeteoData/load_weather_data] --> Error while loading data: {e}")
            print(f"[❌][graphical_interface.py/Streamlit_GUI_HandleOpenMeteoData/load_weather_data] --> Error while loading data: {e}")
            return None

    def display_weather_data(self):
        """ 
            Display weather data in Streamlit interface
            :param: df -> dataframe
        """
        df = self.__load_weather_data(self.w_json_file)
        if df is None or df.empty:
            st.warning("[❌] No weather data available!")
            return

        # Check relevant columns
        required_columns = ['date', 'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'uv_index', 'precipitation_probability']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.warning(f"[❌] Some required columns are missing from the data! Missing columns: {missing_columns}")
            return

        # Convert timestamp to standard unit, second from millisecond
        df["date"] = pd.to_datetime(df["date"] // 1000, unit='s')

        # Extract day from data
        df["day"] = df["date"].dt.date

        # Aggregate data for 1 day
        daily_summary = df.groupby("day").agg({
            "temperature_2m": "mean",
            "relative_humidity_2m": "mean",
            "wind_speed_10m": "mean",
            "uv_index": "mean",
            "precipitation_probability": "max"
        }).reset_index()

        # Verificăm dacă avem date pentru 168h/1 săptămână
        if len(daily_summary) > 7:
            daily_summary = daily_summary.tail(7)

        # Dictionary of weather conditions with corresponding emoji
        weather_icons = {
            0: "☀️",  # Clear
            1: "🌤️",  # Partly cloudy
            2: "☁️",  # Cloudy
            3: "🌧️",  # Rainy
            4: "❄️",  # Snow
            5: "🌬️",  # Windy
            6: "🌫️",  # Fog
            7: "🌩️",  # Thunderstorm
            8: "🌈",   # Rainbow
            9: "🌪️",  # Tornado
        }

        # Days of the week mapping
        day_of_week_map = {
            0: "Luni",
            1: "Marți",
            2: "Miercuri",
            3: "Joi",
            4: "Vineri",
            5: "Sâmbătă",
            6: "Duminică"
        }
        
        #**********************************************************************************************
        # Open style.css file
        with open(self.__style_css_path, "r") as f:
            css = f.read()
        # Apply custom CSS style
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

        #**********************************************************************************************
        # HTML 
        # Create container to wrap columns and make them expand horizontally
        st.markdown('<div class="weather-container">', unsafe_allow_html=True)
        # Create weekly forecast columns (horizontal alignment)
        cols = st.columns(len(daily_summary))  # Create as many columns as the number of days
        for i, col in enumerate(cols):
            with col:
                row = daily_summary.iloc[i]
                day_of_week = row['day'].weekday()
                # Get the corresponding day name 
                day_name = day_of_week_map.get(day_of_week, "N/A")
                precipitation_probability = row.get('precipitation_probability', 0)  
                if precipitation_probability > 50:
                    weather_icon = weather_icons[3]  # Rainy (🌧️)
                elif row['temperature_2m'] < 2 and precipitation_probability > 50:
                    weather_icon = weather_icons[4]  # Snow (❄️)
                elif row['precipitation_probability'] > 80:
                    weather_icon = weather_icons[7]  # Thunderstorm (🌩️)
                elif row['wind_speed_10m'] > 20:
                    weather_icon = weather_icons[5]  # Windy (🌬️)
                elif row['relative_humidity_2m'] > 80 and row['temperature_2m'] < 15:
                    weather_icon = weather_icons[6]  # Fog (🌫️)
                else:
                    weather_icon = weather_icons[1]  # Partly Cloudy (🌤️)
                
                #**********************************************************************************************
                # Open html file
                with open(self.__html_file_path, "r", encoding="utf-8") as f:
                    forecast_html = f.read()
                # Replace placeholders in the HTML with actual data
                forecast_html = forecast_html.replace("{day_name}", day_name)
                forecast_html = forecast_html.replace("{weather_icon}", weather_icon)
                forecast_html = forecast_html.replace("{date}", str(row['day']))
                forecast_html = forecast_html.replace("{temperature}", str(f"{row['temperature_2m']:.2f}°C"))
                forecast_html = forecast_html.replace("{humidity}", str(f"{row['relative_humidity_2m']:.2f}%"))
                forecast_html = forecast_html.replace("{wind_speed}", str(f"{row['wind_speed_10m']:.2f} km/h"))
                forecast_html = forecast_html.replace("{uv_index}", str(f"{row['uv_index']:.2f}"))
                # Display the weather information in a horizontal column
                st.markdown(f'<div class="weather-column">{forecast_html}</div>',unsafe_allow_html=True)
        # End container div
        st.markdown('</div>', unsafe_allow_html=True)
      
                
#***********************************************************************
# CONTENT: Streamlit_GUI_HandleOpenStreetMap
# INFO:Aux class for project GUI, handles data from OpenStreetMap API "https://nominatim.openstreetmap.org/search"
class Streamlit_GUI_HandleOpenStreetMap(pexel):
    """
        :Class name: Streamlit_GUI_HandleOpenStreetMap
        :Descr:  Aux class for project GUI, handles location data from JSON file
        :Inherits from: PexelApiHdl
    """
    def __init__(self):
        super().__init__()
        self.l_json_file = os.path.join(os.path.dirname(__file__), "data\location_data.json")
        self.__html_file_path = os.path.join(os.path.dirname(__file__), "html/location.html")
        self.__style_css_path = os.path.join(os.path.dirname(__file__), "styles/location_style.css")

    def __load_location_data(self, location_file):
        """ 
            Load location data from JSON file
                :param: location data json
        """
        try:
            with open(location_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data
        except Exception as e:
            st.error(f"[❌][graphical_interface.py/Streamlit_GUI_HandleOpenStreetMap/load_location_data] --> Error while loading location data: {e}")
            print(f"[❌][graphical_interface.py/Streamlit_GUI_HandleOpenStreetMap/load_location_data] --> Error while loading location data: {e}")
            return None

    def display_location_data(self):
        """  Display location data in Streamlit interface """
        #**********************************************************************************************
        location_data = self.__load_location_data(self.l_json_file)
        if not location_data:
            st.warning("[❌][graphical_interface.py/Streamlit_GUI_HandleOpenStreetMap/display_location_section] --> No location data available!")
            print("[❌][graphical_interface.py/Streamlit_GUI_HandleOpenStreetMap/display_location_section] --> No location data available!")
            return
        #**********************************************************************************************
        # Box Ttile and descr
        location_title = "Location Information"
        location_info = "This section displays the location data based on OpenStreetMap."
        # Extract values from the loaded location data (replace these with actual JSON keys)
        location_name = location_data.get('name', 'N/A')
        country_code = location_data.get('country_code', 'N/A')
        latitude = location_data.get('latitude', 'N/A')
        longitude = location_data.get('longitude', 'N/A')
        # Extract region from the location name (assumed to be the second part after splitting by comma)
        region = location_name.split(',')[0].strip() if len(location_name.split(',')) > 1 else 'N/A'  # Take the second part
        settlement = location_name.split(',')[0].strip() if len(location_name.split(',')) > 1 else 'N/A'  # Take the first part
        # Get the image URL for the location from Pexels API
        location_image_url = self.get_location_image(region)
        # Links for wikiepdia si google maps
        location_wikipedia_url = f"https://ro.wikipedia.org/wiki/{settlement.replace(' ', '_')}"
        location_google_maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        #**********************************************************************************************
        # Open style.css file
        with open(self.__style_css_path, "r") as f:
            css = f.read()
        # Apply custom CSS style
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        
        #**********************************************************************************************
        # Open html file
        with open(self.__html_file_path, "r", encoding="utf-8") as f:
            location_html = f.read()
        # Replace placeholders in the HTML file with actual data
        location_html = location_html.replace("{location_title}", location_title)
        location_html = location_html.replace("{location_info}", location_info)
        location_html = location_html.replace("{location_name}", location_name)
        location_html = location_html.replace("{country_code}", country_code)
        location_html = location_html.replace("{latitude}", str(latitude))
        location_html = location_html.replace("{longitude}", str(longitude))
        location_html = location_html.replace("{location_wikipedia_url}",str(location_wikipedia_url))
        location_html = location_html.replace("{location_google_maps_url}",str(location_google_maps_url))                           
        # If the image URL exists, replace the placeholder with the actual image URL
        if location_image_url:
            location_html = location_html.replace("{location_image}", location_image_url)
        else:
            # Set a default image if none found
            location_html = location_html.replace("{location_image}", "img/default_placeholder.jpg")  
        # Inject HTML into Streamlit
        st.markdown(f"""{location_html}""", unsafe_allow_html=True)
        
  
#***********************************************************************
# CONTENT: Streamlit_GUI_HandleGeminiAI
# INFO: Aux class for project GUI, handles data from GeminiAI API "https://aistudio.google.com"
class Streamlit_GUI_HandleGeminiAI():
    """
        :Class name: Streamlit_GUI_HandleGeminiAI
        :Descr: Aux class for project GUI, handles data from GeminiAI API "https://aistudio.google.com"
    """
    def __init__(self):
        self.__html_file_path = os.path.join(os.path.dirname(__file__), "html/gemini_response.html")
        self.__style_css_path = os.path.join(os.path.dirname(__file__), "styles/gemini_style.css")
    
    def display_gemini_recomendations(self, gemini_response:str):
        """  Display gemini recomendations in Streamlit interface """
        #**********************************************************************************************
        if not gemini_response:
            st.warning("[❌][graphical_interface.py/Streamlit_GUI_HandleGemeniAI/display_gemini_recomendations] --> No data available!")
            print("[❌][graphical_interface.py/Streamlit_GUI_HandleGemeniAI/display_gemini_recomendations] --> No data available!")
            return
        #**********************************************************************************************
        # Box Ttile and descr
        title = "🤖 Trip Recomendation"
        info = "This section displays the trip recomendation from our AI assistant."
        #**********************************************************************************************
        # Open style.css file
        with open(self.__style_css_path, "r") as f:
            css = f.read()
        # Apply custom CSS style
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        #**********************************************************************************************
        # Open html file
        with open(self.__html_file_path, "r", encoding="utf-8") as f:
            location_html = f.read()
        # Replace placeholders in the HTML file with actual data
        location_html = location_html.replace("{title}", title)
        location_html = location_html.replace("{info}", info)
        location_html = location_html.replace("{gemini_response}", gemini_response)
        # Inject HTML into Streamlit
        st.markdown(f"""{location_html}""", unsafe_allow_html=True)
        
            
#***********************************************************************
# CONTENT: Streamlit_GUI_HandleOpenStreetMap
# INFO: Class for project GUI, made with Streamlit, main GUI Handler
class Streamlit_GUI(Streamlit_GUI_HandleOpenMeteoData,
                    Streamlit_GUI_HandleOpenStreetMap,
                    Streamlit_GUI_HandleGeminiAI,
                    openmap,
                    openmeteo,
                    chatgpt,
                    gemini,
                    ip_location,
                    open_route):
    """ 
        :Class name: Streamlit_GUI
        :Descr: Class for project GUI, made with Streamlit, main GUI Handler
        :Inherits from: Streamlit_GUI_HandleOpenMeteoData,
                        Streamlit_GUI_HandleOpenStreetMap,
                        OpenMeteoHdl,
                        OpenStreetMapHdl,
                        OpenAiApiHdl,
                        GeminiApiHdl,
                        IpLocationApiHdl,
                        OpenRouteServiceApiHdl
    """
    def __init__(self):
        super().__init__()
        Streamlit_GUI_HandleOpenStreetMap.__init__(self)
        Streamlit_GUI_HandleOpenMeteoData.__init__(self)
        Streamlit_GUI_HandleGeminiAI.__init__(self)
        chatgpt.__init__(self)
        gemini.__init__(self)
        ip_location.__init__(self)
        open_route.__init__(self)
        self.__exit_button_css_path = os.path.join(os.path.dirname(__file__), "styles/exit_button_style.css")
        self.__search_bar_css_path = os.path.join(os.path.dirname(__file__), "styles/search_bar_style.css")
        self.__open_ai_data = os.path.join(os.path.dirname(__file__), "data/open_ai_data.json")
        #**********************************************************
        if "old_location" not in st.session_state:
            st.session_state.old_location = ""
        if "change_made" not in st.session_state:
            st.session_state.change_made = False
        #**********************************************************
        self.__run_gui()

    def __run_gui(self):
        """
            Graphical interface handler
        """
        st.title('🏕 Tourism Info 🛫')
        #*********************************************************************************************
        # Location Info Box
        self.display_location_data()
        #*********************************************************************************************
        # Search bar
        new_location, person_type = self.__get_location_and_person(self.__search_bar_css_path)
        #*********************************************************************************************
        # Weather forecast
        self.display_weather_data()
        #*********************************************************************************************
        # Refresh logic
        self.__check_change(new_location, person_type)
        #*********************************************************************************************
        # OpenAITip / GeminiAiTip
        tip = " "
        if st.session_state.change_made and person_type != "":
            tip = self.get_response_from_gemini() 
            print(tip)
            st.session_state.change_made = False
        self.display_gemini_recomendations(tip)
        #*********************************************************************************************
        # Trip info 
        # Get the user's IP location
        self.__get_trip_data()
        #*********************************************************************************************
        # Exit button 
        self.__exit_button(self.__exit_button_css_path)
          
    def __get_trip_data(self):
        """ Get the trip route (using the start location from get_route.json and destination from location_data.json) """
        self.__ip_location = self.get_location_from_ip()
        self.__html_trip = os.path.join(os.path.dirname(__file__), 'html/trip_info.html')
        self.__css_trip = os.path.join(os.path.dirname(__file__), 'styles/trip_info_style.css')
        
        if self.__ip_location != (None, None):
            self.__trip_info = self.get_route()
            self.__distance = self.__trip_info[0]
            self.__time = self.__trip_info[1]

            if self.__distance is not None and self.__time is not None:
                if os.path.exists(self.__html_trip):
                    with open(self.__html_trip, 'r', encoding='utf-8') as f:
                        trip_info_html = f.read()
                    
                    trip_info_html = trip_info_html.replace("{distance}", f"{self.__distance:.2f}")
                    trip_info_html = trip_info_html.replace("{duration}", f"{(self.__time / 60):.2f}")
                    
                    if os.path.exists(self.__css_trip):
                        st.markdown(f"<style>{open(self.__css_trip).read()}</style>", unsafe_allow_html=True)
                    
                    st.markdown(trip_info_html, unsafe_allow_html=True)
                else:
                    st.error("HTML file not found!")
            else:
                st.markdown("<div class='trip-info-container'><div class='trip-info-title'>No route data!</div></div>", unsafe_allow_html=True)
        else:
            print("[❌][graphical_interface.py/Streamlit_GUI/__get_trip_data] --> Could not retrieve IP location.")
            st.error("Could not retrieve IP location.")

    def __exit_button(self, file):
        """
            Closes application
        """
        with open(file, "r") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        if st.button("EXIT"):
            if os.path.exists(self.__open_ai_data):
                os.remove(self.__open_ai_data)
                print(f"[🗑️][graphical_interface.py/Streamlit_GUI/__exit_button] --> File {self.__open_ai_data} deleted before loading new data.")
            os._exit(0)
            st.stop()

    def __get_location_and_person(self, file) -> tuple[str, str]:
        """
            Handles search bar, extracts location and person type
            :return: (location, person_type)
        """
        with open(file, "r") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

        loc_input = st.text_input(
            "Enter a location and person type:", "", key="location_input",
            help="Format: Location, Person Type (ex: Paris, adventure lover)",
            placeholder="Type a location and type of person to generate an AI tip for your trip 😊",
            max_chars=100
        )

        if loc_input.strip():
            parts = loc_input.split(",", 1)  # Împărțim după prima virgulă
            location = parts[0].strip()
            person_type = parts[1].strip() if len(parts) > 1 else "Unknown person type"

            openmap(location).get_location()
            openmeteo(168).fetch_weather_data()
            st.session_state.change_made = True
            self.__save_person_type_to_json(person_type)  # Salvăm tipul de persoană

            return location, person_type

        return "", ""

    def __save_person_type_to_json(self, person_type: str):
        """
            Save the person type to a JSON file
        """
        person_data = {"person_type": person_type}

        # Verificăm dacă fișierul există și citim datele existente
        if os.path.exists(self.__open_ai_data):
            with open(self.__open_ai_data, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]  # Asigurăm că datele sunt într-o listă
        else:
            existing_data = []  # Dacă fișierul nu există, începem o listă goală

        # Adăugăm noul tip de persoană
        existing_data.append(person_data)

        # Salvăm datele actualizate în fișier
        try:
            with open(self.__open_ai_data, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4)
            print(f"[✅][graphical_interface.py/Streamlit_GUI/__save_location_to_json] --> Person type saved in: {self.__open_ai_data}")
        except Exception as e:
            print(f"[❌][graphical_interface.py/Streamlit_GUI/__save_location_to_json] --> Error saving person type data: {e}")

    @retry(stop=stop_after_attempt(3))
    def __check_change(self, new_location: str, person_type: str):
        """ 
            Check if location input changes and trigger refresh
                :param new_location: The entered location
                :param person_type: The extracted person type
        """
        if new_location != st.session_state.old_location and st.session_state.change_made:
            st.session_state.old_location = new_location
            print(f"OLD_LOCATION: {st.session_state.old_location} | NEW_LOCATION: {new_location}")
            st.session_state.change_made = False
            st.rerun()


#***********************************************************************
# DBG_AREA:
if __name__ == "__main__":
    pass
