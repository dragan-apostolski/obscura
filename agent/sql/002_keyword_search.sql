-- 002 — keyword search for hybrid retrieval. Run after 001.

-- 1. Generated tsvector column: Postgres keeps it in sync with `content`.
alter table chunks
    add column if not exists content_tsv tsvector
    generated always as (to_tsvector('english', content)) stored;

-- 2. GIN index makes the @@ keyword match fast.
create index if not exists chunks_content_tsv_gin
    on chunks using gin (content_tsv);
