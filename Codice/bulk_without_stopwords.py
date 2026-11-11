import logging
import json
import getopt, sys
import gzip
from elasticsearch import Elasticsearch as esserver
from elasticsearch.helpers import bulk
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Ensure stopwords and tokenizer resources are downloaded
nltk.download('stopwords')
nltk.download('punkt')

INDEXNAME = 'robust_without_stopwords'

# Initialize the set of stopwords
stop_words = set(stopwords.words('english'))

def remove_stopwords(text):
    words = word_tokenize(text)
    filtered_words = [word for word in words if word.lower() not in stop_words]
    return ' '.join(filtered_words)

def batch(infile):
    i = 0
    for line in infile:
        i += 1
        record = json.loads(line)
        logging.info("yielding %s", record['id'])
        
        # Remove stopwords from the content
        content_without_stopwords = remove_stopwords(record['content'])
        
        yield {
            "_index": INDEXNAME,
            "_id": record['id'],
            "_content": content_without_stopwords
        }

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:i:")
    except getopt.GetoptError as err:
        print(err)  # will print something like "option -a not recognized"
        sys.exit(2)
    
    filename = None
    global INDEXNAME
    
    for o, a in opts:
        if o == "-f":
            filename = a
        elif o == "-i":
            INDEXNAME = a
        else:
            assert False, "unhandled option"
    
    esclient = esserver('http://localhost:9200', request_timeout=60)
    infile = gzip.open(filename, 'rt')  # Open gzip file in text mode
    
    logging.basicConfig(filename='index-trec-fair-corpus.log',
                        filemode='a',
                        format='%(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)
    
    bulk(esclient, batch(infile))
    infile.close()

if __name__ == "__main__":
    main()