-- Accent-insensitive search: "mbappe" finds "Mbappé". search_name is lower-case, accent-stripped,
-- computed by the pipeline (unaccent() isn't immutable, so it can't be a generated column).
alter table players add column search_name text;
alter table clubs add column search_name text;
create index players_search_trgm on players using gin (search_name gin_trgm_ops);
create index clubs_search_trgm on clubs using gin (search_name gin_trgm_ops);
