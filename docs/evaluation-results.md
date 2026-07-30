# Retrieval Evaluation Results

## Scope

This evaluation is a reproducible regression check for the included demonstration corpus. It
does not establish performance on private enterprise documents, other languages, or a larger
index.

The run on 2026-07-30 used:

- five project-authored documents and eight graded queries
- Python 3.13.11
- PostgreSQL 17.10, Redis 7.2.15, and Qdrant 1.18.3
- `BAAI/bge-small-en-v1.5` through FastEmbed with 384-dimensional vectors
- section-aware chunks of up to 300 tokens with 50-token overlap
- a result limit of five
- answer generation disabled

## Results

| Mode | Mean Recall@5 | MRR | Mean NDCG@5 |
| --- | ---: | ---: | ---: |
| Keyword | 0.2500 | 0.2500 | 0.2500 |
| Vector | 1.0000 | 0.9375 | 0.9506 |
| Hybrid | 1.0000 | 0.9375 | 0.9506 |

The vector and hybrid modes retrieved every graded source within the first five results. Seven
queries placed their highest-relevance source first; the device rollback source was second.
The suspicious-authentication query has two graded sources, which accounts for its NDCG value
below one despite finding both.

Keyword retrieval performed poorly on natural-language questions whose wording did not share
enough lexemes with the relevant passage. In this corpus, adding the sparse candidates did not
change the vector ordering, so hybrid and vector metrics are identical. This is useful
diagnostic evidence: the next evaluation iteration should test query expansion, a stronger
lexical configuration, or reranking rather than claiming that fusion improves every corpus.

## Reproduce

Start the complete environment and load the demonstration corpus:

```bash
make compose-up
make seed
```

Then run each mode:

```bash
MODE=keyword LIMIT=5 make evaluate
MODE=vector LIMIT=5 make evaluate
MODE=hybrid LIMIT=5 make evaluate
```

The script evaluates live API responses against
`samples/evaluation/queries.jsonl` and prints aggregate and per-query JSON. Source filenames,
heading paths, and PDF pages define relevance, so reingestion does not invalidate judgments
when deterministic chunk identifiers change with source content.
