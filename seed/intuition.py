"""ECHO-SEED · S2 intuition network: look at a task's (input -> output) pairs, say which primitives to try.

    (Kaggle GPU)  python intuition.py train DREAMS.npz OUT_weights.npz --epochs 8
    (local, CPU)  from echoai.seed.intuition import Intuition; Intuition(path).probs(task)

It is trained only on DREAMS (invented tasks from the train pool, see dreams.py). It never decides:
its probabilities only turn into integer step costs that ORDER the search; a program still counts
only if ECHO verifies it on every example. Training uses torch (GPU); local inference is plain numpy,
so the ECHO side needs no torch.

Architecture: each pair = 22 one-hot planes (11 values x input/output, value 10 = outside the grid),
3 conv layers + global mean/max pooling -> pair vector; the task vector is the mean over pairs; an
MLP gives one logit per primitive family.
"""
import sys

import numpy as np

C = 11                                                      # 10 colours + outside


def onehot(x):
    """x: (..., 30, 30) uint8 with 255 = outside -> (..., 11, 30, 30) float32."""
    v = np.where(x == 255, 10, x).astype(np.int64)
    out = np.zeros(v.shape[:-2] + (C,) + v.shape[-2:], dtype=np.float32)
    np.put_along_axis(out, v[..., None, :, :], 1.0, axis=-3)
    return out


# ---------------------------------------------------------------- training (torch, Kaggle GPU)

def build_torch():
    import torch
    import torch.nn as nn

    class Net(nn.Module):
        def __init__(self, n_out):
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv2d(2 * C, 64, 3, padding=1), nn.ReLU(),
                nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(),
                nn.Conv2d(64, 128, 3, padding=1, stride=2), nn.ReLU())
            self.head = nn.Sequential(nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, n_out))

        def forward(self, x):                               # x: (B, P, 22, 30, 30)
            b, p = x.shape[:2]
            h = self.conv(x.reshape(b * p, *x.shape[2:]))
            h = torch.cat([h.mean((2, 3)), h.amax((2, 3))], 1).reshape(b, p, -1).mean(1)
            return self.head(h)
    return torch, Net


def train(dreams, out, epochs=8, batch=256):
    torch, Net = build_torch()
    d = np.load(dreams)
    X, Y, names = d["X"], d["Y"].astype(np.float32), d["names"]
    n = len(X)
    idx = np.random.default_rng(0).permutation(n)
    val, tr = idx[: n // 20], idx[n // 20:]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = Net(Y.shape[1]).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)
    lossf = torch.nn.BCEWithLogitsLoss()

    def batch_x(ix):                                        # (B, 3, 2, 30, 30) -> (B, 3, 22, 30, 30)
        oh = onehot(X[ix])                                  # (B, 3, 2, 11, 30, 30)
        return torch.from_numpy(oh.reshape(len(ix), 3, 2 * C, 30, 30)).to(dev)

    for ep in range(epochs):
        net.train()
        rng = np.random.default_rng(ep)
        order = rng.permutation(tr)
        tot = 0.0
        for i in range(0, len(order), batch):
            ix = np.sort(order[i:i + batch])
            loss = lossf(net(batch_x(ix)), torch.from_numpy(Y[ix]).to(dev))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(ix)
        net.eval()
        with torch.no_grad():
            hits = k = 0
            for i in range(0, len(val), batch):
                ix = np.sort(val[i:i + batch])
                p = net(batch_x(ix)).cpu().numpy()
                top = np.argsort(-p, 1)[:, :5]                 # recall@5: true primitives among the top 5
                for r, t in zip(top, Y[ix]):
                    true = set(np.nonzero(t)[0])
                    hits += len(true & set(r))
                    k += len(true)
        print({"epoch": ep, "train_loss": round(tot / len(tr), 4), "val_recall_at_5": round(hits / k, 4)}, flush=True)
    sd = {k: v.detach().cpu().numpy() for k, v in net.state_dict().items()}
    np.savez_compressed(out, names=names, **sd)


# ---------------------------------------------------------------- inference (numpy, ECHO side)

def _conv(x, w, b, stride=1):
    """x (N, Cin, H, W), w (Cout, Cin, 3, 3), padding 1."""
    n, cin, h, wd = x.shape
    xp = np.pad(x, ((0, 0), (0, 0), (1, 1), (1, 1)))
    ho, wo = (h - 1) // stride + 1, (wd - 1) // stride + 1
    cols = np.empty((n, cin, 3, 3, ho, wo), dtype=np.float32)
    for i in range(3):
        for j in range(3):
            cols[:, :, i, j] = xp[:, :, i:i + stride * ho:stride, j:j + stride * wo:stride]
    return np.einsum("nckluv,dckl->nduv", cols, w, optimize=True) + b[None, :, None, None]


class Intuition:
    def __init__(self, path):
        d = np.load(path, allow_pickle=False)
        self.names = [str(x) for x in d["names"]]
        self.p = {k: d[k] for k in d.files if k != "names"}

    def probs(self, task):
        from echoai.seed.dreams import pad
        pairs = [(pad(p["input"]), pad(p["output"])) for p in task["train"]][:3]
        while len(pairs) < 3:
            pairs.append(pairs[len(pairs) % max(len(pairs), 1)])
        x = onehot(np.stack([np.stack([a, b]) for a, b in pairs]))      # (3, 2, 11, 30, 30)
        h = x.reshape(3, 2 * C, 30, 30)
        p = self.p
        h = np.maximum(_conv(h, p["conv.0.weight"], p["conv.0.bias"]), 0)
        h = np.maximum(_conv(h, p["conv.2.weight"], p["conv.2.bias"]), 0)
        h = np.maximum(_conv(h, p["conv.4.weight"], p["conv.4.bias"], stride=2), 0)
        v = np.concatenate([h.mean((2, 3)), h.max((2, 3))], 1).mean(0)
        v = np.maximum(v @ p["head.0.weight"].T + p["head.0.bias"], 0)
        z = v @ p["head.2.weight"].T + p["head.2.bias"]
        return dict(zip(self.names, (1 / (1 + np.exp(-z))).tolist()))


if __name__ == "__main__":
    if sys.argv[1] == "train":
        train(sys.argv[2], sys.argv[3], epochs=int(sys.argv[sys.argv.index("--epochs") + 1]) if "--epochs" in sys.argv else 8)
