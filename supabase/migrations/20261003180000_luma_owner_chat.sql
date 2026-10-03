-- Text Luma itself: messages from the owner's own phone are conversation with
-- their Luma ("owner"), not replies from people they texted ("reply").
alter table luma_messages add column if not exists kind text not null default 'reply'
  check (kind in ('reply', 'owner', 'luma'));
