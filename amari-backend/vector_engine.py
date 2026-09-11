import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MLRecommendationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.matrix = None
        self.movie_ids = []
        self.is_fitted = False

    def build_matrix(self, catalog_data: dict):
        self.movie_ids = list(catalog_data.keys())
        corpus = [
            f"{m.get('title','')} {m.get('synopsis','')} {m.get('genre','')} {m.get('original_lang','')}"
            for m in catalog_data.values()
        ]
        
        if corpus:
            self.matrix = self.vectorizer.fit_transform(corpus)
            self.is_fitted = True

    def get_recommendations(self, liked_ids: list, unseen_ids: list, top_k: int = 3):
        if not self.is_fitted or not unseen_ids:
            return unseen_ids[:top_k]
            
        unseen_indices = [self.movie_ids.index(mid) for mid in unseen_ids if mid in self.movie_ids]
        liked_indices = [self.movie_ids.index(mid) for mid in liked_ids if mid in self.movie_ids]
        
        if not liked_indices:
            return [self.movie_ids[i] for i in unseen_indices[:top_k]]
            
        # Calculate average vector of all liked movies
        liked_vectors = self.matrix[liked_indices]
        user_vector = np.asarray(liked_vectors.mean(axis=0))
        
        unseen_vectors = self.matrix[unseen_indices]
        similarities = cosine_similarity(user_vector, unseen_vectors).flatten()
        
        sorted_unseen = np.argsort(similarities)[::-1]
        return [unseen_ids[i] for i in sorted_unseen[:top_k]]
