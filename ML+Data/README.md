# Recommendation model

A hybrid recommender for Steam games, built for the cold-start case: ranking
games for a user the model has never seen, using only the library they already
own. It combines collaborative filtering with content features (genres,
categories, tags, review counts, price) in a single PyTorch network.

## Results

Held-out users, never seen in training. For each, 80% of their library is the
input profile and the remaining 20% are the targets, ranked against the full
catalogue of 17,430 games.

| | NDCG@10 | Recall@10 | Hit@10 |
| --- | --- | --- | --- |
| **ProfileNeuMF** | **0.312** | **0.281** | **0.846** |
| Most-popular baseline | 0.250 | 0.221 | 0.800 |

Split by whether a target game has its own embedding (games with fewer than
10 owners share one slot, so only content features can tell them apart):

| Per-target Hit@10 (99 sampled negatives) | games with own embedding | long-tail games |
| --- | --- | --- |
| ProfileNeuMF | 0.925 | 0.334 |
| Most-popular baseline | 0.920 | 0.002 |

## Data

| | |
| --- | --- |
| Users | 5,406, collected through the Steam Web API |
| Library records | 850,658 with playtime → 553,538 after cleaning and a ≥2 h playtime filter |
| Games | 17,430 after filtering; content features for 24,630 |
| Content features | 561: 32 genres, 68 categories, 454 tags, 6 numeric, 1 availability flag |
| Split | 3,783 / 810 / 812 users (train / val / test), split before any sampling |

Users were found by crawling friends lists from five seed accounts, so the
sample is one social network rather than a random sample of Steam. That skews
popularity: 72% of games have fewer than 10 owners in the data.

The raw interaction files contain Steam IDs and are not included in this
repository. The scripts below rebuild them.

## Pipeline

All scripts run from this folder. Python dependencies: `pip install -r requirements.txt`.

```bash
# 1. User libraries (needs a Steam Web API key; resumable, respects the daily call cap)
export STEAM_API_KEY=...            # Windows: set STEAM_API_KEY=...
python collect_users.py --target 40000 --out steam_users_games.csv

# 2. Game metadata from the Steam Store API and SteamSpy (resumable)
python scrape_steam.py appids --user-csv steam_users_games.csv
python scrape_steam.py steamspy
python scrape_steam.py steam

# 3. Merge into one feature file -> game_features_v2.csv
python build_features.py --user-csv steam_users_games.csv

# 4. Drop non-games, cap idle-farmed playtime, add per-game playtime percentiles
python clean_interactions.py --interactions steam_users_games.csv --write --keep-idlers

# 5. Train and evaluate -> profile_neumf.pkl
python train.py
```

The backend loads `profile_neumf.pkl` from its working directory, or from the
path in the `MODEL_PATH` environment variable.

## Model

`model.py` is shared by training and the backend
(`backend/app/services/model.py` is an identical copy — keep them in sync).

A user is represented as the mean of embeddings of the games they have played,
both in training and at serving time, so there is no per-user parameter that
the service cannot reproduce. During training, the game being scored is left
out of its own user's profile. The score combines three branches — a
generalised matrix factorisation term, a content term, and an MLP over the
user, game and content vectors — through one output layer.

Training uses binary cross-entropy with two negatives per positive, sampled in
proportion to popularity^0.5. The checkpoint is chosen by cold-start NDCG@10 on
validation users.

## What was tried

Full-catalogue NDCG@10 on test users. The label changed partway through
(owned → played at least 2 hours), which changes the task, so compare each row
with its own baseline rather than with rows above it.

| Experiment | Label | Model | Most-popular |
| --- | --- | --- | --- |
| Per-user embedding table (original design) | owned | 0.268 | 0.284 |
| User = mean of owned games (current design) | owned | 0.359 | 0.284 |
| Wider content network, [128, 64] → [256, 128] | owned | 0.348 | 0.284 |
| Label = played ≥2 h, non-games removed | played | **0.312** | 0.250 |
| Content coverage 65% instead of 100% | played | 0.319 | 0.251 |
| Minimum owners 5 instead of 10 | played | 0.310 | 0.250 |
| Rebalanced long-tail negatives | played | 0.278 | 0.250 |

Rebalancing the negatives raised the long-tail share of top-10 lists from 0.2%
to 18.2% at the cost of accuracy; the current model keeps the accuracy.

## Known limitations

- Long-tail games almost never reach a top-10 list (0.2% of recommendations).
- The friends-of-friends sample over-represents one community's tastes.
- Training is pointwise while evaluation is a ranking; a pairwise or
  sampled-softmax loss would align the two.
