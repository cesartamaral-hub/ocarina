"""
Measures how well each translation model translates each language into English, on the FLORES-200 test set (ocarina/quality/quality_set.json),
scored with chrF. Needs the models downloaded. Results are written after every language, so it can be stopped and run again.

    python scripts/measure_quality.py <data folder with the models> <out.json> <model id> [<model id> ...]
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ocarina import paths, translate  # noqa: E402  pylint: disable=wrong-import-position
from ocarina.quality.chrf import chrf  # noqa: E402  pylint: disable=wrong-import-position

SET = os.path.join(os.path.dirname(__file__), "..", "ocarina", "quality", "quality_set.json")


def main(datapath, out, model_ids):
    paths.configure(datapath, bring_models=False)
    os.environ["HF_HUB_OFFLINE"] = "1"
    with open(SET, encoding="utf-8") as f:
        test = json.load(f)
    results = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    for model_id in model_ids:
        done = results.setdefault(model_id, {})
        started = time.time()
        for name, lang in test["languages"].items():
            if name in done:
                continue
            hypotheses, errors = [], 0
            for text in lang["sentences"]:
                try:
                    hypotheses.append(translate._local(text, name, lang["code"], "en", None, model_id))  # pylint: disable=protected-access
                except Exception as e:  # pylint: disable=broad-exception-caught
                    errors += 1
                    hypotheses.append("")
                    print("  error", name, type(e).__name__, e, flush=True)
            done[name] = {"code": lang["code"], "chrf": chrf(hypotheses, test["reference"]), "errors": errors, "translations": hypotheses}
            json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(model_id, name, done[name]["chrf"], f"{round(time.time() - started)}s", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
