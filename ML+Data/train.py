
import copy
import pickle
import time
from collections import namedtuple
from types import SimpleNamespace

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score

from model import ProfileNeuMF, HybridNeuMF, ContentProcessor, TAIL_IDX


CFG = dict(
    user_csv='steam_users_games_clean.csv',
    min_playtime=2.0,
    min_playtime_pct=0.0,
    game_csv='game_features_v2.csv',
    out_path='profile_neumf.pkl',
    seed=42,
    arch='profile',

    split=(0.70, 0.15, 0.15),
    min_owners=10,
    neg_ratio=2,
    neg_alpha=0.5,
    balance_tail_negatives=False,

    warm_holdout=0.02,

    profile_frac=0.8,
    min_games=5,
    eval_negatives=99,
    val_max_users=5000,

    use_content=True,
    mf_dim=16,
    mlp_dims=[64, 32, 16],
    content_hidden_dims=[128, 64],

    lr=3e-4,
    weight_decay=1e-4,
    batch_size=512,
    epochs=80,
    patience=10,
    lr_patience=5,
)


def lookup(mapping, keys, default):
    return pd.Series(keys).map(mapping).fillna(default).astype(np.int64).to_numpy()


def load_interactions(path, min_playtime=0.0, min_playtime_pct=0.0):
    have = pd.read_csv(path, nrows=0).columns
    cols = ['steamid', 'game_id'] + [c for c in ('playtime_hours', 'playtime_pct') if c in have]
    df = pd.read_csv(path, usecols=cols)
    before = len(df)
    df = df.dropna(subset=['steamid', 'game_id']).drop_duplicates(subset=['steamid', 'game_id'])
    df['game_id'] = df['game_id'].astype(np.int64)

    if min_playtime > 0 or min_playtime_pct > 0:
        keep = pd.Series(True, index=df.index)
        if min_playtime > 0:
            if 'playtime_hours' not in df.columns:
                raise ValueError("min_playtime set but the CSV has no playtime_hours column")
            keep &= df['playtime_hours'].fillna(0) >= min_playtime
        if min_playtime_pct > 0:
            if 'playtime_pct' not in df.columns:
                raise ValueError("min_playtime_pct set but the CSV has no playtime_pct column "
                                 "- run clean_interactions.py --write first")
            keep &= df['playtime_pct'].isna() | (df['playtime_pct'] >= min_playtime_pct)
        kept = df[keep]
        print(f"Played filter (>= {min_playtime}h, >= {min_playtime_pct:.0%} of owners): "
              f"kept {len(kept):,} of {len(df):,} ({len(kept) / len(df):.1%}); "
              f"median hours kept {kept['playtime_hours'].median():.1f}")
        df = kept
    df = df.reset_index(drop=True)

    print(f"Interactions: {len(df):,} ({before - len(df):,} dropped), "
          f"{df['steamid'].nunique():,} users, {df['game_id'].nunique():,} games")
    return df


def split_users(inter, fractions, rng):
    users = inter['steamid'].unique()
    users = users[rng.permutation(len(users))]
    n_train = int(len(users) * fractions[0])
    n_val = int(len(users) * fractions[1])
    return (set(users[:n_train]),
            set(users[n_train:n_train + n_val]),
            set(users[n_train + n_val:]))


def build_content(game_csv, use_content=True):
    game_df = pd.read_csv(game_csv)
    processor = ContentProcessor()
    game_to_features, content_dim = processor.fit_transform(game_df)
    game_ids = list(game_to_features)
    matrix = np.zeros((len(game_ids) + 1, content_dim), dtype=np.float32)
    if game_ids:
        matrix[1:] = np.stack([game_to_features[g] for g in game_ids])
    game_to_row = {g: r for r, g in enumerate(game_ids, start=1)}
    if not use_content:
        matrix[:] = 0.0
        print(f"Content features: ABLATED (use_content=False). The content tower still "
              f"runs, on a constant input, so it contributes a bias and nothing else.")
    print(f"Content features: {len(game_ids):,} games, content_dim={content_dim}")
    if content_dim < 500:
        print(f"  !! content_dim={content_dim} looks like the old 2019 features file. "
              f"Check game_csv.")
    return processor, game_to_features, content_dim, torch.from_numpy(matrix), game_to_row


def sample_negatives(owned_by_user, pool, probs, ratio, rng):
    cdf = np.cumsum(probs)
    cdf[-1] = 1.0
    neg_users, neg_games = [], []
    for uidx, owned in owned_by_user.items():
        need = len(owned) * ratio
        got, have = [], 0
        for _ in range(20):                       # nearly always done in one round
            draw = pool[np.searchsorted(cdf, rng.random(int(need * 1.3) + 8), side='right')]
            draw = draw[~np.isin(draw, owned)]
            got.append(draw)
            have += len(draw)
            if have >= need:
                break
        got = np.concatenate(got)[:need]
        neg_users.append(np.full(len(got), uidx, dtype=np.int64))
        neg_games.append(got)
    return np.concatenate(neg_users), np.concatenate(neg_games)


def build_training_samples(train_inter, game_to_row, feat_matrix, cfg, rng, device):
    owners = train_inter.groupby('game_id').size()

    core = sorted(owners[owners >= cfg['min_owners']].index)
    item_to_idx = {g: i for i, g in enumerate(core, start=1)}   # slot 0 = TAIL_IDX
    print(f"Collaborative core: {len(core):,} of {len(owners):,} train games "
          f"(>= {cfg['min_owners']} owners); the rest share the tail slot")

    users = train_inter['steamid'].unique()
    user_to_idx = {u: i for i, u in enumerate(users)}

    pos_u = train_inter['steamid'].map(user_to_idx).to_numpy()
    pos_g = train_inter['game_id'].to_numpy()

    covered = np.isin(pos_g, np.fromiter(game_to_row.keys(), dtype=np.int64))
    print(f"Train interactions with content features: {covered.mean():.3f} "
          f"({(~covered).sum():,} get the unknown-game vector)")
    if covered.mean() < 0.90:
        print(f"  !! only {covered.mean():.1%} of interactions have content features. "
              f"The content branch is running on constants for the rest - check game_csv.")

    pool = owners.index.to_numpy()
    probs = owners.to_numpy().astype(np.float64) ** cfg['neg_alpha']
    probs /= probs.sum()

    if cfg['balance_tail_negatives']:
        pool_tail = lookup(item_to_idx, pool, TAIL_IDX) == TAIL_IDX
        want = float(np.mean(lookup(item_to_idx, pos_g, TAIL_IDX) == TAIL_IDX))
        if pool_tail.any() and not pool_tail.all():
            was = probs[pool_tail].sum()
            probs[pool_tail] *= want / max(was, 1e-12)
            probs[~pool_tail] *= (1.0 - want) / max(1.0 - was, 1e-12)
            probs /= probs.sum()
            print(f"Negative sampling rebalanced: tail mass {was:.1%} -> {want:.1%}, "
                  f"matching its share of positives")
    owned_by_user = (pd.DataFrame({'u': pos_u, 'g': pos_g})
                     .groupby('u')['g'].apply(np.asarray).to_dict())
    t0 = time.time()
    neg_u, neg_g = sample_negatives(owned_by_user, pool, probs, cfg['neg_ratio'], rng)
    print(f"Negatives: {len(neg_g):,} for {len(pos_g):,} positives "
          f"(alpha={cfg['neg_alpha']}, {time.time() - t0:.1f}s)")

    tail_pos = np.mean(lookup(item_to_idx, pos_g, TAIL_IDX) == TAIL_IDX)
    tail_neg = np.mean(lookup(item_to_idx, neg_g, TAIL_IDX) == TAIL_IDX)
    print(f"Tail slot share: {tail_pos:.3f} of positives, {tail_neg:.3f} of negatives")

    games = np.concatenate([pos_g, neg_g])
    labels = np.concatenate([np.ones(len(pos_g)), np.zeros(len(neg_g))]).astype(np.float32)
    n = len(labels)
    holdout = rng.random(n) < cfg['warm_holdout']

    t = lambda a, dt=torch.long: torch.tensor(np.asarray(a), dtype=dt, device=device)
    data = SimpleNamespace(
        users=t(np.concatenate([pos_u, neg_u])),
        items=t(lookup(item_to_idx, games, TAIL_IDX)),
        rows=t(lookup(game_to_row, games, 0)),
        labels=t(labels, torch.float32),
        feats=feat_matrix.to(device),
        train_idx=t(np.flatnonzero(~holdout)),
        warm_idx=t(np.flatnonzero(holdout)),
        pos_weight=len(neg_g) / max(len(pos_g), 1),
        is_pos=t(labels > 0.5, torch.bool),
    )

    pos_items = lookup(item_to_idx, pos_g, TAIL_IDX)
    keep = pos_items != TAIL_IDX
    order = np.argsort(pos_u[keep], kind='stable')
    lengths = np.bincount(pos_u[keep], minlength=len(user_to_idx))
    data.profile = (pos_items[keep][order], np.cumsum(lengths) - lengths, lengths)
    print(f"Profiles: {lengths.mean():.1f} core games per train user "
          f"(median {int(np.median(lengths))}, {np.mean(lengths == 0):.1%} with none)")

    flat, offs, _ = data.profile
    probe = rng.choice(len(labels), min(2000, len(labels)), replace=False)
    u_np, i_np, p_np = pos_u, pos_items, None
    for r in probe:
        u = int(data.users[r]); it = int(data.items[r])
        bag = flat[offs[u]:offs[u] + lengths[u]]
        if labels[r] > 0.5 and it != TAIL_IDX:
            assert it in bag, f"positive row {r}: target {it} missing from user {u}'s profile"
        elif labels[r] < 0.5:
            assert it not in bag, f"negative row {r}: target {it} is owned by user {u}"

    return data, user_to_idx, item_to_idx, owners.to_dict()


EvalUser = namedtuple('EvalUser', 'profile_ids profile_pos target_pos negatives')


class ColdStartEvaluator:

    def __init__(self, user_games, universe, item_to_idx, game_to_row, feat_matrix,
                 profile_frac=0.8, min_games=5, n_neg=99, max_users=None, seed=0):
        rng = np.random.default_rng(seed)
        self.universe = np.asarray(universe, dtype=np.int64)
        self.item_to_idx = item_to_idx
        self.item_idx = torch.tensor(lookup(item_to_idx, self.universe, TAIL_IDX))
        self.is_tail = self.item_idx.numpy() == TAIL_IDX
        self.feats = feat_matrix[torch.tensor(lookup(game_to_row, self.universe, 0))]
        pos_of = {g: i for i, g in enumerate(self.universe)}
        n_items = len(self.universe)

        users = sorted(user_games)
        users = [users[i] for i in rng.permutation(len(users))]

        self.records = []
        for u in users:
            games = [g for g in dict.fromkeys(user_games[u]) if g in pos_of]
            if len(games) < min_games:
                continue
            games = [games[i] for i in rng.permutation(len(games))]
            n_prof = min(max(1, round(len(games) * profile_frac)), len(games) - 1)
            profile, targets = games[:n_prof], games[n_prof:]
            owned_pos = np.array([pos_of[g] for g in games])

            need = len(targets) * n_neg
            cand = np.empty(0, dtype=np.int64)
            while len(cand) < need:
                draw = rng.integers(0, n_items, size=need * 2 + 16)
                cand = np.concatenate([cand, draw[~np.isin(draw, owned_pos)]])

            self.records.append(EvalUser(
                profile_ids=profile,
                profile_pos=np.array([pos_of[g] for g in profile]),
                target_pos=np.array([pos_of[g] for g in targets]),
                negatives=cand[:need].reshape(len(targets), n_neg),
            ))
            if max_users and len(self.records) >= max_users:
                break

    @torch.no_grad()
    def evaluate(self, model, mode='sampled', k=10):
        model.eval()
        dev = model._device()
        cache = model.item_cache(self.item_idx.to(dev), self.feats.to(dev))

        def scorer(rec, positions):
            gmf, mlp, fallback = model.cold_user(rec.profile_ids, self.item_to_idx)
            return model.score_cached(gmf, mlp, cache, positions).cpu().numpy(), fallback

        return self._run(scorer, mode, k)

    def evaluate_popularity(self, counts, mode='sampled', k=10):
        pop = np.array([counts.get(g, 0) for g in self.universe], dtype=np.float64)
        return self._run(lambda rec, pos: (pop if pos is None else pop[pos], False), mode, k)

    def _run(self, scorer, mode, k):
        hits, ndcgs, recalls, fallbacks = [], [], [], []
        ranks, rank_tail, rec_tail = [], [], []
        discounts = 1.0 / np.log2(np.arange(2, k + 2))

        for rec in self.records:
            if mode == 'sampled':
                cand = np.concatenate([rec.target_pos[:, None], rec.negatives], axis=1)
                scores, fb = scorer(rec, cand.ravel())
                scores = scores.reshape(cand.shape)
                rank = (scores[:, 1:] >= scores[:, :1]).sum(axis=1)
                hits.append(np.mean(rank < k))
                ndcgs.append(np.mean(np.where(rank < k, 1.0 / np.log2(rank + 2), 0.0)))
                ranks.append(rank)
                rank_tail.append(self.is_tail[rec.target_pos])
            else:
                scores, fb = scorer(rec, None)
                scores = scores.astype(np.float64)                    # copy
                scores[rec.profile_pos] = -np.inf
                kk = min(k, len(scores) - 1)
                top = np.argpartition(-scores, kk - 1)[:kk]
                top = top[np.argsort(-scores[top])]
                rel = np.isin(top, rec.target_pos)
                n_rel = min(kk, len(rec.target_pos))
                hits.append(float(rel.any()))
                recalls.append(rel.sum() / n_rel)
                ndcgs.append((rel * discounts[:kk]).sum() / discounts[:n_rel].sum())
                rec_tail.append(self.is_tail[top].mean())
            fallbacks.append(fb)

        fallbacks = np.array(fallbacks, dtype=bool)
        out = {'users': len(self.records),
               f'hit@{k}': float(np.mean(hits)) if hits else 0.0,
               f'ndcg@{k}': float(np.mean(ndcgs)) if ndcgs else 0.0,
               'fallback_frac': float(fallbacks.mean()) if len(fallbacks) else 0.0}
        if recalls:
            out[f'recall@{k}'] = float(np.mean(recalls))
        if fallbacks.any():
            out[f'fallback_hit@{k}'] = float(np.mean(np.array(hits)[fallbacks]))

        if ranks:
            r = np.concatenate(ranks)
            t = np.concatenate(rank_tail)
            out['targets'] = int(len(r))
            out['tail_target_frac'] = float(t.mean())
            if (~t).any():
                out[f'core_hit@{k}'] = float(np.mean(r[~t] < k))
            if t.any():
                out[f'tail_hit@{k}'] = float(np.mean(r[t] < k))
        if rec_tail:
            out['tail_in_recs'] = float(np.mean(rec_tail))
        return out


def make_optimizer(model, lr, weight_decay=1e-4):
    decay, no_decay = [], []
    for name, p in model.named_parameters():
        if p.requires_grad:
            (no_decay if 'embedding' in name else decay).append(p)
    return torch.optim.Adam([
        {'params': decay, 'weight_decay': weight_decay},
        {'params': no_decay, 'weight_decay': 0.0},
    ], lr=lr)


@torch.no_grad()
def warm_metrics(model, data, criterion, batch_size=8192):
    model.eval()
    idx = data.warm_idx
    if len(idx) == 0:
        return float('nan'), float('nan')
    outs, labels = [], []
    for s in range(0, len(idx), batch_size):
        b = idx[s:s + batch_size]
        outs.append(model(data.users[b], data.items[b], data.feats[data.rows[b]],
                          data.is_pos[b]))
        labels.append(data.labels[b])
    outs, labels = torch.cat(outs), torch.cat(labels)
    return criterion(outs, labels).item(), roc_auc_score(labels.cpu().numpy(), outs.cpu().numpy())


def train_model(model, data, val_eval, cfg, device):
    model.to(device)
    optimizer = make_optimizer(model, cfg['lr'], cfg['weight_decay'])

    if model.use_logits:
        criterion = nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor([data.pos_weight], device=device))
    else:
        criterion = nn.BCELoss()

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=cfg['lr_patience'], min_lr=1e-6)

    history = {k: [] for k in ('train_loss', 'warm_loss', 'warm_auc',
                               'cold_ndcg@10', 'cold_hit@10', 'fallback_frac', 'lr')}
    best_score, best_state, best_epoch, stale = -1.0, None, 0, 0
    bs = cfg['batch_size']

    try:
        for epoch in range(1, cfg['epochs'] + 1):
            t0 = time.time()
            lr = optimizer.param_groups[0]['lr']

            model.train()
            perm = data.train_idx[torch.randperm(len(data.train_idx), device=device)]
            total, batches = 0.0, 0
            for s in range(0, len(perm) - bs + 1, bs):
                b = perm[s:s + bs]
                optimizer.zero_grad()
                out = model(data.users[b], data.items[b], data.feats[data.rows[b]],
                            data.is_pos[b])
                loss = criterion(out, data.labels[b])
                loss.backward()
                optimizer.step()
                total += loss.item()
                batches += 1

            warm_loss, warm_auc = warm_metrics(model, data, criterion)
            cold = val_eval.evaluate(model, 'sampled')
            score = cold['ndcg@10']
            scheduler.step(score)

            for key, val in (('train_loss', total / max(batches, 1)), ('warm_loss', warm_loss),
                             ('warm_auc', warm_auc), ('cold_ndcg@10', score),
                             ('cold_hit@10', cold['hit@10']),
                             ('fallback_frac', cold['fallback_frac']), ('lr', lr)):
                history[key].append(val)

            improved = score > best_score + 1e-4
            if improved:
                best_score, best_epoch, stale = score, epoch, 0
                best_state = copy.deepcopy(model.state_dict())
            else:
                stale += 1

            print(f"epoch {epoch:3d} | {time.time() - t0:5.1f}s | lr {lr:.1e} | "
                  f"train {history['train_loss'][-1]:.4f} | warm loss {warm_loss:.4f} auc {warm_auc:.4f} | "
                  f"cold ndcg@10 {score:.4f} hit@10 {cold['hit@10']:.4f}"
                  f"{'  *' if improved else ''}")

            if stale >= cfg['patience']:
                print(f"Early stop: no val improvement for {cfg['patience']} epochs.")
                break

    except KeyboardInterrupt:
        print("\nStopped by hand. Keeping the best epoch so far and finishing up...")
        n = min(len(v) for v in history.values())
        history = {k: v[:n] for k, v in history.items()}

    if best_state is None:
        raise SystemExit("Stopped before the first epoch finished - nothing to save.")
    model.load_state_dict(best_state)
    print(f"Restored best model from epoch {best_epoch} (val cold ndcg@10 {best_score:.4f})")
    return model, history, best_epoch

def save_package(path, model, processor, user_to_idx, item_to_idx, game_to_features,
                 history, test_results, cfg):
    package = {
        'model_state_dict': {k: v.cpu() for k, v in model.state_dict().items()},
        'model_config': model.config,
        'user_to_idx': user_to_idx,
        'item_to_idx': item_to_idx,
        'game_to_features': game_to_features,
        'content_processor': processor,
        'training_history': history,
        'test_results': test_results,
        'train_config': cfg,
        'model_class': type(model).__name__,
    }
    with open(path, 'wb') as f:
        pickle.dump(package, f)
    print(f"Saved -> {path}")


def load_hybrid_model(filepath):
    with open(filepath, 'rb') as f:
        package = pickle.load(f)
    cls = {'ProfileNeuMF': ProfileNeuMF}.get(package.get('model_class'), HybridNeuMF)
    model = cls(**package['model_config'])
    model.load_state_dict(package['model_state_dict'])
    model.eval()
    return model, package


def plot_history(history, baseline_ndcg, path='training_curves.png'):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available - skipping plot")
        return
    ep = range(1, len(history['train_loss']) + 1)
    fig, ax = plt.subplots(1, 3, figsize=(17, 4.5))
    ax[0].plot(ep, history['train_loss'], label='train')
    ax[0].plot(ep, history['warm_loss'], label='warm holdout')
    ax[0].set_title('Loss (warm path)')
    ax[1].plot(ep, history['warm_auc'])
    ax[1].set_title('Warm AUC (diagnostic)')
    ax[2].plot(ep, history['cold_ndcg@10'], label='NDCG@10')
    ax[2].plot(ep, history['cold_hit@10'], label='Hit@10')
    ax[2].axhline(baseline_ndcg, color='gray', ls='--', label='popularity NDCG@10')
    ax[2].set_title('Cold start, val users (selects the model)')
    for a in ax:
        a.set_xlabel('epoch')
        a.grid(alpha=0.3)
    ax[0].legend()
    ax[2].legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    print(f"Curves -> {path}")


def print_results(results, k=10):
    print(f"\n{'':28s}{'hit@'+str(k):>9s}{'ndcg@'+str(k):>10s}{'recall@'+str(k):>11s}")
    for name, r in results.items():
        rec = f"{r[f'recall@{k}']:.4f}" if f'recall@{k}' in r else '-'
        print(f"{name:28s}{r[f'hit@{k}']:9.4f}{r[f'ndcg@{k}']:10.4f}{rec:>11s}")

    rows = [(n, r) for n, r in results.items() if f'tail_hit@{k}' in r]
    if rows:
        print(f"\nPer-target hit@{k}, split by whether the game has its own embedding.")
        print(f"Tail games share one slot, so only the content branch can rank them.")
        print(f"\n{'':28s}{'core':>9s}{'tail':>10s}")
        for name, r in rows:
            print(f"{name:28s}{r[f'core_hit@{k}']:9.4f}{r[f'tail_hit@{k}']:10.4f}")
        print(f"\n  {rows[0][1]['tail_target_frac']:.1%} of targets are tail games.")

    rows = [(n, r) for n, r in results.items() if 'tail_in_recs' in r]
    if rows:
        print(f"\nShare of the top {k} that are tail games (catalogue reach):")
        for name, r in rows:
            print(f"  {name:30s}{r['tail_in_recs']:.1%}")


def main(cfg=CFG):
    rng = np.random.default_rng(cfg['seed'])
    torch.manual_seed(cfg['seed'])
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    inter = load_interactions(cfg['user_csv'], cfg['min_playtime'], cfg['min_playtime_pct'])
    train_users, val_users, test_users = split_users(inter, cfg['split'], rng)
    print(f"Users: {len(train_users):,} train / {len(val_users):,} val / {len(test_users):,} test")

    processor, game_to_features, content_dim, feat_matrix, game_to_row = build_content(
        cfg['game_csv'], cfg['use_content'])

    train_inter = inter[inter['steamid'].isin(train_users)]
    data, user_to_idx, item_to_idx, pop_counts = build_training_samples(
        train_inter, game_to_row, feat_matrix, cfg, rng, device)

    universe = np.union1d(inter['game_id'].unique(),
                          np.fromiter(game_to_features.keys(), dtype=np.int64))

    def games_of(users):
        sub = inter[inter['steamid'].isin(users)]
        return sub.groupby('steamid')['game_id'].apply(list).to_dict()

    common = dict(universe=universe, item_to_idx=item_to_idx, game_to_row=game_to_row,
                  feat_matrix=feat_matrix, profile_frac=cfg['profile_frac'],
                  min_games=cfg['min_games'], n_neg=cfg['eval_negatives'])
    val_eval = ColdStartEvaluator(games_of(val_users), max_users=cfg['val_max_users'],
                                  seed=cfg['seed'] + 1, **common)
    test_eval = ColdStartEvaluator(games_of(test_users), seed=cfg['seed'] + 2, **common)
    print(f"Cold-start eval: {len(val_eval.records):,} val users, "
          f"{len(test_eval.records):,} test users (>= {cfg['min_games']} games)")

    baseline = val_eval.evaluate_popularity(pop_counts, 'sampled')
    print(f"Popularity baseline on val: ndcg@10 {baseline['ndcg@10']:.4f}, "
          f"hit@10 {baseline['hit@10']:.4f}  <- the bar to beat\n")

    shared = dict(num_items=len(item_to_idx) + 1, content_dim=content_dim,
                  mf_dim=cfg['mf_dim'], mlp_dims=cfg['mlp_dims'],
                  content_hidden_dims=cfg['content_hidden_dims'], use_logits=True)
    if cfg['arch'] == 'profile':
        model = ProfileNeuMF(**shared).to(device)
        model.set_profile_index(*data.profile)
    else:
        model = HybridNeuMF(num_users=len(user_to_idx), **shared).to(device)
    print(f"Model: {type(model).__name__}, "
          f"{sum(p.numel() for p in model.parameters()):,} parameters\n")

    model, history, best_epoch = train_model(model, data, val_eval, cfg, device)

    print("\nTest set (cold-start users)...")
    results = {
        'model, 99 negatives': test_eval.evaluate(model, 'sampled'),
        'popularity, 99 negatives': test_eval.evaluate_popularity(pop_counts, 'sampled'),
        'model, full catalogue': test_eval.evaluate(model, 'full'),
        'popularity, full catalogue': test_eval.evaluate_popularity(pop_counts, 'full'),
    }
    print_results(results)
    fb = results['model, full catalogue']
    empty = "a zero user vector" if cfg['arch'] == 'profile' else "the population-average user"
    print(f"\n{fb['fallback_frac']:.1%} of test users had no core games in their profile "
          f"and fell back to {empty}.")
    if 'fallback_hit@10' in fb:
        print(f"Their hit@10 (full catalogue): {fb['fallback_hit@10']:.4f}")

    save_package(cfg['out_path'], model, processor, user_to_idx, item_to_idx,
                 game_to_features, history, results, cfg)
    plot_history(history, baseline['ndcg@10'])


if __name__ == '__main__':
    main()