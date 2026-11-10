-- The Super Intelligence (Luma Plus): the cloud brain asked through the relay.
-- Only counts are kept here: per account, per month. No message, no reply, no memory, nothing a person said.
-- NOT APPLIED YET: applying this changes the live database, which needs the owner's yes.

alter table luma_accounts add column if not exists brain_consent_at timestamptz;  -- when the owner said yes on their Luma; null: not yet, or taken back
alter table luma_accounts add column if not exists brain_consent_words integer;  -- which wording of the yes screen they said yes to

create table if not exists luma_brain_usage (
  account_id uuid not null references luma_accounts(id) on delete cascade,
  period text not null,                 -- "2026-11"
  micros bigint not null default 0,     -- cost so far, in millionths of a dollar
  calls integer not null default 0,
  tokens_in bigint not null default 0,
  tokens_out bigint not null default 0,
  cache_read bigint not null default 0,
  ms bigint not null default 0,
  primary key (account_id, period)
);
alter table luma_brain_usage enable row level security;

create or replace function luma_add_brain_usage(p_account uuid, p_period text, p_micros bigint, p_calls integer, p_tokens_in bigint,
                                                p_tokens_out bigint, p_cache_read bigint, p_ms bigint)
returns void language sql security definer set search_path = public as $$
  insert into luma_brain_usage (account_id, period, micros, calls, tokens_in, tokens_out, cache_read, ms)
  values (p_account, p_period, p_micros, p_calls, p_tokens_in, p_tokens_out, p_cache_read, p_ms)
  on conflict (account_id, period) do update set
    micros = luma_brain_usage.micros + excluded.micros, calls = luma_brain_usage.calls + excluded.calls,
    tokens_in = luma_brain_usage.tokens_in + excluded.tokens_in, tokens_out = luma_brain_usage.tokens_out + excluded.tokens_out,
    cache_read = luma_brain_usage.cache_read + excluded.cache_read, ms = luma_brain_usage.ms + excluded.ms;
$$;
revoke all on function luma_add_brain_usage(uuid, text, bigint, integer, bigint, bigint, bigint, bigint) from public, anon, authenticated;
grant execute on function luma_add_brain_usage(uuid, text, bigint, integer, bigint, bigint, bigint, bigint) to service_role;
