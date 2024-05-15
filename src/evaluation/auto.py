from sentence_transformers import SentenceTransformer
import torch
from rouge import Rouge


sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
cossim = torch.nn.CosineSimilarity(dim=0, eps=1e-6)

def score_sbert_similarity(text1, text2):
    embeddings = sbert_model.encode([text1, text2], convert_to_tensor=True)
    return cossim(embeddings[0], embeddings[1]).item()

# get the similarity score between two texts using ROUGE score
def score_rouge_similarity(text1, text2):
    rouge = Rouge()
    scores = rouge.get_scores(text1, text2)
    return scores[0]['rouge-l']['f']