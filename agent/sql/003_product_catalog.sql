-- 003 — product catalog + chunk metadata. Run after 002; review catalog/products.json first.

-- 1. Store catalog. slug is the business key — it's what tools accept and chunks.product references.
create table if not exists products (
    id          bigint generated always as identity primary key,
    slug        text unique not null,    -- 'sony-a7-iv', 'canon-eos-r5', ...
    name        text not null,
    brand       text not null,
    type        text not null check (type in ('mirrorless', 'dslr', 'cinema')),
    sensor_format text check (sensor_format in ('full-frame', 'aps-c', 'micro-four-thirds')),
    description text,
    price_eur   numeric(10,2),
    in_stock    boolean not null default false,
    specs       jsonb,
    source_url  text,
    created_at  timestamptz default now()
);

-- RLS on: blocks reads via the anon/PostgREST API key. Our server connects as the
-- table owner (postgres.<ref>), which bypasses RLS, so the app is unaffected.
alter table products enable row level security;

-- 2. Chunk metadata for filtered retrieval (search_manual / explain_technique).
alter table chunks add column if not exists doc_type text;   -- 'manual' | 'technique'
alter table chunks add column if not exists brand    text;
alter table chunks add column if not exists product  text;   -- FK-by-convention to products.slug

-- 3. Backfill metadata onto corpus rows ingested before these columns existed.
update chunks set doc_type = 'manual',    brand = 'Fujifilm', product = 'fujifilm-x100v'
    where source = 'fujifilm-x100v-manual.pdf';
update chunks set doc_type = 'manual',    brand = 'Canon',    product = 'canon-eos-r5'
    where source = 'canon-eos-r5-user-guide.pdf';
update chunks set doc_type = 'technique'
    where source like 'technique-%';

-- 4. Partial index: manual searches always filter product = <slug>, and technique
--    chunks (product is null) would only bloat it. doc_type has 2 values — not worth indexing.
create index if not exists chunks_product_idx on chunks (product) where product is not null;

-- 5. Guard against typo'd doc_type values in future ingests.
alter table chunks drop constraint if exists chunks_doc_type_check;
alter table chunks add constraint chunks_doc_type_check
    check (doc_type in ('manual', 'technique'));
