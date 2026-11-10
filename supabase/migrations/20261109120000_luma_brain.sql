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

-- Who's asking the brain: the device, its account and this month's use in one trip, because every trip is time before
-- the first words. It also notes that the device was here.
create or replace function luma_brain_gate(p_device uuid, p_period text)
returns json language sql security definer set search_path = public as $$
  with seen as (update luma_devices set last_seen_at = now() where id = p_device returning *)
  select json_build_object(
    'device', (select row_to_json(d) from seen d),
    'account', (select row_to_json(a) from luma_accounts a where a.id = (select account_id from seen)),
    'usage', (select row_to_json(u) from luma_brain_usage u where u.account_id = (select account_id from seen) and u.period = p_period));
$$;
revoke all on function luma_brain_gate(uuid, text) from public, anon, authenticated;
grant execute on function luma_brain_gate(uuid, text) to service_role;
