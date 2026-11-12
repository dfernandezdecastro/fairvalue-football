-- FairValue Football: initial schema (Step 6).
-- Holds DERIVED outputs and the individual facts each page needs (see DATA_SOURCES.md, decision D15).
-- Public read-only: every table has RLS enabled with a SELECT policy and no write policies.
-- Writes happen only from the pipeline machine with the database owner's connection.

create extension if not exists pg_trgm;

-- ------------------------------------------------------------------ dimensions
create table competitions (
  id               text primary key,
  name             text not null,
  country          text,
  is_big5          boolean not null,
  has_full_history boolean not null
);

create table clubs (
  id   bigint primary key,
  name text not null,
  slug text not null unique
);

create table players (
  id           bigint primary key,
  name         text not null,
  slug         text not null unique,
  birth_year   integer,             -- year only: data minimisation
  position     text,                -- current Transfermarkt label
  sub_position text,
  foot         text,
  height_cm    real,
  citizenship  text                 -- display only; never a model feature
);
create index players_name_trgm on players using gin (lower(name) gin_trgm_ops);

-- ------------------------------------------------------------------ Layer 1: profiles
create table player_seasons (
  player_id        bigint not null references players (id),
  season           integer not null,              -- start year: 2024 = 2024/25
  competition_id   text not null references competitions (id),
  club_id          bigint references clubs (id),
  data_tier        text not null check (data_tier in ('full', 'basic')),
  position_group   text not null,
  position_source  text not null,
  age              real,
  games            integer not null,
  minutes          integer not null,
  starts           integer not null,
  goals            integer not null,
  assists          integer not null,
  npxg             real, xa real, shots real, key_passes real, xg_chain real, xg_buildup real,
  minutes_share    real,
  starts_share     real,
  team_ppg         real,
  eligible         boolean not null,              -- >= 900 league minutes and known position
  peer_scope       text not null,                 -- 'big5' or the league id
  peer_n           integer not null,
  goals_p90 real, assists_p90 real, npxg_p90 real, xa_p90 real, shots_p90 real, key_passes_p90 real,
  xg_chain_p90 real, xg_buildup_p90 real,
  goals_p90_shrunk real, assists_p90_shrunk real, npxg_p90_shrunk real, xa_p90_shrunk real,
  shots_p90_shrunk real, key_passes_p90_shrunk real, xg_chain_p90_shrunk real, xg_buildup_p90_shrunk real,
  goals_p90_pct real, assists_p90_pct real, npxg_p90_pct real, xa_p90_pct real, shots_p90_pct real,
  key_passes_p90_pct real, xg_chain_p90_pct real, xg_buildup_p90_pct real,
  minutes_share_pct real, starts_share_pct real,
  primary key (player_id, season, competition_id)
);
create index player_seasons_peer on player_seasons (season, position_group, peer_scope) where eligible;

create table similar_players (
  player_id                bigint not null,
  season                   integer not null,
  competition_id           text not null,
  rank                     integer not null,
  neighbour_id             bigint not null references players (id),
  neighbour_competition_id text not null,
  similarity               real not null,
  primary key (player_id, season, competition_id, rank),
  foreign key (player_id, season, competition_id) references player_seasons (player_id, season, competition_id)
);

-- ------------------------------------------------------------------ model runs
create table model_runs (
  id               text primary key,                -- e.g. 'piv-2026-11-12T20:04:04+00:00'
  model            text not null check (model in ('piv', 'expected_fee')),
  created_at       timestamptz not null,
  pipeline_version text not null,
  is_current       boolean not null default true,
  summary          jsonb not null                   -- metrics, coverage, selection, backtest
);

-- ------------------------------------------------------------------ Layer 2: performance-implied value
create table piv_estimates (
  player_id          bigint not null,
  season             integer not null,
  competition_id     text not null,
  model_tier         text not null check (model_tier in ('full', 'basic')),
  model_run_id       text not null references model_runs (id),
  model_kind         text not null,
  train_through      integer not null,              -- vintage: trained on seasons <= this only
  reliability        text not null check (reliability in ('High', 'Moderate', 'Low', 'Insufficient')),
  reliability_reason text not null,
  market_value_eur   real,                          -- Transfermarkt value after the season (the one compared)
  market_value_date  date,
  market_index_eur   real,
  estimate_eur       real, lo80_eur real, hi80_eur real, lo95_eur real, hi95_eur real,
  peer_estimate_eur  real, peer_lo80_eur real, peer_hi80_eur real, peer_lo95_eur real, peer_hi95_eur real,
  league_shift_log   real,
  market_gap_log     real,
  gap_log            real,                          -- peer-relative (decision D11)
  gap_label          text,
  calibration_group  text,
  drivers            jsonb,
  primary key (player_id, season, competition_id, model_tier),
  foreign key (player_id, season, competition_id) references player_seasons (player_id, season, competition_id),
  -- rule R3: no estimate without its range
  check (estimate_eur is null or (lo80_eur is not null and hi80_eur is not null))
);
create index piv_estimates_gap on piv_estimates (season, gap_label) where reliability <> 'Insufficient';

-- ------------------------------------------------------------------ Layer 3: transfers and expected fee
create table transfers (
  id                  bigint primary key,
  player_id           bigint not null references players (id),
  date                date not null,
  season              integer not null,
  transfer_window     text not null,                 -- summer | winter | other
  from_club_id        bigint not null references clubs (id),
  to_club_id          bigint not null references clubs (id),
  from_competition_id text references competitions (id),
  to_competition_id   text references competitions (id),
  position_group      text,
  age                 real,
  fee_eur             real not null,
  mv_before_eur       real,                         -- last Transfermarkt value strictly before the transfer
  mv_before_date      date,
  model_run_id        text references model_runs (id),
  expected_fee_eur    real, lo80_eur real, hi80_eur real, lo95_eur real, hi95_eur real,
  premium_eur         real,
  premium_pct         real,
  label               text,
  reliability         text not null check (reliability in ('High', 'Moderate', 'Low', 'Insufficient')),
  reliability_reason  text not null,
  calibration_group   text,
  drivers             jsonb,
  check (expected_fee_eur is null or (lo80_eur is not null and hi80_eur is not null))
);
create index transfers_season on transfers (season);
create index transfers_to_club on transfers (to_club_id);
create index transfers_from_club on transfers (from_club_id);
create index transfers_player on transfers (player_id);

create table club_audit (
  club_id                      bigint not null references clubs (id),
  period                       text not null check (period in ('all', 'last3')),
  season_from                  integer not null,
  season_to                    integer not null,
  n_assessed                   integer not null,
  ranked                       boolean not null,
  total_fee_eur                real not null,
  total_expected_eur           real not null,
  price_ratio                  real not null,
  price_ratio_lo80             real,
  price_ratio_hi80             real,
  share_notable_premium        real not null,
  share_notable_discount       real not null,
  outcome_n                    integer not null,
  outcome_median_mv_change_12m real,                -- outcome, not used by any model
  primary key (club_id, period)
);

-- ------------------------------------------------------------------ reference
create table data_coverage (
  source         text not null,
  competition_id text not null,
  season         integer not null,
  status         text not null,
  primary key (source, competition_id, season)
);

create table app_meta (
  key   text primary key,
  value jsonb not null
);

-- ------------------------------------------------------------------ views (security_invoker: RLS applies)
-- One row per player-season with the best available PIV tier (full preferred).
create view v_player_season with (security_invoker = true) as
select ps.*, p.name as player_name, p.slug as player_slug, p.birth_year, p.citizenship,
       c.name as club_name, c.slug as club_slug, comp.name as competition_name,
       e.model_tier, e.reliability, e.reliability_reason, e.market_value_eur, e.market_value_date,
       e.estimate_eur, e.lo80_eur, e.hi80_eur, e.lo95_eur, e.hi95_eur,
       e.peer_estimate_eur, e.peer_lo80_eur, e.peer_hi80_eur, e.peer_lo95_eur, e.peer_hi95_eur,
       e.gap_log, e.gap_label, e.drivers, e.train_through
from player_seasons ps
join players p on p.id = ps.player_id
left join clubs c on c.id = ps.club_id
join competitions comp on comp.id = ps.competition_id
left join lateral (
  select * from piv_estimates pe
  where pe.player_id = ps.player_id and pe.season = ps.season and pe.competition_id = ps.competition_id
  order by (pe.model_tier = 'full') desc
  limit 1
) e on true;

create view v_transfers with (security_invoker = true) as
select t.*, p.name as player_name, p.slug as player_slug,
       fc.name as from_club_name, fc.slug as from_club_slug,
       tc.name as to_club_name, tc.slug as to_club_slug
from transfers t
join players p on p.id = t.player_id
join clubs fc on fc.id = t.from_club_id
join clubs tc on tc.id = t.to_club_id;

create view v_club_audit with (security_invoker = true) as
select a.*, c.name as club_name, c.slug as club_slug
from club_audit a join clubs c on c.id = a.club_id;

-- ------------------------------------------------------------------ row-level security: public read only
do $$
declare t text;
begin
  foreach t in array array['competitions', 'clubs', 'players', 'player_seasons', 'similar_players',
                           'model_runs', 'piv_estimates', 'transfers', 'club_audit', 'data_coverage', 'app_meta']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy "public read" on %I for select to anon, authenticated using (true)', t);
    execute format('revoke insert, update, delete, truncate on %I from anon, authenticated', t);
  end loop;
end $$;

grant select on v_player_season, v_transfers, v_club_audit to anon, authenticated;
