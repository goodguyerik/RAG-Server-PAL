import nltk
import psycopg2
nltk.data.path.append('/root/nltk_data')

conn = None 

# Uncomment these if you need to download NLTK data.
# nltk.download('stopwords')
# nltk.download('punkt')

map_table = """CREATE TABLE IF NOT EXISTS map (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE
                );"""

text_table = """CREATE TABLE IF NOT EXISTS texts (
                    id SERIAL PRIMARY KEY,
                    original_text TEXT,
                    processed_text TEXT[],
                    pages INT[],
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(id, timestamp),
                    FOREIGN KEY(id) REFERENCES map(id)
                );"""

pages_table = """CREATE TABLE IF NOT EXISTS pages (
                    id INT,
                    number INT,
                    text TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    PRIMARY KEY(id, number, timestamp),
                    FOREIGN KEY(id) REFERENCES texts(id)
                );"""

log_table = """CREATE TABLE IF NOT EXISTS log (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    bm25 INT[],
                    cross_encoder INT[][],
                    answer TEXT,
                    feedback_text TEXT,
                    positive_bm25 INT[],
                    negative_bm25 INT[],
                    positive_ce INT[],
                    negative_ce INT[],
                    runtime TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );"""

# New synonym tables for managing synonyms dynamically.
synonym_groups_table = """CREATE TABLE IF NOT EXISTS synonym_groups (
                            id SERIAL PRIMARY KEY
                        );"""

synonyms_table = """CREATE TABLE IF NOT EXISTS synonyms (
                        id SERIAL PRIMARY KEY,
                        group_id INTEGER REFERENCES synonym_groups(id) ON DELETE CASCADE,
                        word TEXT NOT NULL
                    );"""

def get_connection(service_name):
    global conn
    try:
        if conn:
            return conn
        else:
            conn = psycopg2.connect(
                database="RetrievalSystem",
                user="postgres",
                host=f"db_{service_name}",
                #host='localhost',
                password="root",
                port=5432
            )
            print("Successfully connected to the database.")
            return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise

def check_and_create_tables(conn):
    with conn.cursor() as cursor:
        cursor.execute(map_table)
        cursor.execute(text_table)
        cursor.execute(pages_table)
        cursor.execute(log_table)
        cursor.execute(synonym_groups_table)
        cursor.execute(synonyms_table)
        conn.commit()

def initialize_database(service_name):
    conn = get_connection(service_name)
    check_and_create_tables(conn)
    return conn
