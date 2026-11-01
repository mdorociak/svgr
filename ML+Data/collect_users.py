import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import date

API = "https://api.steampowered.com"
UA = "Mozilla/5.0 (compatible; recsys-research/1.0)"

STEAMID64_BASE = 76561197960265728

DAILY_CALL_CAP = 100_000

CSV_HEADER = ["steamid", "game_id", "game_name", "playtime_hours"]

class Budget:

    def __init__(self, path, cap):
        self.path, self.cap = path, cap
        self.day, self.used = str(date.today()), 0
        if os.path.exists(path):
            try:
                with open(path) as f:
                    d = json.load(f)
                if d.get("day") == self.day:
                    self.used = int(d.get("used", 0))
            except Exception:
                pass

    def spend(self, n=1):
        self.used += n
        if self.used % 50 == 0:
            self.save()

    def left(self):
        return self.cap - self.used

    def save(self):
        with open(self.path, "w") as f:
            json.dump({"day": self.day, "used": self.used}, f)


def api_get(path, params, budget, timeout=15, max_tries=4):

    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    backoff = 20
    for attempt in range(max_tries):
        budget.spend()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", errors="replace")), None
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return None, "forbidden"   
            if e.code == 429:
                print(f"    429 - sleeping {backoff}s", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 600)
                continue
            if 500 <= e.code < 600:
                time.sleep(3 * (attempt + 1))
                continue
            return None, f"http_{e.code}"
        except Exception as e:
            if attempt == max_tries - 1:
                return None, type(e).__name__
            time.sleep(3 * (attempt + 1))
    return None, "exhausted"


def get_owned_games(steamid, key, budget):
    payload, err = api_get("/IPlayerService/GetOwnedGames/v1/", {
        "key": key, "steamid": steamid,
        "include_appinfo": 1, "include_played_free_games": 1,
    }, budget)
    if err:
        return None, ("private" if err == "forbidden" else err)

    resp = (payload or {}).get("response")
    if not isinstance(resp, dict) or not resp:
        return None, "private" 
    games = resp.get("games")
    if games is None:
        return None, "empty" 
    return games, "ok"


def get_friends(steamid, key, budget):
    payload, err = api_get("/ISteamUser/GetFriendList/v1/", {
        "key": key, "steamid": steamid, "relationship": "friend",
    }, budget)
    if err:
        return []
    friends = (payload or {}).get("friendslist", {}).get("friends", [])
    out = []
    for f in friends:
        try:
            out.append(int(f["steamid"]))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def load_visited(path):
    """steamid -> status, for every account already looked at."""
    visited = {}
    if not os.path.exists(path):
        return visited
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
                visited[int(rec["id"])] = rec["s"]
            except Exception:
                continue    
    return visited

FINAL = {"ok", "private", "empty", "too_few", "too_many"}


def load_queue(path, seeds):
    if os.path.exists(path):
        try:
            with open(path) as f:
                q = json.load(f)
            if q:
                return deque(int(x) for x in q)
        except Exception:
            pass
    return deque(seeds)


def random_steamids(n, observed, rng):
    if len(observed) >= 2:
        lo, hi = min(observed) - STEAMID64_BASE, max(observed) - STEAMID64_BASE
        lo, hi = max(lo, 1), max(hi, 2)
    else:
        lo, hi = 1, 1_500_000_000
    return [STEAMID64_BASE + rng.randrange(lo, hi + 1) for _ in range(n)]


# ---------------------------------------------------------------------- run

def collect(args, key):
    rng = random.Random()
    budget = Budget(args.budget_file, args.daily_cap)
    visited = load_visited(args.visited)
    collected = {sid for sid, st in visited.items() if st == "ok"}
    queue = load_queue(args.queue, args.seeds)

    retry = [sid for sid, st in visited.items() if st not in FINAL]
    if retry:
        queue.extendleft(retry)
        print(f"Retrying {len(retry):,} accounts that failed transiently")

    print(f"Collected so far : {len(collected):,} users")
    print(f"Already visited  : {len(visited):,} accounts "
          f"({sum(1 for s in visited.values() if s == 'private'):,} private)")
    print(f"Queue            : {len(queue):,}")
    print(f"API calls today  : {budget.used:,} of {budget.cap:,}\n")

    if not os.path.exists(args.out):
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADER)

    vis_f = open(args.visited, "a", buffering=1)
    out_f = open(args.out, "a", newline="", encoding="utf-8")
    writer = csv.writer(out_f)

    def mark(sid, status):
        visited[sid] = status
        vis_f.write(json.dumps({"id": sid, "s": status}) + "\n")

    counts = {}
    rows = 0
    started = time.time()

    try:
        while len(collected) < args.target:
            if budget.left() <= 10:
                print(f"\nDaily cap of {budget.cap:,} calls reached. "
                      f"Rerun tomorrow to continue.")
                break

            if not queue:
                print("Queue empty - refilling...")
                for uid in rng.sample(sorted(collected), min(10, len(collected))) if collected else []:
                    queue.extend(f for f in get_friends(uid, key, budget)
                                 if visited.get(f) not in FINAL)
                    time.sleep(args.delay)
                queue.extend(random_steamids(200, collected, rng))
                if not queue:
                    print("Nothing left to crawl.")
                    break

            sid = queue.popleft()
            if visited.get(sid) in FINAL:
                continue

            games, status = get_owned_games(sid, key, budget)
            time.sleep(args.delay)

            if status != "ok":
                mark(sid, status)
                counts[status] = counts.get(status, 0) + 1
                continue

            n = len(games)
            if n < args.min_games:
                mark(sid, "too_few")
                counts["too_few"] = counts.get("too_few", 0) + 1
                continue
            if n > args.max_games:
                mark(sid, "too_many")  
                counts["too_many"] = counts.get("too_many", 0) + 1
                continue

            for g in games:
                writer.writerow([sid, g.get("appid", 0), g.get("name", "Unknown"),
                                 round(g.get("playtime_forever", 0) / 60, 2)])
            out_f.flush()
            mark(sid, "ok")
            collected.add(sid)
            rows += n

            if len(collected) % 25 == 0:
                rate = len(collected) / max(time.time() - started, 1e-9)
                print(f"[{len(collected):,}/{args.target:,}] {rows:,} rows | "
                      f"queue {len(queue):,} | calls {budget.used:,} | "
                      f"{rate * 3600:.0f} users/h", flush=True)

            if len(queue) < args.queue_low:
                new = [f for f in get_friends(sid, key, budget)
                       if visited.get(f) not in FINAL]
                time.sleep(args.delay)
                rng.shuffle(new)
                queue.extend(new)
                if args.random_frac > 0:
                    queue.extend(random_steamids(
                        max(1, int(len(new) * args.random_frac)), collected, rng))

            if len(collected) % 200 == 0:
                with open(args.queue, "w") as f:
                    json.dump(list(queue), f)

    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        with open(args.queue, "w") as f:
            json.dump(list(queue), f)
        budget.save()
        vis_f.close()
        out_f.close()

    print(f"\nUsers {len(collected):,} | rows added this run {rows:,} | "
          f"calls used today {budget.used:,}")
    if counts:
        print("skipped: " + ", ".join(f"{k}={v:,}" for k, v in sorted(counts.items())))
    print(f"-> {args.out}   (rerun the same command to continue)")

def stats(args):
    if not os.path.exists(args.out):
        print(f"{args.out} not found.")
        return
    import collections
    per_user = collections.Counter()
    per_game = collections.Counter()
    names = {}
    total = 0
    with open(args.out, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            per_user[row["steamid"]] += 1
            per_game[row["game_id"]] += 1
            names.setdefault(row["game_id"], row["game_name"])
            total += 1

    sizes = sorted(per_user.values())
    print(f"users {len(per_user):,} | rows {total:,} | games {len(per_game):,}")
    print(f"games per user: median {sizes[len(sizes) // 2]}, "
          f"mean {sum(sizes) / len(sizes):.1f}, max {sizes[-1]}")

    for bar in (5, 10, 20):
        n = sum(1 for c in per_game.values() if c >= bar)
        print(f"games with >= {bar:>2} owners: {n:,} of {len(per_game):,} "
              f"({n / len(per_game):.1%})")

    print("\nmost owned:")
    for gid, c in per_game.most_common(10):
        print(f"  {c:>6,}  {names[gid][:50]}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", type=int, default=40000)
    p.add_argument("--out", default="steam_users_games.csv")
    p.add_argument("--visited", default="visited.jsonl")
    p.add_argument("--queue", default="queue.json")
    p.add_argument("--budget-file", default="api_budget.json")
    p.add_argument("--daily-cap", type=int, default=DAILY_CALL_CAP)
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--min-games", type=int, default=5)
    p.add_argument("--max-games", type=int, default=5000)
    p.add_argument("--queue-low", type=int, default=5000,
                   help="fetch friend lists only when the frontier drops below this")
    p.add_argument("--random-frac", type=float, default=0.15,
                   help="random Steam IDs added per friend batch, as a fraction; "
                        "0 = pure friends-of-friends (fast, one social cluster)")
    p.add_argument("--seeds", type=int, nargs="*", default=[
        76561198006409530, 76561198040894045, 76561197960435530,
        76561197979669175, 76561198029481460,
    ])
    p.add_argument("--stats", action="store_true")
    args = p.parse_args()

    if args.stats:
        stats(args)
        return

    key = os.environ.get("STEAM_API_KEY", "").strip()
    if not key:
        print("Set STEAM_API_KEY first:\n"
              "  Windows cmd : set STEAM_API_KEY=xxxxx\n"
              "  PowerShell  : $env:STEAM_API_KEY=\"xxxxx\"\n"
              "  bash        : export STEAM_API_KEY=xxxxx\n"
              "Get a key at https://steamcommunity.com/dev/apikey")
        sys.exit(1)

    collect(args, key)


if __name__ == "__main__":
    main()
