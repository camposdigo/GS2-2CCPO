"""Download official historical/current data, or verify the bundled cache."""
import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from source import acquire, unavailable

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone(timedelta(hours=-3))).date())
    p.add_argument("--start-year", type=int, default=2018)
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    try:
        quality = acquire(args.as_of, args.start_year, args.offline)
        print(f"OK: {quality['rows']} linhas, até {quality['lastObservedAt']}; treine com train.py.")
    except Exception as error:
        unavailable(f"Coleta falhou: {type(error).__name__}: {error}")
        print(f"FALHA TRANSPARENTE: {error}", file=sys.stderr)
        sys.exit(1)
