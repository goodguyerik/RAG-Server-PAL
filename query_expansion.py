# synonyms.py
# Replace your CSV-based synonym loader with a database version

synonym_map = {}

def update_synonym_list(conn):
    global synonym_map
    temp = {}
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sg.id, s.word
        FROM synonym_groups sg
        JOIN synonyms s ON s.group_id = sg.id
    """)
    rows = cursor.fetchall()
    
    group_map = {}
    for group_id, word in rows:
        group_map.setdefault(group_id, []).append(word)
        
    for group in group_map.values():
        for word in group:
            temp[word.lower()] = group
    synonym_map = temp

def expand_query(query):
    query_terms = query.split()
    expanded_terms = []
    for term in query_terms:
        lower_term = term.lower()
        if lower_term in synonym_map:
            expanded_terms.extend(synonym_map[lower_term])
        else:
            expanded_terms.append(term)
    return ' '.join(expanded_terms)