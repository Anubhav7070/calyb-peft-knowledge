"""Run every file in examples/input through the reasoner; write results to examples/output."""
import _path  # noqa
import glob, json, os
from peft_kb import knowledge as K
from peft_kb.reasoning import InputError, reason

ks = K.load("knowledge/knowledge_state.json")
for f in sorted(glob.glob("examples/input/*.txt")):
    try:
        out = reason(open(f, encoding="utf-8").read(), ks)
    except InputError as e:
        out = {"status": "error", "error": str(e)}
    dest = os.path.join("examples/output", os.path.basename(f).replace(".txt", ".json"))
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"{f} -> {dest} [{out['status']}]")
