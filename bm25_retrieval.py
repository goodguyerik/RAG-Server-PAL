from preprocessing import preprocess_text
from rank_bm25 import BM25Okapi
import numpy as np

def initialize_bm25(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT texts.processed_text, texts.id FROM texts;")
    temp = cursor.fetchall()
    if len(temp) == 0:
        # No documents available: return None and empty list.
        return None, []
    corpus = [toks[0] for toks in temp]
    doc_ids = [toks[1] for toks in temp]
    return BM25Okapi(corpus), doc_ids

def retrieve_bm25(bm25, query):
    if bm25 is None:
        return []  # No documents to score
    return bm25.get_scores(preprocess_text(query))

def get_retrieved_doc_ids(doc_ids, score, k):
    score = np.array(score)
    if score is None or score.size == 0:
        return []
    top = np.argsort(-score)[:k]
    return [doc_ids[x] for x in top]

def get_doc_names(conn, doc_ids):
    cursor = conn.cursor()
    ids_str = ', '.join(map(str, doc_ids))
    cursor.execute(f"SELECT name FROM map WHERE id IN ({ids_str});")
    return cursor.fetchall()