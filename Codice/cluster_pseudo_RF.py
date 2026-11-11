from elasticsearch import Elasticsearch # il server
from sklearn.feature_extraction.text import TfidfVectorizer # per creare la DTM con il tf-idf
from sklearn.preprocessing import normalize # per normalizzare la DTM
from sklearn.neighbors import NearestNeighbors # per il clustering
import numpy as np
from math import log10
from concurrent.futures import ThreadPoolExecutor
from heapq import nlargest
from time import sleep


def QE_kNN(server, INDEXNAME, N_collezione, querytext, first_query_size, k, e, Lambda):

    query_original = { 'match': { "_content": querytext } }
    response = server.search(index=INDEXNAME, query=query_original, size=first_query_size)

    def get_documents(response):
        return [hit['_source']['_content'] for hit in response['hits']['hits']]

    documents = get_documents(response)
    vectorizer = TfidfVectorizer(stop_words='english')
    dtm = vectorizer.fit_transform(documents)
    # Normalize the DTM
    dtm_normalized = normalize(dtm, norm='l2')

    neigh = NearestNeighbors(n_neighbors=k, metric="cosine")
    # Fit the classifier with the entire dataset (note that X should be the whole DataFrame)
    neigh.fit(dtm_normalized)

    # calcolo dei cluster stimati
    test=dtm_normalized
    # ???? threshold = 0.25 ???
    fitted_clusters = neigh.kneighbors(test, n_neighbors=k, return_distance=False)

    # calcolo del numero di volte in cui un documento appare in un cluster
    keys = [i for i in range(0,dtm_normalized.shape[0])]
    dominant_docs = dict.fromkeys(keys,0)
    for cluster in fitted_clusters:
        for doc in cluster:
            dominant_docs[doc] += 1

    # id dei documenti rilevanti
    def get_dominant_id(doc_freq, criterion):
        return [key for key, value in doc_freq.items() if value > criterion]

    min_occurrences_cluster = first_query_size*1/10
    #min_occurrences_cluster = 6
    dominant_ids = get_dominant_id(dominant_docs, min_occurrences_cluster)
    if not dominant_ids:
        print("! Nessun documento dominante !")
        return server.search(index=INDEXNAME, query=query_original, size=30)

    # fusione dei documenti in accordo ai cluster
    giga_docs = []
    for cluster in fitted_clusters[dominant_ids]:
        cluster_docs = np.array(documents)[cluster]
        giga_docs.append(" ".join(cluster_docs))

    # Indicizazzione dei cluster
    Indexname_supporto = "small_index"
    server.indices.create(index=Indexname_supporto, ignore=400)
    def index_document(this_id, record):
        record = {"id": this_id, "text": record}
        server.index(index=Indexname_supporto, id=this_id, document=record)

    with ThreadPoolExecutor() as executor:
       for this_id, record in enumerate(giga_docs):
            executor.submit(index_document, this_id, record)

    query_cluster = { 'match': { "text": querytext } }
    
    def get_first_id(query_dict):
        sleep(2)
        return server.search(index=Indexname_supporto, query=query_dict, size=1)["hits"]["hits"]

    print("Tentativo numero: 1")
    first_id = get_first_id(query_cluster)
    print("len:",len(first_id))

    i = 1
    while not first_id:
        i += 1
        sleep(i)
        print("Tentativo numero:",i)
        first_id = get_first_id(query_cluster)
        if i > 10:
            print(server.search(index=Indexname_supporto, query=query_cluster, size=1)["hits"]["hits"])
            raise ValueError(f"Query effettuata {i} volte")
    
    print("Numero di richieste mandate al server:",i)
    first_id = first_id[0]["_id"]

    tv = server.termvectors(index  = Indexname_supporto,         # term vector dall'indice
                    id     =  first_id,        # per il documento documento
                    fields = "text",            # con questi campi
                    term_statistics=True)

    terms=dict(tv)["term_vectors"]["text"]["terms"]
    tf_idfs = {key: value["term_freq"] * log10(N_collezione / value["doc_freq"]) for key, value in terms.items()}


    top_e = nlargest(e, tf_idfs.items(), key=lambda item: item[1])

    # Define your weighted terms
    weighted_terms = [{"term": {"_content": {"value": key, "boost": 1*(1-Lambda)}}} for key, value in top_e]
    weighted_terms.extend([{"term": {"_content": {"value": key, "boost": 1*Lambda}}} for key in querytext.split(" ")])

    # Create the query using function_score
    query_expanded = {
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": weighted_terms
                    }
                }
            }
        }
    }

    # Execute the search query
    qe_response = server.search(index=INDEXNAME, body=query_expanded, size=30)
    return qe_response


#server1 = Elasticsearch("http://localhost:9200")
#QE_kNN(server1, "robust", 51, qText, 10, 3, 4, 5, 0.8)