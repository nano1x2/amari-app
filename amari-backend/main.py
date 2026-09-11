from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from omdb_service import fetch_movie_data
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

SEED_IDS = [
    "tt10850932", 
    "tt8178634", 
    "tt6751668", 
    "tt11828492", 
    "tt27496661", 
    "tt0245429",  
    "tt0364569",  

session_state = {
    "liked_ids": [],
    "unseen_ids": SEED_IDS.copy(),
    "catalog_data": {}
}

@app.on_event("startup")
async def startup_event():
    print("Pre-fetching catalog & building ML matrix...")
    tasks = [fetch_movie_data(mid) for mid in SEED_IDS]
    results = await asyncio.gather(*tasks)
    
    for movie in results:
        if movie:
            session_state["catalog_data"][movie["id"]] = movie
            
    ml_engine.build_matrix(session_state["catalog_data"])
    print("Backend ready!")

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
