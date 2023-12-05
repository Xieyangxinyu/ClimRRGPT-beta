import pandas as pd
import pickle

# Load data
df = pd.read_csv('./data/wildfire_literature.csv')
df['combined_text'] = df['title'] + ' ' + df['abstract'] + ' ' + df['field']

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


# Initialize FAISS index
index = faiss.read_index("./data/wildfire_index.bin")

# Load a sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2', device='mps')

def search(query, k=5):
    query_vector = model.encode([query]).astype(np.float32)
    _, indices = index.search(query_vector, k)
    return df.iloc[indices[0]].reset_index(drop=True)
    
def get_author(authors_str):
    import ast
    authors = ast.literal_eval(authors_str)
    if len(authors) > 3:
        # Use et al. for more than three authors
        formatted = f"{authors[0]['first']} {authors[0]['last']} et al."
    else:
        # Join all authors' names
        formatted = ', '.join(f"{author['first']} {author['last']}" for author in authors)
    return formatted

def literature_search(query):
    results = search(query)
    return "\n\n".join([f"{i + 1}. Title: {result['title']}. Authors: {get_author(result['authors'])}. Year: {result['year']}.\n Abstract: {result['abstract']}." for i, result in results.iterrows()])

if __name__ == "__main__":
    
    query = "What is the relationship between climate change and wildfire?"
    results = search(query)
    # print titles and abstracts of results as 1 string