import os
import httpx
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
BASE_URL = "http://www.omdbapi.com/"

def map_language_to_iso(omdb_lang_string):
    if not omdb_lang_string: return 'en'
    lang = omdb_lang_string.split(',')[0].strip().lower()
    mapping = {
        'korean': 'ko', 'japanese': 'ja', 'chinese': 'zh', 
        'mandarin': 'zh', 'telugu': 'te', 'tamil': 'ta', 
        'malayalam': 'ml', 'hindi': 'hi'
    }
    return mapping.get(lang, 'en')

def proxy_image(raw_url):
    if not raw_url or raw_url == "N/A": 
        return ""
        
    clean_url = raw_url.replace("https://", "").replace("http://", "")
    
    return f"https://images.weserv.nl/?url={clean_url}&w=600&fit=cover"

async def fetch_movie_data(imdb_id: str):
    async with httpx.AsyncClient() as client:
        # The URL now uses the protected OMDB_API_KEY variable
        response = await client.get(f"{BASE_URL}?i={imdb_id}&apikey={OMDB_API_KEY}&plot=short")
        data = response.json()

        if data.get("Response") == "False": return None

        iso_lang = map_language_to_iso(data.get("Language", ""))
        is_asian_or_indian = iso_lang in ['ko', 'ja', 'zh', 'te', 'ta', 'ml']
        
        return {
            "id": data.get("imdbID"),
            "title": data.get("Title"),
            "synopsis": data.get("Plot"),
            "genre": data.get("Genre", ""),
            "image": proxy_image(data.get("Poster")),
            "original_lang": iso_lang,
            "hindi_dub_available": is_asian_or_indian 
        }
