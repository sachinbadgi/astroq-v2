import os
import json
import torch
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from astroq.lk_prediction.agent.tool_registry import TOOL_TREES

class IntentRouter:
    """
    Semantic Tool RAG Router.
    Uses sentence-transformers to map user queries to specific Tool Trees.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.tree_names = list(TOOL_TREES.keys())
        self.tree_descriptions = [TOOL_TREES[name]["description"] for name in self.tree_names]
        
        # Pre-compute embeddings for tree descriptions
        self.tree_embeddings = self.model.encode(self.tree_descriptions)

    def get_intent_and_tools(self, query: str) -> Dict[str, Any]:
        """
        Finds the most relevant Tool Tree and returns its name and tools.
        """
        query_embedding = self.model.encode([query])
        similarities = cosine_similarity(query_embedding, self.tree_embeddings)[0]
        
        best_idx = np.argmax(similarities)
        best_tree_name = self.tree_names[best_idx]
        
        return {
            "intent": best_tree_name,
            "tools": TOOL_TREES[best_tree_name]["tools"]
        }

    def get_tools_for_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Backwards compatibility: Just returns the tools.
        """
        return self.get_intent_and_tools(query)["tools"]

if __name__ == "__main__":
    # Quick CLI test
    router = IntentRouter()
    q = "What is my destiny in my career during my 40s?"
    result = router.get_intent_and_tools(q)
    print(f"Intent for '{q}': {result['intent']}")
    print(f"Tools: {[t['name'] for t in result['tools']]}")
