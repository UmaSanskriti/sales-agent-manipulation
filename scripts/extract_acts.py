"""Extract residual-stream activations for every judged agent turn (visible-text replay).

    python scripts/extract_acts.py --model openai/gpt-oss-120b                  # all 600 conversations
    python scripts/extract_acts.py --model openai/gpt-oss-120b --limit 3         # smoke test
    python scripts/extract_acts.py --model openai/gpt-oss-120b --verify 5        # per-turn equivalence check

Writes data/activations/acts.npy ([N, n_layers, 3, D] fp16, memmap; row order = sorted turn_id),
index.jsonl (one line per row) and done.txt (finished conversations; the run is resumable).
Needs one 80 GB GPU for gpt-oss-120b and the full dependency set in requirements.txt.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from src.acts import POSITIONS, gather_vectors, locate_turns  # noqa: E402
from src.judge.inputs import load_conversation  # noqa: E402
from src.probe_data import ACT_DIR, CONV_DIR, all_labeled_turn_ids, load_splits  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-oss-120b")
    ap.add_argument("--reasoning-effort", default="medium")
    ap.add_argument("--conv-dir", default=str(CONV_DIR))
    ap.add_argument("--out", default=str(ACT_DIR))
    ap.add_argument("--limit", type=int, default=None, help="only the first N conversations")
    ap.add_argument("--verify", type=int, default=0, help="re-run N turns one at a time and compare")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    turn_ids = all_labeled_turn_ids()
    row_of = {t: i for i, t in enumerate(turn_ids)}
    splits = load_splits()

    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype="auto", device_map="auto")
    model.eval()
    n_layers = model.config.num_hidden_layers + 1
    d = model.config.hidden_size

    path = out / "acts.npy"
    mode = "r+" if path.exists() else "w+"
    acts = np.lib.format.open_memmap(path, mode=mode, dtype=np.float16,
                                     shape=(len(turn_ids), n_layers, len(POSITIONS), d))
    done_path = out / "done.txt"
    done = set(done_path.read_text().split()) if done_path.exists() else set()
    index_path = out / "index.jsonl"

    def run(system, messages):
        ids, spans = locate_turns(tok, system, messages, a.reasoning_effort)
        x = torch.tensor([ids], device=model.device)
        with torch.no_grad():
            hs = model(input_ids=x, output_hidden_states=True).hidden_states
        return gather_vectors(hs, spans), spans, len(ids)

    files = sorted(Path(a.conv_dir).glob("*.jsonl"))[: a.limit]
    t0 = time.time()
    checked = 0
    skipped = 0
    with open(index_path, "a") as idx:
        for n, p in enumerate(files, 1):
            spec, messages, meta = load_conversation(p)
            if spec.conv_id in done:
                continue
            system = meta["metadata"]["agent_system_prompt"]
            vecs, spans, n_tok = run(system, messages)
            for v, s in zip(vecs, spans):
                tid = f"{spec.conv_id}#t{s['turn']}"
                if tid not in row_of:  # turn the judge never labeled: not a probe example, skip it
                    skipped += 1
                    continue
                acts[row_of[tid]] = v
                idx.write(json.dumps({"row": row_of[tid], "turn_id": tid, "conv_id": spec.conv_id,
                                      "turn": s["turn"], "split": splits[spec.scenario_id],
                                      "condition": spec.condition, "persona": spec.persona_id,
                                      "n_reply_tokens": s["end"] - s["start"], "n_context_tokens": n_tok}) + "\n")
            acts.flush()
            idx.flush()
            with open(done_path, "a") as f:
                f.write(spec.conv_id + "\n")
            # per-turn equivalence: replay the prefix that ends at this turn and compare its vectors
            if checked < a.verify and len(spans) > 1:
                from src.acts import agent_turn_indices
                ai = agent_turn_indices(messages)
                k = len(spans) - 1
                prefix = messages[: ai[k] + 1]
                v2, s2, _ = run(system, prefix)
                x, y = vecs[k].astype(np.float32).ravel(), v2[-1].astype(np.float32).ravel()
                cos = float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y)))
                print(f"verify {spec.conv_id}#t{spans[k]['turn']}: cosine {cos:.5f}")
                assert cos > 0.999, "single-pass and per-turn activations disagree"
                checked += 1
            print(f"[{n}/{len(files)}] {spec.conv_id} {len(spans)} turns {n_tok} tokens "
                  f"({time.time() - t0:.0f}s)", flush=True)
    print(f"done ({skipped} unlabeled turns skipped)")


if __name__ == "__main__":
    main()
