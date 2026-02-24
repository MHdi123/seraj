from quran_verses import search_verses

def get_verse_recommendations(user_question):
    return search_verses(user_question, top_k=5)
