-- 004 — checkpoint retention. Optional, but run it on a schedule if the API is public.
--
-- The agent checkpoints every turn, including one-shot questions that will never be
-- resumed and every eval row. Nothing expires on its own, and the rows are not small:
-- a turn that searched a manual carries the retrieved chunks. Left alone, `checkpoints`
-- grows without bound.
--
-- There is no created_at column, so age comes from checkpoint_id, which LangGraph
-- generates as a UUID version 6: a 60-bit timestamp in 100-nanosecond intervals since
-- 1582-10-15, laid out most-significant-first so the ids sort chronologically as text.
-- The first 12 hex characters are the top 48 bits of that timestamp, so a cutoff can be
-- compared as a plain string prefix.

create or replace function checkpoint_id_cutoff(older_than interval)
returns text language sql stable as $$
    select lpad(to_hex(
        -- unix epoch → Gregorian epoch (12219292800 s earlier), seconds → 100ns units,
        -- then drop the low 12 bits that live after the version nibble.
        ((extract(epoch from now() - older_than)::numeric + 12219292800) * 10000000)::bigint >> 12
    ), 12, '0');
$$;

-- Delete checkpoints older than the interval, children first (no FK cascade is defined).
create or replace procedure prune_checkpoints(older_than interval default '30 days')
language plpgsql as $$
declare
    cutoff text := checkpoint_id_cutoff(older_than);
begin
    delete from checkpoint_writes where left(replace(checkpoint_id, '-', ''), 12) < cutoff;
    delete from checkpoints      where left(replace(checkpoint_id, '-', ''), 12) < cutoff;
    -- blobs are keyed by thread, not checkpoint: drop those with no checkpoints left.
    delete from checkpoint_blobs b
        where not exists (select 1 from checkpoints c where c.thread_id = b.thread_id);
end;
$$;

-- Preview what would go:
--   select count(*) from checkpoints
--    where left(replace(checkpoint_id, '-', ''), 12) < checkpoint_id_cutoff('30 days');
--
-- Run manually:   call prune_checkpoints('30 days');
-- Or with pg_cron:
--   select cron.schedule('prune-checkpoints', '0 4 * * *',
--                        $$call prune_checkpoints('30 days')$$);
