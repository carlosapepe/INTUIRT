"""Exporta um trace do modelo IRT para o simulador INTUIRT.

Uso:
    python exportar_intuirt.py <modulo> <topologia> <semente> > trace.json

    <modulo>     nome do arquivo do modelo sem .py (padrao: modelo_irt)
    <topologia>  BA, ER ou WS (padrao: BA)
    <semente>    semente da execucao (padrao: SEEDS[0] do modelo)

O script nao altera o modelo: ele envolve as funcoes de cada fase do ciclo,
roda as tres configuracoes (Baseline, Baseline+Ataque, Ataque+Protecao) com a
mesma semente e grava, ciclo a ciclo, o que mudou na rede e as metricas.
"""
import importlib
import json
import random
import sys

import networkx as nx
import numpy as np

MOD = sys.argv[1] if len(sys.argv) > 1 else "modelo_irt"
KIND = sys.argv[2] if len(sys.argv) > 2 else "BA"
irt = importlib.import_module(MOD)
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else irt.SEEDS[0]

cur = {}
REC = []


def edges(G):
    return {tuple(sorted(e)) for e in G.edges}


def alive(G):
    return {v for v in G.nodes if G.nodes[v].get("alive", True)}


def ua(G):
    return {v for v in G.nodes if G.nodes[v].get("under_attack", False)}


def num(x):
    if x is None:
        return None
    x = float(x)
    return None if np.isnan(x) else x


_elect = irt.elect_leaders
def elect(G):
    l, d = _elect(G)
    cur["L"], cur["D"] = l, d
    return l, d
irt.elect_leaders = elect

_inject = irt.inject_failures_and_attacks
def inject(G, leader, config=irt.ATTACK_CONFIG):
    E0, A0, U0 = edges(G), alive(G), ua(G)
    gt = _inject(G, leader, config)
    A1 = alive(G)
    cur["rem"] = [list(e) for e in sorted(E0 - edges(G))]
    cur["fn"] = sorted(A0 - A1)
    cur["dos"] = sorted((ua(G) - U0) & A1)
    cur["gt"] = sorted(gt)
    return gt
irt.inject_failures_and_attacks = inject

_detect = irt.detect_anomalies_intuitive
def detect(G, pre):
    an, sc = _detect(G, pre)
    cur["an"] = sorted(an)
    return an, sc
irt.detect_anomalies_intuitive = detect

_disc = irt.KnowledgeNetworks.discretize
def disc(self, qi, p_threat=0.0):
    b = _disc(self, qi, p_threat)
    if cur.get("_in") and not cur.get("b"):
        cur["b"] = b
    return b
irt.KnowledgeNetworks.discretize = disc

_conf = irt.DualSystemResponse.confidence
def conf(self, state):
    v = _conf(self, state)
    if cur.get("_in"):
        cur["eta"] = float(v)
    return v
irt.DualSystemResponse.confidence = conf

_choose = irt.DualSystemResponse.choose
def choose(self, knowledge, dl, qi, p_threat, anomalous):
    cur["_in"] = True
    action, da, system, theta = _choose(self, knowledge, dl, qi, p_threat, anomalous)
    cur["_in"] = False
    cur.update(sys=system, act=action, da=da, p=float(p_threat), th=num(theta))
    return action, da, system, theta
irt.DualSystemResponse.choose = choose

_apply = irt.apply_resilience
def apply(G, leader, deputy, action, anomalies, config):
    E0, A0, U0 = edges(G), alive(G), ua(G)
    l2, d2 = _apply(G, leader, deputy, action, anomalies, config)
    ref = sorted(alive(G) - A0)
    cur["ref"] = ref
    cur["mit"] = sorted(U0 - ua(G))
    cur["add"] = [[u, v, "r" if (u in ref or v in ref) else "m"] for u, v in sorted(edges(G) - E0)]
    cur["prom"] = l2 != leader
    return l2, d2
irt.apply_resilience = apply

KEYS = {"qi_before": "qb", "qi_failure": "qf", "qi": "qa", "connectivity": "c", "prop_eff": "pe",
        "delivery": "d", "eprop_global": "eg", "tii": "tii", "arf": "arf", "roc_auc": "auc",
        "precision": "prec", "recall": "rec", "f1": "f1", "accuracy": "acc", "reward": "rew",
        "p_threat": "p", "tp": "tp", "fp": "fp", "fn": "fn", "tn": "tn"}

_cycle = irt.single_cycle
def cycle(G, config, cycle_id, knowledge=None, dl=None, dual=None, pre=None):
    cur.clear()
    cur.update(c=cycle_id, rem=[], fn=[], dos=[], gt=[], an=[], sys="", act="OK", da="", p=0.0,
               th=None, eta=None, b="", mit=[], ref=[], add=[], prom=False)
    r = _cycle(G, config, cycle_id, knowledge=knowledge, dl=dl, dual=dual, pre=pre)
    cur["m"] = {KEYS[k]: num(v) for k, v in r.items() if k in KEYS}
    if knowledge is not None:
        cur["kn"] = {"h": len(knowledge.historical), "i": len(knowledge.intuitive),
                     "e": len(knowledge.emergent), "ctx": knowledge.contextual.get("threat", "")}
    REC.append({k: v for k, v in cur.items() if not k.startswith("_")})
    return r
irt.single_cycle = cycle


def run(cfg):
    np.random.seed(SEED)
    random.seed(SEED)
    G = irt.build_topology(KIND, irt.N_NODES, seed=SEED)
    E0 = [list(e) for e in sorted(edges(G))]
    if cfg.get("use_intuitive"):
        kn, dl, du, pre = (irt.KnowledgeNetworks(), irt.DistributedLearning(G),
                           irt.DualSystemResponse(), irt.PatternRecognitionEngine())
    else:
        kn = dl = du = pre = None
    REC.clear()
    for c in range(1, irt.N_CYCLES + 1):
        irt.single_cycle(G, cfg, c, knowledge=kn, dl=dl, dual=du, pre=pre)
    return E0, list(REC)


if __name__ == "__main__":
    np.random.seed(SEED)
    random.seed(SEED)
    G = irt.build_topology(KIND, irt.N_NODES, seed=SEED)
    pos = nx.spring_layout(G, seed=SEED)
    mx = max(max(abs(x), abs(y)) for x, y in pos.values()) or 1.0
    P = [[round(float(pos[v][0]) / mx * 0.95, 4), round(float(pos[v][1]) / mx * 0.95, 4)] for v in sorted(G.nodes)]

    out = {"model": "intuirt", "source": f"python:{MOD}", "topology": KIND, "seed": SEED,
           "n": irt.N_NODES, "cycles": irt.N_CYCLES, "attack": irt.ATTACK_CONFIG, "pos": P, "cfg": {}}
    for key, cfg in (("base", irt.NO_ATTACK_CFG), ("atk", irt.BASELINE_CFG), ("irt", irt.IMPROVED_CFG)):
        E0, recs = run(cfg)
        out.setdefault("E0", E0)
        out["cfg"][key] = recs
    json.dump(out, sys.stdout, separators=(",", ":"))
