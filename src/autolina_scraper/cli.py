"""``autolina-scraper`` command-line entry point."""

from __future__ import annotations

import argparse
import logging
import sys

from autolina_scraper import __version__
from autolina_scraper.orchestrate import scrape

logger = logging.getLogger("autolina_scraper")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autolina-scraper",
        description="Fetch every autolina.ch listing for a given make/model.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--make", required=True, help='Make name or slug, e.g. "VW" or "vw"')
    parser.add_argument(
        "--model", required=True, help='Model name or slug, e.g. "Tiguan" or "tiguan"'
    )
    parser.add_argument("--domain", default="ch", help="Country domain (default: ch)")
    parser.add_argument("--category", default="car", help='Vehicle category (only "car")')
    parser.add_argument(
        "--out",
        default=None,
        help="Output file base name, without extension (default: <make>_<model>)",
    )
    parser.add_argument(
        "--no-detail",
        action="store_true",
        help="Skip per-listing detail visits; keep only summary fields (faster, fewer fields)",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Seconds between requests (default: 1.0)"
    )
    parser.add_argument("--price-from", type=int, default=None, help="Minimum price, CHF")
    parser.add_argument("--price-to", type=int, default=None, help="Maximum price, CHF")
    parser.add_argument("--mileage-from", type=int, default=None, help="Minimum mileage, km")
    parser.add_argument("--mileage-to", type=int, default=None, help="Maximum mileage, km")
    parser.add_argument(
        "--year-from", type=int, default=None, help="Minimum first-registration year"
    )
    parser.add_argument("--year-to", type=int, default=None, help="Maximum first-registration year")
    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Cap the number of listings collected/detail-visited (default: unlimited)",
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose", action="store_true", help="Also show debug-level detail"
    )
    verbosity.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output; only warnings/errors",
    )
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.quiet:
        level = logging.WARNING
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format="%(message)s")

    try:
        result = scrape(
            args.make,
            args.model,
            domain=args.domain,
            category=args.category,
            detail=not args.no_detail,
            price_from=args.price_from,
            price_to=args.price_to,
            mileage_from=args.mileage_from,
            mileage_to=args.mileage_to,
            year_from=args.year_from,
            year_to=args.year_to,
            max_results=args.max_results,
            delay=args.delay,
            verbose=not args.quiet,
        )
    except ValueError as error:
        logger.error("%s", error)
        return 2
    except Exception as error:  # noqa: BLE001 - network/HTTP errors, reported then re-raised as exit code
        logger.error("scrape failed: %s", error)
        return 1

    out_base = args.out or f"{result.make_key}_{result.model_key}"
    result.to_csv(f"{out_base}.csv")
    result.to_json(f"{out_base}.json")
    logger.info(
        "wrote %d listings to %s.csv and %s.json", len(result.rows), out_base, out_base
    )
    return 0


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":  # pragma: no cover - exercised by the e2e CLI subprocess tests
    main()
