-- Everyone has a Luma account: an email and a key made from their password on their own device (Luma Cloud
-- hashes it again; the password itself never leaves the device). A Luma registered only for the phone app has
-- no phone number yet, so the phone is optional (it was required, which made registering for the phone app fail).
alter table luma_accounts alter column owner_phone drop not null;
alter table luma_accounts add column if not exists email text unique;
alter table luma_accounts add column if not exists key_hash text;
