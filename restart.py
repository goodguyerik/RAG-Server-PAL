from init import check_and_create_tables

delete_instruction = """DROP TABLE pages; DROP TABLE texts; DROP TABLE map;"""

def restart_system(conn):
    cursor = conn.cursor()
    cursor.execute(delete_instruction)
    conn.commit()
    check_and_create_tables(conn)
    print("System restarted")