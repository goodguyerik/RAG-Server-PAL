import os
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = 'secret'

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"),)

def get_page_text(conn, id, number):
    cursor = conn.cursor()
    cursor.execute(f"SELECT text FROM pages WHERE id = {id} AND number = {number};")
    return cursor.fetchall()[0][0]

def get_llm_answer(conn, query, doc_dict, k):
    texts = [get_page_text(conn, id, number) for id, number in doc_dict[:k]]
    prompt = f"Beantworte die Query '{query}' mithilfe der gegebenen Dokumente. Gebe zu jeder generierten Aussage die Quelle an, also das Dokument, was du zur Generierung der Antwort verwendet hast. Hier sind die zu verwendenden Dokumente: "
    for i in range(len(texts)):
        prompt += f'Dokument{i + 1}: {texts[i]} \n'
    answer = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f'{prompt}',
            }],
        model="gpt-4o",)
    return answer.choices[0].message.content
