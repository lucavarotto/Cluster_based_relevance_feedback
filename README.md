# Cluster-based Pseudo-Relevance Feedback with k-NN

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-BM25-005571?logo=elasticsearch&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-TF--IDF%20%7C%20k--NN-F7931E?logo=scikitlearn&logoColor=white)
![R](https://img.shields.io/badge/R-significance%20tests-276DC3?logo=r&logoColor=white)

Pseudo-relevance feedback takes the top results of a first retrieval, assumes
they are relevant, and uses their terms to expand the query. Its weak spot is
that those top documents often cover several subtopics, so the expansion drifts
away from what the user asked.

This project implements the remedy proposed by Lee, Croft and Allan: cluster
the top-retrieved documents with k-NN, find the **dominant documents**, the
ones that show up in many overlapping clusters and therefore touch every
subtopic, and expand the query only from the clusters they belong to. The
method is implemented on top of Elasticsearch and evaluated against plain
BM-25 on the TREC ROBUST 2004 collection.

**Academic context.** Written by Andrea Quartuccio and Luca Varotto for the
*Information Retrieval* exam of the BSc in *Statistics for Technology and
Science* at the University of Padua, June 2024. The presentation is in Italian.

---

## The method

The post-retrieval function is `QE_kNN` in
[`Codice/cluster_pseudo_RF.py`](Codice/cluster_pseudo_RF.py). It runs in seven steps:

1. **First retrieval** of the top `N` documents for the original query, with
   BM-25 over the whole collection.
2. **Clustering** of those `N` documents: a TF-IDF document-term matrix built
   with `TfidfVectorizer`, normalised, then `NearestNeighbors` with `k = 5`.
   Every document forms its own cluster with its `k` closest neighbours, so the
   clusters overlap and one document can belong to several of them.
3. **Dominant documents**: those appearing in at least a tenth of the clusters
   (`min_occurrences_cluster = N/10`). If none qualifies, the function returns
   the BM-25 results unchanged, which makes the method a safe fallback rather
   than a gamble.
4. **Mega-texts**: the documents of each cluster containing a dominant document
   are concatenated into a single text, indexed in a temporary index.
5. **Retrieval over the mega-texts** with the original query.
6. **Query expansion**: the `e` highest scoring terms of the best mega-text are
   added to the query, weighted by `λ`.
7. **Second retrieval** of the expanded query over the whole collection.

| Parameter | In the code | Meaning |
| --- | --- | --- |
| `N` | `first_query_size` | documents retrieved by the first query and fed to the clustering |
| `k` | `k` | neighbours of each document, fixed at 5 |
| `e` | `e` | number of expansion terms added to the query |
| `λ` | `Lambda` | weight of the expansion terms in the new query |

---

## Repository structure

```
cluster_based_relevance_feedback/
├── Codice/
│   ├── bulk.py                      # indexes ROBUST 2004 into Elasticsearch
│   ├── bulk_without_stopwords.py    # same, dropping stopwords at index time
│   ├── cluster_pseudo_RF.py         # QE_kNN, the post-retrieval function above
│   ├── search.py                    # runs the topics through QE_kNN, grid search
│   └── search_BM25.py               # the BM-25 baseline run
├── Quartuccio_Varotto.pdf           # the presentation (Italian)
├── .gitignore
└── README.md
```

Both search scripts read the topic file from `Dati/` and write their run into
`Results/Test/` in `trec_eval` format. They resolve those paths from the
location of the script itself, so they can be launched from any working
directory, and they create the output folder if it is missing.

### What is not in this repository

**Neither the data nor the `.txt` files with the results have been uploaded.**
The repository holds the code, the presentation and this README, nothing else:

| Not published | What it is | Why |
| --- | --- | --- |
| `Dati/` | `train.txt` and `test.txt`, the 250 ROBUST 2004 topics split into the two sets | part of the TREC collection, which is not ours to redistribute |
| `Results/` | every run and the `.txt` output of `trec_eval`, about 340 files | regenerable by running the scripts against the collection |
| `Paper/` | the articles behind the method | works by other authors, cited below instead |
| `presentazione.pptx` | the source of the published presentation | of the presentation, only the PDF is published |

Everything above stays in the local working folder; see `.gitignore`. So the
scripts in `Codice/` run as they are only on a machine that has the collection
indexed in Elasticsearch and the topic files in `Dati/`.

---

## Results

The collection is TREC **ROBUST 2004**, indexed without stopwords. Of its 250
topics, the **first 150 are the training set**, used to choose the parameters,
and the **last 100 the test set**, used to evaluate. Runs are scored with
`trec_eval`; the grid search covers `N` and `e` in {10, 25, 50, 75, 100} and
`λ` from 0.1 to 0.9.

Two configurations were selected on the training set, one per measure, and then
compared with BM-25 on the test set:

| Configuration | Parameters | Measure | BM-25 | k-NN pseudo-RF |
| --- | --- | --- | --- | --- |
| Best MAP | `N=10`, `e=25`, `λ=0.7` | MAP | 0.13 | **0.15** |
| Best P@5 | `N=10`, `e=100`, `λ=0.9` | P@5 | 0.48 | **0.52** |

**Significance.** Both comparisons were tested with a paired t-test and a
Wilcoxon signed-rank test, one-sided alternative. The gain in average precision
is significant (p < 0.05); the gain in P@5 is **not** (p > 0.05). So the method
improves the ranking as a whole, while the evidence on the very top of the list
is not conclusive.

**Where it helps and where it hurts.** Looking at single topics under the best
MAP configuration, topic 607, *Human genetic code*, improves the most: the
expansion adds terms such as *genetic*, *gene*, *genome* and *dna*, a relevant
document climbs from rank 10 to rank 1 and a new relevant one is retrieved.
Topic 626, *Human Stampede*, degrades the most: the first retrieval is led by
non-relevant documents about the Calgary Stampede rodeo, so the expansion picks
up *calgary*, *rodeo* and *stampeders*, and the one marginally relevant document
slips from rank 2 to rank 10. The method inherits the quality of its first
retrieval, which is the structural limit of any pseudo-relevance feedback.

The practical cost is computational: every query needs a clustering, a
temporary index and two retrievals, which is what kept the grid search coarse.
Natural next steps would be the resampling of the original paper, a language
model in place of BM-25, a less arbitrary dominance threshold and Kendall's tau
as a measure of rank correlation.

---

## References

1. Lee, K. S., Croft, W. B., & Allan, J. (2008). *A cluster-based resampling
   method for pseudo-relevance feedback*. SIGIR.
2. Smucker, M. D., Allan, J., & Carterette, B. (2007). *A comparison of
   statistical significance tests for information retrieval evaluation*. CIKM.
3. M. Melucci. *Information Retrieval, macchine e motori di ricerca*.

---

## Authors

**Andrea Quartuccio** and **Luca Varotto** — BSc in Statistics for Technology
and Science, University of Padua. Presented for the *Information Retrieval*
exam, June 2024.
