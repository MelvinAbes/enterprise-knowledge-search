# Demonstration Corpus

These documents describe a fictional software operations environment. They were written for
this repository and contain no customer, employer, or personal data. They are distributed
under the repository's Apache-2.0 licence.

The corpus deliberately contains related terminology across several documents so keyword,
vector, and hybrid retrieval can be compared. `evaluation/queries.jsonl` defines graded
relevance judgments using filenames and source locations, which remain stable across repeated
ingestion runs.

Generate the PDF fixture if it is missing:

```bash
uv run python scripts/generate_demo_pdf.py
```

With the local stack running, load the corpus and execute an evaluation:

```bash
make seed
make evaluate
```

The evaluation command reports measurements from the running service. No benchmark output is
committed as a claim about untested environments.
