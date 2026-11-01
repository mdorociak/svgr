import argparse
import ast
import json
import os


def load_jsonl(path):
    if not os.path.exists(path):
        print(f"  ! {path} missing - continuing without it")
        return {}
    out = {}
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            out[r["appid"]] = r
    return out


def to_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--steam", default="steam_raw.jsonl")
    p.add_argument("--steamspy", default="steamspy_raw.jsonl")
    p.add_argument("--user-csv", default="steam_users_games_processed.csv")
    p.add_argument("--column", default="game_id")
    p.add_argument("--out", default="game_features_v2.csv")
    p.add_argument("--max-tags", type=int, default=20,
                   help="keep the N highest-voted tags per game")
    args = p.parse_args()

    import pandas as pd

    print("Loading raw scrapes...")
    steam = load_jsonl(args.steam)
    spy = load_jsonl(args.steamspy)
    print(f"  steam:    {len(steam):,} records, {sum(r.get('ok', False) for r in steam.values()):,} ok")
    print(f"  steamspy: {len(spy):,} records, {sum(r.get('ok', False) for r in spy.values()):,} ok")

    appids = sorted(set(steam) | set(spy))
    rows = []

    for appid in appids:
        s = steam.get(appid, {})
        y = spy.get(appid, {})
        s_ok, y_ok = s.get("ok", False), y.get("ok", False)

        genres = s.get("genres") if s_ok else None
        if not genres and y_ok and y.get("genre"):
            genres = [g.strip() for g in str(y["genre"]).split(",") if g.strip()]
        genres = genres or []

        categories = (s.get("categories") or []) if s_ok else []

        tags = {}
        if y_ok and isinstance(y.get("tags"), dict):
            tags = dict(sorted(y["tags"].items(),
                               key=lambda kv: kv[1], reverse=True)[:args.max_tags])

        price_cents = None
        if s_ok and s.get("price_cents") is not None:
            price_cents = s["price_cents"]
        elif y_ok and y.get("price_cents") is not None:
            price_cents = y["price_cents"]
        if s_ok and s.get("is_free"):
            price_cents = 0
        price = round(to_int(price_cents) / 100.0, 2)

        rows.append({
            "appid": appid,
            "name": (s.get("name") if s_ok else None) or y.get("name") or "",
            "genres": repr(genres),
            "categories": repr(categories),
            "tags": repr(tags),
            "positive": to_int(y.get("positive")),
            "negative": to_int(y.get("negative")),
            "price": price,
            "required_age": to_int(s.get("required_age")),
            "type": (s.get("type") if s_ok else None) or "unknown",
            "release_date": (s.get("release_date") if s_ok else None) or "",
            "has_features": int(bool(genres or categories or tags)),
        })

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {len(df):,} rows -> {args.out}")

    print("\n--- content depth ---")
    n_tags = df["tags"].apply(lambda s: len(ast.literal_eval(s)))
    n_gen = df["genres"].apply(lambda s: len(ast.literal_eval(s)))
    print(f"  tags/game:   mean {n_tags.mean():.1f}  median {int(n_tags.median())}  zero {(n_tags == 0).sum():,}")
    print(f"  genres/game: mean {n_gen.mean():.1f}  zero {(n_gen == 0).sum():,}")
    print(f"  has_features=1: {df['has_features'].mean():.3f}")

    vocab = set()
    for s in df["tags"]:
        vocab |= set(ast.literal_eval(s).keys())
    n_g = len({g for s in df["genres"] for g in ast.literal_eval(s)})
    n_c = len({c for s in df["categories"] for c in ast.literal_eval(s)})
    print(f"\n  vocab: {n_g} genres + {n_c} categories + {len(vocab)} tags")
    print(f"  => content_dim will be about {n_g + n_c + len(vocab) + 6}")

    print("\n  type breakdown:")
    for t, n in df["type"].value_counts().head(8).items():
        print(f"    {t:12s} {n:,}")

    if os.path.exists(args.user_csv):
        print("\n--- coverage against interactions ---")
        u = pd.read_csv(args.user_csv)
        good = set(df.loc[df["has_features"] == 1, "appid"])
        hit = u[args.column].isin(good)
        print(f"  interactions w/ features: {hit.mean():.3f}   (was 0.652)")
        print(f"  distinct games covered:   {u.loc[hit, args.column].nunique():,}"
              f" / {u[args.column].nunique():,}")

        missing = set(u[args.column]) - good
        if missing:
            lost = u[args.column].isin(missing).sum()
            print(f"  still missing: {len(missing):,} games, {lost:,} interactions"
                  f" ({lost / len(u):.1%})")
            print("  (delisted appids are unrecoverable - that's your floor)")
    else:
        print(f"\n  ! {args.user_csv} not found - skipped coverage check")


if __name__ == "__main__":
    main()
