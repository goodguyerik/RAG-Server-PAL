import os
import re
import time
import locale
import numpy as np
import io
import zipfile
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, Response
from markupsafe import Markup
from flask import current_app as app
from PIL import Image
from functools import wraps  # New import for decorators

# Import your custom modules
from init import initialize_database
from updatePDFs import add_pdf, delete_pdf, get_db_pdf_names
from cross_encoder import retrieve_cross_encoder 
import query_expansion
import log
import bm25_retrieval
import handle_bm25_dump

app = Flask(__name__)

# ------------------ Login Decorators ------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Bitte zuerst einloggen!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Admin-Zugang erforderlich!")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------ Load Dynamic Configuration ------------------
try:
    import config
    app.secret_key = config.SECRET_KEY
except ImportError:
    # Fallback defaults if config.py isn't present.
    class Config:
        COMPANY_NAME = "DefaultCompany"
        LOGO_PATH = "logos/DefaultCompany"
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "admin"
        SERVICE_NAME = "db"
        INFERENCE_URL = 'http://localhost:8001/score'
    config = Config()

# Make dynamic configuration available in all templates.
@app.context_processor
def inject_config():
    return dict(
        company_name=config.COMPANY_NAME,
        logo_path=config.LOGO_PATH,
        inference_url=config.INFERENCE_URL
    )

# ------------------ Global Initialization ------------------
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
conn = initialize_database(config.SERVICE_NAME)
query_expansion.update_synonym_list(conn)

# Initially build the BM25 index.
bm25, doc_ids = bm25_retrieval.initialize_bm25(conn)
handle_bm25_dump.modify_bm25_dump(conn, bm25, doc_ids, 'insert')
keycaps = [
    '1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟',
    '11','12','13','14','15','16','17','18','19','20',
    '21','22','23','24','25','26','27','28','29','30',
    '31','32','33','34','35','36','37','38','39','40',
    '41','42','43','44','45','46','47','48','49','50'
]

# ------------------ Helper Function ------------------
def score_to_color(score, min_score, max_score):
    if max_score - min_score == 0:
        t = 1.0
    else:
        t = (score - min_score) / (max_score - min_score)
    red = int((1 - t) * 255)
    green = int(t * 255)
    return f"#{red:02x}{green:02x}00"

# ------------------ Routes ------------------
@app.route('/')
def index():
    return redirect(url_for('search'))

@app.route('/barrierefreiheit')
def accessibility():
    return render_template('barrierefreiheit.html')

@app.route('/impressum')
def legal_notice():
    return render_template('Impressum.html')

@app.route('/datenschutz')
def data_prot():
    return render_template('Datenschutzerklaerung.html')

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        original_query = request.form.get('query', '')
        original_query = re.sub(r"[()?\[\]{}<>]", "", original_query)
        query = query_expansion.expand_query(original_query)

        global bm25, doc_ids

        pid = os.getpid()
        t0 = time.perf_counter()
        bm25, doc_ids = handle_bm25_dump.fetch_latest_bm25(conn)
        t1 = time.perf_counter()

        if len(doc_ids) == 0:
            flash("Keine Dokumente vorhanden. Bitte fügen Sie zuerst PDFs hinzu!")
            return render_template('search.html', query=original_query)
	
        t2 = time.perf_counter()
        scores = bm25_retrieval.retrieve_bm25(bm25, query)
        t3 = time.perf_counter()

        res = bm25_retrieval.get_retrieved_doc_ids(doc_ids, scores, 10)
        if len(res) == 0:
            flash("Keine Treffer gefunden. Bitte versuchen Sie eine andere Suchanfrage!")
            return render_template('search.html', query=original_query)
	
        t4 = time.perf_counter()
        temp, runtime = retrieve_cross_encoder(conn, res, query, 10, 10, config.INFERENCE_URL)
        #temp, runtime = retrieve_cross_encoder(conn, res, query, 10, 10, 'http://localhost:8001/score')
        t5 = time.perf_counter()

        rank = temp[0]
        names = temp[1]
        doc_dict = dict(names)
        merged_list = [
            (doc_id, doc_dict[doc_id], page, score)
            for doc_id, page, score in rank if doc_id in doc_dict
        ]

        if merged_list:
            all_scores = [score for (_, _, _, score) in merged_list]
            min_score = min(all_scores)
            max_score = max(all_scores)
            merged_list = [
                (doc_id, doc_dict[doc_id], page, score, score_to_color(score, min_score, max_score))
                for doc_id, _, page, score in merged_list
            ]

        updated_list = []
        for doc_id, name, page, score, color in merged_list:
            base_name, _ = os.path.splitext(name)
            video_filename = base_name + ".mp4"
            video_path = os.path.join("videos", video_filename)
            if os.path.exists(video_path):
                file_type = "video"
                display_name = video_filename
            else:
                file_type = "pdf"
                display_name = name
            updated_list.append((doc_id, display_name, page, score, color, file_type))


        results_with_times = []
        cursor = conn.cursor()
        timestamp_pattern = re.compile(r"\[(\d{2}):(\d{2}):(\d{2})\]")
        for doc_id, display_name, page, score, color, file_type in updated_list:
            ts_seconds = None
            if file_type == "video":
                cursor.execute(
                    "SELECT text FROM pages WHERE id = %s AND number = %s",
                    (doc_id, page)
                )
                row = cursor.fetchone()
                if row:
                    text = row[0]
                    m = timestamp_pattern.search(text)
                    if m:
                        h, m1, s = map(int, m.groups())
                        ts_seconds = h*3600 + m1*60 + s
            results_with_times.append(
                (doc_id, display_name, page, score, color, file_type, ts_seconds)
            )

        results = list(enumerate(results_with_times))

        t6 = time.perf_counter()
        print(f"[pid={pid}] bm25Init     : {t1-t0:.3f}s", flush=True)
        print(f"[pid={pid}] bm25     : {t3-t2:.3f}s", flush=True)
        print(f"[pid={pid}] crossEncoder     : {t5-t4:.3f}s", flush=True)
        print(f"[pid={pid}] otherStuff     : {t6-t5:.3f}s", flush=True)

        log_id = log.log_data(conn, query, res, [[doc_id, page] for doc_id, page, score in rank], runtime)
        session['log_id'] = log_id
        session['topk'] = len(updated_list)
        
        return render_template(
            'search.html',
            query=original_query,
            results=results,
            log_id=log_id,
            keycaps=keycaps
        )
    else:
        return render_template('search.html')

@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    log_id = request.form.get('log_id')
    topk = int(request.form.get('topk', 0))
    comment = request.form.get('comment', '')
    thumbs_up_vector = []
    thumbs_down_vector = []

    for i in range(topk):
        feedback_val = request.form.get(f'feedback_{i}')
        if feedback_val is None:
            thumbs_up_vector.append(None)
            thumbs_down_vector.append(None)
        elif feedback_val == 'up':
            thumbs_up_vector.append(1)
            thumbs_down_vector.append(0)
        elif feedback_val == 'down':
            thumbs_up_vector.append(0)
            thumbs_down_vector.append(1)
    
    log.log_feedback(
        conn=conn,
        id=log_id,
        feedback_text=comment,
        pos_ce=thumbs_up_vector,
        neg_ce=thumbs_down_vector,
    )
    flash("Feedback erfolgreich übermittelt!")
    return redirect(url_for('search'))

@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        if 'files' not in request.files:
            flash("Keine Datei ausgewählt!")
            return redirect(request.url)
        files = request.files.getlist('files')
        pdf_count = 0
        video_count = 0
        temp_dir = "temp_upload"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        video_dir = "videos"
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)
        for file in files:
            if file:
                filename = file.filename
                if filename.lower().endswith('.pdf'):
                    temp_file_path = os.path.join(temp_dir, filename)
                    file.save(temp_file_path)
                    add_pdf(conn, temp_file_path)
                    pdf_count += 1
                elif filename.lower().endswith('.mp4'):
                    video_file_path = os.path.join(video_dir, filename)
                    file.save(video_file_path)
                    video_count += 1
        flash(f"{pdf_count} PDFs und {video_count} Videos wurden erfolgreich hochgeladen!")

        bm25, doc_ids = bm25_retrieval.initialize_bm25(conn)
        handle_bm25_dump.modify_bm25_dump(conn, bm25, doc_ids, 'update')
        
        return redirect(url_for('upload'))
    return render_template('upload.html')

@app.route('/pdf/delete', methods=['GET'])
@admin_required
def pdf_delete():
    pdf_names = get_db_pdf_names(conn)
    return render_template('pdf_delete.html', pdf_names=pdf_names)

@app.route('/pdf/delete_all', methods=['POST'])
@admin_required
def delete_all_pdfs():
    pdfs = get_db_pdf_names(conn)
    for pdf in pdfs:
        file_path = os.path.join("data", pdf)
        delete_pdf(conn, file_path)
    flash("Alle PDFs (und zugehörige Videos, falls vorhanden) wurden erfolgreich gelöscht!")
    time.sleep(2)
    
    bm25, doc_ids = bm25_retrieval.initialize_bm25(conn)
    handle_bm25_dump.modify_bm25_dump(conn, bm25, doc_ids, 'update')
    
    return redirect(url_for('pdf_delete'))

@app.route('/pdf/delete/<path:pdf>', methods=['POST'])
@admin_required
def delete_single_pdf(pdf):
    file_path = os.path.join("data", pdf)
    delete_pdf(conn, file_path)
    flash(f"Datei '{pdf}' (und zugehöriges Video, falls vorhanden) wurde erfolgreich gelöscht!")
    time.sleep(2)
            
    bm25, doc_ids = bm25_retrieval.initialize_bm25(conn)
    handle_bm25_dump.modify_bm25_dump(conn, bm25, doc_ids, 'update')
    
    return redirect(url_for('pdf_delete'))

@app.route('/pdf_viewer/<path:filename>')
@login_required
def pdf_viewer(filename):
    page = request.args.get('page', default=1, type=int)
    return render_template('pdf_viewer.html', filename=filename, page=page)

@app.route('/video_player/<path:filename>')
@login_required
def video_player(filename):
    t = request.args.get('t', default=0, type=int)
    return render_template('video_player.html', filename=filename, t=t)

@app.route('/data/<path:filename>')
@login_required
def serve_pdf(filename):
    return send_from_directory("data", filename)

@app.route('/video/<path:filename>')
@login_required
def serve_video(filename):
    return send_from_directory("videos", filename)

def highlight(text, q):
    if not q:
        return text
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    return Markup(pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text))

app.jinja_env.filters['highlight'] = highlight

@app.route('/synonyms', methods=['GET', 'POST'])
@admin_required
def synonyms_management():
    cursor = conn.cursor()
    # carry over q for POST redirects and rendering
    q = request.args.get('q', '', type=str)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            words = request.form.get('words')
            if words:
                word_list = [w.strip() for w in words.split(',') if w.strip()]
                if word_list:
                    cursor.execute("INSERT INTO synonym_groups DEFAULT VALUES RETURNING id")
                    group_id = cursor.fetchone()[0]
                    for word in word_list:
                        cursor.execute(
                            "INSERT INTO synonyms (group_id, word) VALUES (%s, %s)",
                            (group_id, word)
                        )
                    conn.commit()

        elif action == 'delete':
            group_id = request.form.get('group_id')
            if group_id:
                cursor.execute("DELETE FROM synonym_groups WHERE id = %s", (group_id,))
                conn.commit()

        elif action == 'update':
            group_id = request.form.get('group_id')
            words = request.form.get('words')
            if group_id and words is not None:
                cursor.execute("DELETE FROM synonyms WHERE group_id = %s", (group_id,))
                word_list = [w.strip() for w in words.split(',') if w.strip()]
                for word in word_list:
                    cursor.execute(
                        "INSERT INTO synonyms (group_id, word) VALUES (%s, %s)",
                        (group_id, word)
                    )
                conn.commit()

        query_expansion.update_synonym_list(conn)
        flash("Synonyme aktualisiert!")
        # keep search after actions
        return redirect(url_for('synonyms_management', q=q) if q else url_for('synonyms_management'))

    # GET: list groups (filtered if q present)
    if q:
        cursor.execute("""
            SELECT sg.id,
                string_agg(s2.word, ', ' ORDER BY s2.word) AS words
            FROM synonym_groups sg
            JOIN synonyms s2 ON s2.group_id = sg.id
            WHERE sg.id IN (
                SELECT DISTINCT s.group_id
                FROM synonyms s
                WHERE s.word ILIKE %s
            )
            GROUP BY sg.id
            ORDER BY sg.id;
        """, (f"%{q}%",))
    else:
        cursor.execute("""
            SELECT sg.id,
                string_agg(s.word, ', ' ORDER BY s.word) AS words
            FROM synonym_groups sg
            JOIN synonyms s ON s.group_id = sg.id
            GROUP BY sg.id
            ORDER BY sg.id;
        """)

    groups = cursor.fetchall()
    return render_template('synonyms.html', groups=groups, q=q)

@app.route('/download_all')
@admin_required
def download_all():
    log_csv = log.get_log_csv(conn)
    map_csv = log.get_map_csv(conn)
    
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("log.csv", log_csv)
        zf.writestr("map.csv", map_csv)
    mem_zip.seek(0)
    
    return Response(
        mem_zip.read(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=combined_logs.zip"}
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    ADMIN_USERNAME = config.ADMIN_USERNAME
    ADMIN_PASSWORD = config.ADMIN_PASSWORD

    if request.method == 'POST':
         username = request.form.get('username')
         password = request.form.get('password')
         if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
             session['logged_in'] = True
             flash("Erfolgreich eingeloggt.")
             return redirect(url_for('search'))
         else:
             flash("Ungültige Anmeldedaten.")
    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
@login_required
def admin_login():
    if request.method == 'POST':
         username = request.form.get('username')
         password = request.form.get('password')
         # These credentials are fixed for admin mode
         if username == 'admin' and password == 'admin':
             session['admin_logged_in'] = True
             flash("Admin login erfolgreich.")
             return redirect(url_for('search'))
         else:
             flash("Ungültige Admin-Anmeldedaten.")
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('admin_logged_in', None)
    flash("Erfolgreich ausgeloggt.")
    return redirect(url_for('login'))

#if __name__ == '__main__':
#    app.run(debug=True, port=9000)