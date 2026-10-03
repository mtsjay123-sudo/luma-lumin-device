-- Luma: everything Supabase needs, in one paste.
-- Supabase dashboard → SQL Editor → New query → paste this whole file → Run.
-- Safe to run more than once.

-- ── 1. Waitlist (the website's reservation form) ─────────────────────────────
create table if not exists reservations (
  id bigint generated always as identity primary key,
  email text not null,
  phone text,
  timestamp timestamptz not null default now()
);
alter table reservations enable row level security;

-- Nobody can read the waitlist with the public key any more. Only the server
-- (service-role key, behind the admin token) can.
do $$
declare p record;
begin
  for p in select policyname from pg_policies
           where schemaname = 'public' and tablename = 'reservations' and cmd in ('SELECT', 'ALL', 'UPDATE', 'DELETE')
  loop
    execute format('drop policy %I on public.reservations', p.policyname);
  end loop;
end $$;

-- The public sign-up form may still add itself to the list.
do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'reservations' and policyname = 'Anyone can join the waitlist') then
    create policy "Anyone can join the waitlist" on reservations for insert to anon with check (true);
  end if;
end $$;

-- ── 2. Luma Cloud: texting, quotas, Luma Plus ──────────────────────────────
-- Luma Cloud: Luma's texting number, monthly quotas and Luma Plus.
-- Every table has row-level security on with no policies, so only the
-- server-side service role (used by api/luma/[route].js) can read or write.

create table if not exists luma_accounts (
  id uuid primary key default gen_random_uuid(),
  owner_phone text not null unique,
  owner_name text not null default 'Luma owner',
  phone_verified_at timestamptz,
  plan text not null default 'free' check (plan in ('free', 'plus')),
  subscription_status text,
  stripe_customer_id text unique,
  stripe_subscription_id text,
  assigned_number text unique,
  assigned_number_sid text,
  created_at timestamptz not null default now()
);

create table if not exists luma_devices (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references luma_accounts(id) on delete cascade,
  secret_hash text not null,
  name text not null default 'Luma',
  created_at timestamptz not null default now(),
  last_seen_at timestamptz,
  revoked_at timestamptz
);
create index if not exists luma_devices_account on luma_devices(account_id);

create table if not exists luma_messages (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references luma_accounts(id) on delete cascade,
  device_id uuid references luma_devices(id) on delete set null,
  client_ref text,
  direction text not null check (direction in ('out', 'in')),
  to_number text,
  from_number text,
  body text not null,
  status text not null,
  provider_sid text unique,
  error_code text,
  created_at timestamptz not null default now(),
  unique (device_id, client_ref)
);
create index if not exists luma_messages_account_time on luma_messages(account_id, direction, created_at);
create index if not exists luma_messages_reply_lookup on luma_messages(to_number, from_number, created_at desc);

create table if not exists luma_usage (
  account_id uuid not null references luma_accounts(id) on delete cascade,
  period text not null,
  texts_sent integer not null default 0 check (texts_sent >= 0),
  primary key (account_id, period)
);

-- account_id null = opted out of the shared Luma number entirely.
create table if not exists luma_optouts (
  number text not null,
  account_id uuid references luma_accounts(id) on delete cascade,
  created_at timestamptz not null default now()
);
create unique index if not exists luma_optouts_unique on luma_optouts(number, coalesce(account_id, '00000000-0000-0000-0000-000000000000'::uuid));

create table if not exists luma_stripe_events (
  id text primary key,
  received_at timestamptz not null default now()
);

alter table luma_accounts enable row level security;
alter table luma_devices enable row level security;
alter table luma_messages enable row level security;
alter table luma_usage enable row level security;
alter table luma_optouts enable row level security;
alter table luma_stripe_events enable row level security;

-- Count one text against the month's allowance, atomically.
-- Returns the new count, or null when the allowance is already used up.
create or replace function luma_reserve_text(p_account uuid, p_period text, p_limit integer)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  v_count integer;
begin
  insert into luma_usage (account_id, period, texts_sent)
  values (p_account, p_period, 0)
  on conflict (account_id, period) do nothing;

  update luma_usage
     set texts_sent = texts_sent + 1
   where account_id = p_account and period = p_period and texts_sent < p_limit
  returning texts_sent into v_count;

  return v_count;
end;
$$;

-- Give a text back when the carrier definitively rejected it.
create or replace function luma_release_text(p_account uuid, p_period text)
returns void
language sql
security definer
set search_path = public
as $$
  update luma_usage set texts_sent = texts_sent - 1
   where account_id = p_account and period = p_period and texts_sent > 0;
$$;

revoke all on function luma_reserve_text(uuid, text, integer) from public, anon, authenticated;
revoke all on function luma_release_text(uuid, text) from public, anon, authenticated;
grant execute on function luma_reserve_text(uuid, text, integer) to service_role;
grant execute on function luma_release_text(uuid, text) to service_role;

-- ── 3. Texting your Luma from your phone ───────────────────────────────────
-- Text Luma itself: messages from the owner's own phone are conversation with
-- their Luma ("owner"), not replies from people they texted ("reply").
alter table luma_messages add column if not exists kind text not null default 'reply'
  check (kind in ('reply', 'owner', 'luma'));
