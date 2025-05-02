from nltk.stem import SnowballStemmer
from nltk import word_tokenize
from nltk.corpus import stopwords

stemmer = SnowballStemmer('german')
stopwords = set(stopwords.words('german'))

def preprocess_text(text):
    toks = word_tokenize(text)
    toks = [t for t in toks if t.lower() not in stopwords]
    toks = [stemmer.stem(t) for t in toks]
    return toks