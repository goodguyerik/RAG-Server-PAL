import os
import re
import glob
import shutil
from PyPDF2 import PdfReader
from nltk.stem import SnowballStemmer
from nltk import word_tokenize
from nltk.corpus import stopwords

stemmer = SnowballStemmer('german')
stopwords = set(stopwords.words('german'))

map_insert = """INSERT INTO map (name) VALUES (%s) 
                ON CONFLICT (name)
                DO NOTHING
                RETURNING id;"""

text_insert = """INSERT INTO texts (id, original_text, processed_text, pages) 
                 VALUES (%s, %s, %s, %s)
                 RETURNING timestamp;"""

page_insert = """INSERT INTO pages 
                 VALUES (%s, %s, %s, %s);"""

delete_pages_query = "DELETE FROM pages WHERE id = (SELECT id FROM map WHERE name = %s);"
delete_texts_query = "DELETE FROM texts WHERE id = (SELECT id FROM map WHERE name = %s);"
delete_map_query = "DELETE FROM map WHERE name = %s;"

def get_pages(pdf):
    res = []
    reader = PdfReader(pdf)
    for page_num, page in enumerate(reader.pages, start=1):
        content = page.extract_text()
        if not content:
            content = ''
        content = clean_string(content)
        res.append({'number': str(page_num), 'content': content})
    file_name = os.path.basename(pdf)
    return res, file_name

def clean_string(s):
    return s.replace('\0', '') if s else s

def get_text(pages):
    text = ''.join(' ' + page['content'] for page in pages)
    return text

def store_texts(conn, pages, file_name, text, preprocessed_text):
    cursor = conn.cursor()
    cursor.execute(map_insert, (file_name,))
    result = cursor.fetchone()
    if result is None:  # If PDF was already parsed, then do nothing
        conn.commit()
        return
    pdf_id = result[0] if isinstance(result, tuple) else result
    cursor.execute(text_insert, (pdf_id, text, preprocessed_text, [int(page['number']) for page in pages]))
    timestamp = cursor.fetchone()[0]
    for page in pages:
        cursor.execute(page_insert, (pdf_id, page['number'], page['content'], timestamp))
    conn.commit()

def preprocess_text(text):
    toks = word_tokenize(text)
    toks = [t for t in toks if t.lower() not in stopwords]
    toks = [stemmer.stem(t) for t in toks]
    return toks

def parse_pdf(conn, pdf):
    pages, file_name = get_pages(pdf)
    text = get_text(pages)
    preprocessed_text = preprocess_text(text)
    store_texts(conn, pages, file_name, text, preprocessed_text)

def add_pdf(conn, pdf):
    parse_pdf(conn, pdf)
    add_to_folder(pdf)

def delete_pdf(conn, pdf):
    file_name = os.path.basename(pdf)
    cursor = conn.cursor()
    cursor.execute(delete_pages_query, (file_name,))
    cursor.execute(delete_texts_query, (file_name,))
    cursor.execute(delete_map_query, (file_name,))
    conn.commit()
    
    destination_dir = './data'
    file_path = os.path.join(destination_dir, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    base_name, _ = os.path.splitext(file_name)
    video_file_name = base_name + ".mp4"
    video_path = os.path.join("videos", video_file_name)
    if os.path.exists(video_path):
        os.remove(video_path)

def add_to_folder(pdf):
    destination_dir = './data'
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    destination_path = os.path.join(destination_dir, os.path.basename(pdf))
    # Only move if the source and destination paths differ.
    if os.path.abspath(pdf) != os.path.abspath(destination_path):
        shutil.move(pdf, destination_path)

def get_db_pdf_names(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM map ORDER BY name ASC;")
    result = cursor.fetchall()
    return [row[0] for row in result]
