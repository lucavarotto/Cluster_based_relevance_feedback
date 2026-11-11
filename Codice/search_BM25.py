import os

from elasticsearch import Elasticsearch as esserver
esclient = esserver('http://localhost:9200')

# I percorsi sono ancorati alla cartella di questo file, non alla working
# directory, cosi' lo script funziona da qualsiasi posizione venga lanciato.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # Codice/
PROJECT_DIR = os.path.dirname(BASE_DIR)                 # radice del progetto
DATA_DIR = os.path.join(PROJECT_DIR, "Dati")            # i topic
OUT_DIR = os.path.join(PROJECT_DIR, "Results", "Test")  # le run prodotte

def searchTxt(pathInput, indexName):

  # Results/ non e' versionata, quindi puo' mancare in un clone pulito
  os.makedirs(OUT_DIR, exist_ok=True)

  file = open(pathInput, 'r')
  fileO = open(os.path.join(OUT_DIR, "results_BM25.txt"), 'w')

  while True:
    content=file.readline()
    if("<num>" in content):
      qIndx = content.removeprefix("<num> Number: ").strip()
      print(qIndx)
    elif("<title>" in content):
      content = content.removeprefix("<title>").strip()
      if(len(content)==0):
        content=file.readline().strip()
      print("\nquery num:", qIndx, ", content:", content)
      query_dict = {'match': { '_content': content } }
      response = esclient.search(index=indexName, query=query_dict, size=30)
      i = 1
      for hit in response['hits']['hits']:          
        st =f"{qIndx} Q0 {hit["_id"]} {i} {hit["_score"]} {hit["_index"]} \n"
        i +=1
        fileO.write(st) #numero query, indice     
    elif not content:
      break

  file.close()
  fileO.close()

searchTxt(os.path.join(DATA_DIR, "test.txt"), "robust")