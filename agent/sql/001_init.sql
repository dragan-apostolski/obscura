-- 001 — schema for the RAG corpus. Run once, before ingesting.

-- 1. Enable pgvector
create extension if not exists vector;

-- 2. Chunks table. embedding dim 384 = BAAI/bge-small-en-v1.5 (local).
create table if not exists chunks (
    id          bigint generated always as identity primary key,
    source      text not null,          -- filename / URL the chunk came from
    content     text not null,          -- the chunk text
    token_count int,
    embedding   vector(384),
    created_at  timestamptz default now()
);

-- 3. ANN index for fast cosine search (HNSW: high recall, good default).
--    Build AFTER a first bulk insert for speed; fine to create now for a small corpus.
create index if not exists chunks_embedding_hnsw
    on chunks using hnsw (embedding vector_cosine_ops);

-- The keyword index for hybrid search is added in 002:
-- create index if not exists chunks_content_fts on chunks using gin (to_tsvector('english', content));
