import argparse

import numpy as np
import pandas as pd


IDLE_TAGS = {'Idler', 'Clicker', 'Incremental', 'Idle'}

IMPLAUSIBLE_HOURS = 20_000


def load(args):
    inter = pd.read_csv(args.interactions)
    if 'playtime_hours' not in inter.columns:
        raise SystemExit("no playtime_hours column - nothing to clean")
    inter['playtime_hours'] = inter['playtime_hours'].fillna(0).clip(lower=0)

    games = pd.read_csv(args.features)
    keep = [c for c in ('appid', 'name', 'type', 'tags') if c in games.columns]
    return inter, games[keep]


def tag_sets(games):
    import ast

    def parse(x):
        try:
            d = ast.literal_eval(x) if isinstance(x, str) else {}
            return set(d) if isinstance(d, dict) else set(d or ())
        except Exception:
            return set()

    return games['tags'].apply(parse) if 'tags' in games.columns else pd.Series([set()] * len(games))


def diagnose(inter, games, idle_ids, nongame_ids):
    n = len(inter)
    p = inter['playtime_hours']
    print(f"\n{'=' * 70}\nDIAGNOSIS — {n:,} interactions, "
          f"{inter['steamid'].nunique():,} users, {inter['game_id'].nunique():,} games")

    print("\n-- implausible single-game totals --")
    for cap in (1_000, 5_000, 10_000, 20_000, 50_000):
        m = p >= cap
        if m.any():
            print(f"  >= {cap:>6,}h : {m.sum():>6,} rows ({m.mean():.3%}), "
                  f"{inter.loc[m, 'steamid'].nunique():,} users, "
                  f"{inter.loc[m, 'game_id'].nunique():,} games")

    print("\n-- non-game appids (type != 'game') --")
    m = inter['game_id'].isin(nongame_ids)
    print(f"  {m.sum():,} rows ({m.mean():.2%}) across {inter.loc[m, 'game_id'].nunique():,} appids"
          f"{'' if not m.any() else f', median {p[m].median():.1f}h'}")

    print("\n-- idle / clicker / incremental tags --")
    m = inter['game_id'].isin(idle_ids)
    print(f"  {len(idle_ids):,} such games, {m.sum():,} rows ({m.mean():.2%})")
    if m.any():
        print(f"  median hours: {p[m].median():.1f} on idlers vs {p[~m].median():.1f} elsewhere")
        print(f"  they hold {p[m].sum() / p.sum():.1%} of all recorded playtime")

    print("\n-- games whose top owner dwarfs the typical one --")
    g = inter.groupby('game_id')['playtime_hours']
    stat = pd.DataFrame({'n': g.size(), 'med': g.median(), 'mx': g.max()})
    stat = stat[stat['n'] >= 20]
    if len(stat):
        stat['ratio'] = stat['mx'] / stat['med'].clip(lower=0.1)
        worst = stat.nlargest(8, 'ratio')
        names = games.set_index('appid')['name'] if 'name' in games.columns else {}
        print(f"  {'appid':>9} {'owners':>7} {'median':>8} {'max':>10}  ratio  name")
        for appid, r in worst.iterrows():
            nm = str(names.get(appid, ''))[:32] if len(names) else ''
            print(f"  {appid:>9} {int(r['n']):>7} {r['med']:>8.1f} {r['mx']:>10.0f} "
                  f"{r['ratio']:>6.0f}  {nm}")

    print("\n-- users dominated by one title --")
    tot = inter.groupby('steamid')['playtime_hours'].sum()
    top = inter.groupby('steamid')['playtime_hours'].max()
    share = (top / tot.clip(lower=1e-9))
    print(f"  one game is >50% of total hours for {(share > 0.5).mean():.1%} of users, "
          f">80% for {(share > 0.8).mean():.1%}")
    print('=' * 70)


def add_percentile(inter, min_owners):
    """playtime_pct: rank of this row among that game's owners, in [0, 1]."""
    g = inter.groupby('game_id')['playtime_hours']
    inter['playtime_pct'] = g.rank(pct=True, method='average')
    # Too few owners to rank meaningfully -> leave it blank rather than fake it.
    inter.loc[g.transform('size') < min_owners, 'playtime_pct'] = np.nan
    return inter


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--interactions', default='steam_users_games_processed.csv')
    ap.add_argument('--features', default='game_features_v2.csv')
    ap.add_argument('--out', default='steam_users_games_clean.csv')
    ap.add_argument('--write', action='store_true', help='write the cleaned file (default: diagnose only)')
    ap.add_argument('--keep-nongames', action='store_true')
    ap.add_argument('--keep-idlers', action='store_true',
                    help='keep idle/clicker games (their hours are still winsorised)')
    ap.add_argument('--winsorise', type=float, default=0.99,
                    help='cap each game\'s playtime at this quantile; 0 disables')
    ap.add_argument('--pct-min-owners', type=int, default=10,
                    help='owners needed before a per-game percentile is meaningful')
    args = ap.parse_args()

    inter, games = load(args)
    tags = tag_sets(games)
    idle_ids = set(games.loc[tags.apply(lambda t: bool(t & IDLE_TAGS)), 'appid'])
    nongame_ids = (set(games.loc[games['type'].fillna('unknown') != 'game', 'appid'])
                   if 'type' in games.columns else set())

    diagnose(inter, games, idle_ids, nongame_ids)

    if not args.write:
        print("\nDiagnosis only. Re-run with --write to produce the cleaned file.")
        return

    print(f"\n{'=' * 70}\nCLEANING")
    n0, h0 = len(inter), inter['playtime_hours'].sum()

    if not args.keep_nongames and nongame_ids:
        m = inter['game_id'].isin(nongame_ids)
        print(f"  drop non-games          : -{m.sum():,} rows")
        inter = inter[~m]

    if not args.keep_idlers and idle_ids:
        m = inter['game_id'].isin(idle_ids)
        print(f"  drop idle/clicker games : -{m.sum():,} rows")
        inter = inter[~m]

    m = inter['playtime_hours'] >= IMPLAUSIBLE_HOURS
    if m.any():
        print(f"  drop >{IMPLAUSIBLE_HOURS:,}h rows      : -{m.sum():,} rows")
        inter = inter[~m]

    if args.winsorise:
        cap = inter.groupby('game_id')['playtime_hours'].transform(
            lambda s: s.quantile(args.winsorise) if len(s) >= 20 else s.max())
        hit = inter['playtime_hours'] > cap
        trimmed = (inter['playtime_hours'] - cap)[hit].sum()
        inter = inter.copy()
        inter['playtime_hours'] = np.minimum(inter['playtime_hours'], cap).round(2)
        print(f"  winsorise at q{args.winsorise:<5g}     : {hit.sum():,} rows capped, "
              f"{trimmed:,.0f} hours removed")

    inter = add_percentile(inter.reset_index(drop=True), args.pct_min_owners)

    print(f"\n  rows    {n0:,} -> {len(inter):,} ({len(inter) / n0:.1%} kept)")
    print(f"  hours   {h0:,.0f} -> {inter['playtime_hours'].sum():,.0f} "
          f"({inter['playtime_hours'].sum() / h0:.1%} kept)")
    print(f"  users   {inter['steamid'].nunique():,}   games {inter['game_id'].nunique():,}")
    print(f"  playtime_pct available for {inter['playtime_pct'].notna().mean():.1%} of rows")

    inter.to_csv(args.out, index=False)
    print(f"\nWrote {args.out}")
    print("Point train.py at it:  user_csv='" + args.out + "'")


if __name__ == '__main__':
    main()
