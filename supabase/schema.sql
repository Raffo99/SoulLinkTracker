-- =====================================================================
--  SOUL LINK TRACKER - database su Supabase
--  Incolla tutto nel "SQL Editor" del tuo progetto Supabase e premi Run.
-- =====================================================================

-- stato della partita (un'unica riga per partita; l'id e' il codice segreto)
create table if not exists public.soullink_partite (
  id          text primary key,
  stato       jsonb not null,
  versione    integer not null default 0,
  aggiornato  timestamptz not null default now()
);

-- chi e' online (aggiornato spesso, separato per non far riscaricare la partita)
create table if not exists public.soullink_presenza (
  partita     text not null,
  giocatore   text not null,
  visto       timestamptz not null default now(),
  info        jsonb,
  primary key (partita, giocatore)
);

alter table public.soullink_partite  enable row level security;
alter table public.soullink_presenza enable row level security;

-- si vede/modifica solo la partita di cui si conosce il codice (mandato dall'app nell'header x-partita)
drop policy if exists "partita con codice" on public.soullink_partite;
create policy "partita con codice" on public.soullink_partite
  for all to anon, authenticated
  using      (id = current_setting('request.headers', true)::json ->> 'x-partita')
  with check (id = current_setting('request.headers', true)::json ->> 'x-partita');

drop policy if exists "presenza con codice" on public.soullink_presenza;
create policy "presenza con codice" on public.soullink_presenza
  for all to anon, authenticated
  using      (partita = current_setting('request.headers', true)::json ->> 'x-partita')
  with check (partita = current_setting('request.headers', true)::json ->> 'x-partita');

grant select, insert, update on public.soullink_partite  to anon, authenticated;
grant select, insert, update on public.soullink_presenza to anon, authenticated;
