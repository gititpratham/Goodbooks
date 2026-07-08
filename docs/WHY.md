# Why This Project

## Motivation

Book discovery is a problem almost every reader has felt firsthand — too many books, too little
signal on which ones are actually worth the time. That made it a compelling, personally relatable
domain to build a *complete* product around, rather than stopping at a notebook full of
exploratory plots. Goodbooks was built to answer a simple question: given a raw, publicly available
dataset, how far can it be taken — through cleaning, enrichment, modelling, and deployment — before
it becomes something a real person could actually use to find their next book?

## What Makes It Special

- **It's a genuine ML system, not a lookup table.** Recommendations come from a trained
  `MLPClassifier` scoring every book in the catalog against a learned user preference vector —
  trained on 424,000+ pairwise user–book interactions from 53,424 users — not from static rules or
  simple genre matching.
- **Hybrid signal design.** The model blends structured signals (genre/mood multi-hot, numeric
  features like pages, publication year, and rating) with unstructured signal (TF-IDF + SVD
  embeddings of book descriptions), so recommendations respond to both explicit taste and semantic
  content.
- **Data enrichment, not just data display.** The underlying Goodbooks-10K dataset was incomplete —
  many books were missing publication years, and several descriptions were thin or uninformative.
  Missing publication years were backfilled, and richer, more useful descriptions were generated
  using a **locally-run LLM**, rather than shipping the raw data as-is.
- **Cost-conscious, repeatable enrichment.** Using a local LLM for description generation avoided
  reliance on paid third-party APIs and external rate limits, keeping the enrichment pipeline free
  to run and easy to repeat as the dataset evolved.
- **End-to-end ownership.** The project spans data cleaning, feature engineering, model training
  and evaluation (ROC-AUC of 0.86), a documented REST API, a polished React/TypeScript frontend,
  containerization, and live cloud deployment — a complete pipeline rather than an isolated script.
- **Real, hosted product.** Goodbooks isn't just source code sitting in a repository — it's
  deployed and publicly usable at https://goodbooks.pratham.dpdns.org, running on a live Oracle
  Cloud Infrastructure instance.

## Links

- Live Demo: https://goodbooks.pratham.dpdns.org
- Docs / Source: https://github.com/gititpratham/Goodbooks
- Dataset: [Goodbooks-10K on Kaggle](https://www.kaggle.com/datasets/zygmunt/goodbooks-10k)
