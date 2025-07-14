import pickle
import psycopg2

insert = """INSERT INTO bm25
            VALUES (1, %s, %s)
            ON CONFLICT (id) DO NOTHING;"""

update = """UPDATE bm25
            SET bm25_object = %s,
                doc_ids = %s
            WHERE id = 1;"""

#mode == insert: for initialization purposes 
#mode == update: during further runtime
def modify_bm25_dump(conn, bm25_object, doc_ids, mode):
    cursor = conn.cursor()
    bm25_serialized = pickle.dumps(bm25_object)

    if mode == 'insert': 
        cursor.execute(insert, (psycopg2.Binary(bm25_serialized), doc_ids))
    elif mode == 'update':
        cursor.execute(update, (psycopg2.Binary(bm25_serialized), doc_ids))
    conn.commit()

def fetch_latest_bm25(conn):
    cursor = conn.cursor()
    cursor.execute(f'SELECT bm25_object, doc_ids FROM bm25 WHERE id = 1;')
    row = cursor.fetchone()

    if row is None:
        return None, None

    bm25_object = pickle.loads(row[0])
    doc_ids = row[1]
    
    return bm25_object, doc_ids