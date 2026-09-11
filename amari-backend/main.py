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
    
    # 1. Search OMDb for our keywords
    for query in LIVE_SEARCH_QUERIES:
        ids = await search_live_movies(query)
        live_ids.update(ids)
        
    # 2. Limit to 30 so we don't hit OMDb rate limits, and fetch full details
    tasks = [fetch_movie_data(mid) for mid in list(live_ids)[:30]]
    results = await asyncio.gather(*tasks)
    
    # 3. Feed the live data into the session and ML Engine
    session_state["unseen_ids"] = []
    for movie in results:
        if movie:
            session_state["catalog_data"][movie["id"]] = movie
            session_state["unseen_ids"].append(movie["id"])
            
    ml_engine.build_matrix(session_state["catalog_data"])
    print(f"Backend ready with {len(session_state['catalog_data'])} live movies!")

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
