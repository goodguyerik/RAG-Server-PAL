import numpy as np
import time
import requests

def get_page(conn, doc_id): 
    cursor = conn.cursor()
    cursor.execute(f"SELECT pages.number, pages.text FROM pages WHERE id = {doc_id};")
    temp = cursor.fetchall()
    return list(zip([doc_id] * len(temp), [x[0] for x in temp])), [x[1] for x in temp]

def get_retrieved_pages(conn, page_ids, score, k):
    cursor = conn.cursor()
    top = np.argsort(-score)[:k]
    res = [(page_ids[x][0], page_ids[x][1], score[x]) for x in top]
    unique_ids = list({x[0] for x in res})  # get unique doc_ids
    ids_str = ', '.join(map(str, unique_ids))
    cursor.execute(f"SELECT * FROM map WHERE id IN ({ids_str});")
    return res, cursor.fetchall()

def retrieve_cross_encoder(conn, doc_ids, query, i, k, inference_url):
    start_time = time.time()
    page_content = []
    page_ids = []
    for doc_id in doc_ids[:i]:
        temp = get_page(conn, doc_id)
        page_ids.extend(temp[0])
        page_content.extend(temp[1])
    combs = [(query, content) for content in page_content]

    payload = {
        'combs': combs,
        'page_content': page_content
    }

    resp = requests.post(inference_url, json=payload, timeout=(10, 300))
    resp.raise_for_status()
    print(resp)
    outputs = resp.json()["scores"]
    outputs = np.array(outputs)
    end_time = time.time()
    return get_retrieved_pages(conn, page_ids, outputs, k), end_time - start_time