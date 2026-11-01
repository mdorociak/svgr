import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

STEAM_URL = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=english"
STEAMSPY_URL = "https://steamspy.com/api.php?request=appdetails&appid={appid}"

DELAY = {"steam": 1.6, "steamspy": 1.1}
URL = {"steam": STEAM_URL, "steamspy": STEAMSPY_URL}

UA = "Mozilla/5.0 (compatible; recsys-research/1.0)"


def cmd_appids(args):
    import pandas as pd

    df = pd.read_csv(args.user_csv)
    ids = sorted(int(x) for x in df[args.column].dropna().unique())
    with open(args.out, "w") as f:
        f.write("\n".join(str(i) for i in ids))
    print(f"{len(ids):,} distinct appids -> {args.out}")


def load_appids(path):
    with open(path) as f:
        return [int(line) for line in f if line.strip()]


FINAL_REASONS = {"delisted_or_unknown", "not_in_steamspy",
                 "http_400", "http_404", "http_410"}


def is_final(rec):
    return bool(rec.get("ok")) or rec.get("reason") in FINAL_REASONS


def load_done(path, retry_all_failed=False):
    done, failed = set(), set()
    if not os.path.exists(path):
        return done, 0
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue 
            final = rec.get("ok") if retry_all_failed else is_final(rec)
            (done if final else failed).add(rec["appid"])
    return done, len(failed - done)


def ensure_trailing_newline(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        last = f.read(1)
    if last != b"\n":
        with open(path, "ab") as f:
            f.write(b"\n")


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def fetch_with_retry(url, max_tries=5):
    backoff = 30
    for attempt in range(max_tries):
        try:
            return fetch(url), None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    429 - sleeping {backoff}s", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 600)
                continue
            if 500 <= e.code < 600:
                time.sleep(5 * (attempt + 1))
                continue
            return None, f"http_{e.code}"
        except Exception as e:
            if attempt == max_tries - 1:
                return None, type(e).__name__
            time.sleep(5 * (attempt + 1))
    return None, "exhausted"


def parse_steam(appid, payload):
    if not isinstance(payload, dict) or str(appid) not in payload:
        return {"appid": appid, "ok": False, "reason": "empty_response"}
    entry = payload[str(appid)] or {}
    if not entry.get("success"):
        return {"appid": appid, "ok": False, "reason": "delisted_or_unknown"}
    d = entry.get("data") or {}
    return {
        "appid": appid,
        "ok": True,
        "type": d.get("type"),
        "name": d.get("name"),
        "genres": [g.get("description") for g in (d.get("genres") or [])],
        "categories": [c.get("description") for c in (d.get("categories") or [])],
        "required_age": d.get("required_age"),
        "is_free": d.get("is_free"),
        "price_cents": (d.get("price_overview") or {}).get("final"),
        "release_date": (d.get("release_date") or {}).get("date"),
        "fullgame": (d.get("fullgame") or {}).get("appid"),
    }


def parse_steamspy(appid, payload):
    if not isinstance(payload, dict) or not payload:
        return {"appid": appid, "ok": False, "reason": "empty_response"}
    d = payload
    if not d.get("name"):
        return {"appid": appid, "ok": False, "reason": "not_in_steamspy"}
    return {
        "appid": appid,
        "ok": True,
        "name": d.get("name"),
        "positive": d.get("positive"),
        "negative": d.get("negative"),
        "tags": d.get("tags") if isinstance(d.get("tags"), dict) else {},
        "genre": d.get("genre"),
        "price_cents": d.get("price"),
        "owners": d.get("owners"),
        "developer": d.get("developer"),
    }


PARSE = {"steam": parse_steam, "steamspy": parse_steamspy}


def cmd_scrape(args):
    source = args.source
    out = args.out or f"{source}_raw.jsonl"
    delay = args.delay if args.delay is not None else DELAY[source]

    appids = load_appids(args.appids)
    done, retrying = load_done(out, args.retry_all_failed)
    todo = [a for a in appids if a not in done]

    print(f"[{source}] {len(appids):,} total, {len(done):,} done, {len(todo):,} to go"
          + (f" (incl. {retrying:,} earlier failures to retry)" if retrying else ""))
    if todo:
        eta_h = len(todo) * delay / 3600
        print(f"[{source}] ~{eta_h:.1f}h at {delay}s/request")
    if not todo:
        return

    ok = final_fail = transient = streak = 0
    started = time.time()
    ensure_trailing_newline(out)

    with open(out, "a", buffering=1) as f:
        for i, appid in enumerate(todo, 1):
            payload, err = fetch_with_retry(URL[source].format(appid=appid))

            if err:
                rec = {"appid": appid, "ok": False, "reason": err}
            else:
                rec = PARSE[source](appid, payload)

            f.write(json.dumps(rec) + "\n")
            if rec.get("ok"):
                ok += 1
            elif is_final(rec):
                final_fail += 1
            else:
                transient += 1

            streak = 0 if is_final(rec) else streak + 1
            if streak and streak % 10 == 0:
                print(f"[{source}] {streak} temporary failures in a row "
                      f"(connection down or rate limited?) - pausing 5 min", flush=True)
                time.sleep(300)

            if i % 100 == 0 or i == len(todo):
                rate = i / max(time.time() - started, 1e-9)
                remain = (len(todo) - i) / max(rate, 1e-9) / 3600
                print(
                    f"[{source}] {i:,}/{len(todo):,}  ok={ok:,} gone={final_fail:,} "
                    f"retry-later={transient:,}  "
                    f"{remain:.1f}h left",
                    flush=True,
                )

            time.sleep(delay + random.uniform(0, 0.3))

    print(f"[{source}] finished: {ok:,} ok, {final_fail:,} gone for good, "
          f"{transient:,} temporary failures -> {out}")
    if transient:
        print(f"[{source}] run the same command again to retry those {transient:,}")



def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("appids", help="write appids.txt from the interaction CSV")
    a.add_argument("--user-csv", default="steam_users_games_processed.csv")
    a.add_argument("--column", default="game_id")
    a.add_argument("--out", default="appids.txt")
    a.set_defaults(func=cmd_appids)

    for src in ("steam", "steamspy"):
        s = sub.add_parser(src, help=f"scrape {src}")
        s.add_argument("--appids", default="appids.txt")
        s.add_argument("--out", default=None)
        s.add_argument("--delay", type=float, default=None)
        s.add_argument("--retry-all-failed", action="store_true",
                       help="also retry failures normally treated as final (e.g. 'delisted')")
        s.set_defaults(func=cmd_scrape, source=src)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted - rerun the same command to resume")
        sys.exit(130)
