"""Train, select on validation, calibrate, evaluate once on held-out time, export."""
import argparse
import sys
from datetime import date
from source import unavailable

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    try:
        from modeling import run
        artifact = run(as_of=args.as_of)
        evaluation = artifact["evaluation"]
        print(f"Modelo: {evaluation['selectedModel']}; teste MAE={evaluation['test']['mae']}, RMSE={evaluation['test']['rmse']} p.p.; baseline MAE={evaluation['baseline']['mae']}; cobertura={evaluation['coverage']:.1%}")
    except Exception as error:
        unavailable(f"Treino/avaliação falhou: {type(error).__name__}: {error}")
        print(f"FALHA TRANSPARENTE: {error}", file=sys.stderr)
        sys.exit(1)
