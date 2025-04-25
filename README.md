# Social Media Monitoring Tool

A project web application for analyzing sentiment trends from Mastodon social media posts with advanced data visualization.

## Example of the project

![Image](https://github.com/user-attachments/assets/63c0478f-7eec-47d5-9bcb-58ff7d58f781)

### Features

-	Hashtag/Keyword Summary: Search for and analyze posts by hashtag or keyword
-	Sentiment Analysis: Analyze the overall sentiment of posts (positive, neutral, negative)
-	Sentiment Over Time Analysis: Track how sentiment changes over time
-	Related Keywords: Discover related keywords and topics

## Architecture
#### Frontend (ASP.NET Core Razor Pages)
-	Modern responsive UI built with Bootstrap
-	Interactive charts using Chart.js
-	jQuery for DOM manipulation and AJAX requests
#### Backend (ASP.NET Core + Python)
-	ASP.NET Core API controller for handling client requests

	Python API for:
-	Mastodon data retrieval
-	Natural Language Processing (NLP)
-	Sentiment analysis using LLM models
-	Temporal trend analysis
-	Key phrase extraction

## Setup And Configuration

### Prerequisites
-	.NET 9.0 SDK
-	Python 3.9+

### Environment Variables

To run the project, you need to implement these variables in the [config.py](PythonApi/config.py)

`OPENAI_API_KEY`

`OPENAI_API_KEY_SENTIMENT`

`MASTODON_ACCESS_TOKEN`


## Running The Application

Clone the project

```bash
git clone https://github.com/yourusername/social-media-monitoring.git
cd social-media-monitoring
```

Set up and start the Python API

```bash
cd PythonApi
pip install -r requirements.txt
python app.py
```

Start the ASP.NET Core application

```bash
cd SocialMediaMonitoring
dotnet run

```

## Docker Support

The application includes Docker support for easy deployment:

Don't forget to change [AnalysisController.cs](SocialMediaMonitoring/Controllers/AnalysisController.cs) and [appsettings.json](SocialMediaMonitoring/appsettings.json) as mentioned in comments.

```bash
docker-compose up
```
