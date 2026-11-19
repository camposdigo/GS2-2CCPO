"""Execute this project's trusted notebook using plain Python; persist outputs.

Jupyter is optional. This runner is deliberately limited to the bundled notebook,
whose cells use ordinary Python without magics. It does not fetch notebook code.
"""
import contextlib
import io
import json
import os
from pathlib import Path


if __name__ == "__main__":
    path = Path(__file__).resolve().parent / "analise.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    os.chdir(path.parent)
    namespace = {"__name__": "__main__"}
    count = 0
    for index, cell in enumerate(notebook["cells"]):
        cell.setdefault("id", f"water-{index:02d}")
        if cell["cell_type"] != "code":
            continue
        count += 1
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile("".join(cell["source"]), f"{path.name}:cell-{index}", "exec"), namespace)
        cell["execution_count"] = count
        cell["outputs"] = [{"output_type": "stream", "name": "stdout", "text": output.getvalue().splitlines(keepends=True)}]
        print(f"Célula {count}: OK", flush=True)
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Notebook executado e saídas preservadas: {path}")
