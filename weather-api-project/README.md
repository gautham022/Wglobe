# Weather API Project
A RESTful Weather API built using **FastAPI** that provides real-time weather information and a 5-day weather forecast for cities around the world using the **OpenWeatherMap API**.
# Features
- Get current weather for any city
- Get a 5-day weather forecast (3-hour intervals)- 🌡️ Displays:
- Temperature
- Feels Like Temperature
- Humidity
- Wind Speed
- Weather Description
- Returns both the Country Name and Country Code
- Input validation to reject invalid city names (e.g., numeric inputs)
- Secure API key management using environment variables
- Interactive API documentation with Swagger UI

# Technologies Used
- Python
- FastAPI
- Uvicorn
- Requests
- OpenWeatherMap API
- Git & GitHub

# Project Structure
```
weather-api-project/
│
├── main.py
├── news.py
├── requirements.txt
├── .gitignore
└── README.md
```

# What I Learned
During this project I learned how to:
- Build REST APIs using FastAPI
- Create API endpoints
- Handle query parameters and input validation
- Work with external APIs
- Process JSON responses
- Secure API keys using environment variables
- Organize a Python project
- Use Git and GitHub for version control
- Deploy and run FastAPI applications using Uvicorn
- Understand the basics of Gunicorn and Nginx on Linux
  
# Installation

# 1. Clone the repository
```bash
git clone https://github.com/gautham022/weather-api-project.git
```
# 2. Move into the project folder
```bash
cd weather-api-project
```
# 3. Create a virtual environment
```bash
python -m venv venv
```
# 4. Activate the virtual environment
**Windows**
```bash
venv\Scripts\activate
```
**Linux / macOS**
```bash
source venv/bin/activate
```
# 5. Install dependencies
```bash
pip install -r requirements.txt
```
# 6. Create a `.env` file
```text
OPENWEATHER_API_KEY=your_api_key_here
```
Get your free API key from:
https://openweathermap.org/api
---
##  Run the Application
```bash
uvicorn main:app --reload
```
##  API Documentation
Once the server is running, open:
```
http://127.0.0.1:8000/docs
```
Swagger UI allows you to test all available API endpoints directly from your browser.
---
# Example Endpoints
# Current Weather
```
GET /weather?city=Chennai
```
# 5-Day Forecast
```
GET /forecast?city=Chennai
```
# Security
The API key is stored using environment variables and is **not committed** to GitHub. The `.env` file is ignored using `.gitignore` to keep sensitive information secure.
# Future Improvements
- Air Quality Index (AQI)
- Weather Alerts
- Multiple Language Support
- Unit Conversion (°C / °F)
- City Search Suggestions
- Caching for Faster Responses
# Author
**Gautham Balaji**

GitHub: https://github.com/gautham022
