from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from omdb_service import fetch_movie_data, search_live_movies
from vector_engine import MLRecommendationEngine

app = FastAPI(title="Amari API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ml_engine = MLRecommendationEngine()

session_state = {
    "liked_ids": [],
    "unseen_ids": [],
    "catalog_data": {}
}

# The engine will scrape live movies matching these terms every time it boots
LIVE_SEARCH_QUERIES = ["jujutsu", "kuroko", "mf ghost", "seoul", "tokyo"]

@app.on_event("startup")
async def startup_event():
    print("Scraping live data from OMDb...")
    live_ids = set()
    
    # 1. Search OMDb for keywords
    for query in LIVE_SEARCH_QUERIES:
        ids = await search_live_movies(query)
        live_ids.update(ids)
        
    # 2. Fetch sequentially to avoid OMDb DDoS blocks
    session_state["unseen_ids"] = []
    
    # Limit to 20 to ensure fast startup times
    for mid in list(live_ids)[:20]:
        movie = await fetch_movie_data(mid)
        # Only keep titles with actual plots so the ML math doesn't break
        if movie and movie.get("synopsis") and movie["synopsis"] != "N/A":
            session_state["catalog_data"][movie["id"]] = movie
            session_state["unseen_ids"].append(movie["id"])
            
    # 3. Build ML Matrix safely
    if len(session_state["catalog_data"]) > 1:
        ml_engine.build_matrix(session_state["catalog_data"])
        print(f"Backend ready with {len(session_state['catalog_data'])} titles!")
    else:
        print("Warning: Not enough data to build ML matrix.")

class SwipeAction(BaseModel):
    imdb_id: str
    direction: str 

@app.post("/api/v1/swipe")
async def register_swipe(action: SwipeAction):
    if action.imdb_id in session_state["unseen_ids"]:
        session_state["unseen_ids"].remove(action.imdb_id)
        
    if action.direction == "right":
        session_state["liked_ids"].append(action.imdb_id)
        
    return {"status": "success"}

@app.get("/api/v1/feed")
async def get_feed_batch():
    best_match_ids = ml_engine.get_recommendations(
        liked_ids=session_state["liked_ids"],
        unseen_ids=session_state["unseen_ids"],
        top_k=3
    )
    return [session_state["catalog_data"][mid] for mid in best_match_ids]

@app.get("/health")
async def health_check():
    """Keeps the Render free tier awake when pinged by UptimeRobot."""
    return {"status": "Amari backend is awake and ready"}
