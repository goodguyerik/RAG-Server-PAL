import csv
import io

def log_data(conn, query, bm25, cross_encoder, runtime, llm=''):
    cursor = conn.cursor()
    command = """INSERT INTO log (query, bm25, cross_encoder, runtime, answer) 
                 VALUES (%s, %s, %s, %s, %s) RETURNING id"""
    cursor.execute(command, (query, bm25, cross_encoder, runtime, llm))
    # Return the new log id as an integer (not a tuple)
    new_id = cursor.fetchone()[0]
    conn.commit()
    return new_id

def log_feedback(conn, id, feedback_text='', pos_ce=[], neg_ce=[], pos_bm25=[], neg_bm25=[]):
    cursor = conn.cursor()
    command = """UPDATE log 
                 SET feedback_text = %s, positive_bm25 = %s, negative_bm25 = %s, 
                     positive_ce = %s, negative_ce = %s 
                 WHERE id = %s"""
    # Ensure the log id is an integer
    cursor.execute(command, (feedback_text, pos_bm25, neg_bm25, pos_ce, neg_ce, int(id)))
    conn.commit()
    return

def get_log_csv(conn):
    """Return the log table as CSV-formatted string."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM log;")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(rows)
    return output.getvalue()

def get_map_csv(conn):
    """Return the map table as CSV-formatted string."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM map;")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(rows)
    return output.getvalue()