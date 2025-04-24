import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
MASTODON_API_BASE_URL = os.getenv("MASTODON_API_BASE_URL", "https://mastodon.social")
MASTODON_ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN", "") # Replace with actual acces token used for Mastodon

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") # Replace with actual access token taken from IO.NET Intelligence
OPENAI_API_KEY_SENTIMENT = os.getenv("OPENAI_API_KEY_SENTIMENT", "") # Replace with actual access token taken from IO.NET Intelligence
LLM_API_BASE_URL = "https://api.intelligence.io.solutions/api/v1"
LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

# Server Configuration
HOST = "0.0.0.0"
PORT = 5002

# Set environment variables for libraries that need them
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_API_KEY_SENTIMENT"] = OPENAI_API_KEY_SENTIMENT
