import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

LOGIN_URL = "http://localhost:9000/login"
SEARCH_URL = "http://localhost:9000/search"

USERNAME = "admin"
PASSWORD = "admin"
QUERY_TEXTS = [f"Test query {i}" for i in range(15)]

def get_logged_in_session():
    session = requests.Session()
    
    response = session.post(LOGIN_URL, data={
        'username': USERNAME,
        'password': PASSWORD
    })
    assert response.status_code == 200
    assert "Erfolgreich eingeloggt" in response.text
    return session

def send_query(session, query_text):
    response = session.post(SEARCH_URL, data={'query': query_text})
    return (query_text, response.status_code, response.text)

def main():
    session = get_logged_in_session()
    results = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_query = {
            executor.submit(send_query, session, q): q for q in QUERY_TEXTS
        }

        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                q, status, text = future.result()
                print(f"Query: {q} | Status: {status}")
                assert status == 200
                results.append((q, True))
            except Exception as e:
                print(f"Error on query '{query}': {e}")
                results.append((query, False))

    all_passed = all(success for _, success in results)
    print("ALL PASSED" if all_passed else "SOME FAILED")

if __name__ == "__main__":
    main()