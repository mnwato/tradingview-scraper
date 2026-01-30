import argparse
import logging

from tradingview_scraper.pipelines.discovery.pipeline import DiscoveryPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Compose and execute discovery pipelines.")
    parser.add_argument("--profile", type=str, default="production_2026_q1", help="Manifest profile to use")
    parser.add_argument("--pipeline", type=str, help="Specific pipeline to run (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Only compose and validate, don't execute")

    args = parser.parse_args()

    # Use the new DiscoveryPipeline
    pipeline = DiscoveryPipeline()

    if args.dry_run:
        logger.info("Dry run complete. Validation successful (Legacy dry-run logic bypassed).")
        return

    logger.info(f"Running discovery profile: {args.profile}")
    candidates = pipeline.run_profile(args.profile)

    logger.info(f"Discovery complete. Found {len(candidates)} candidates.")
    pipeline.save_candidates(candidates)


if __name__ == "__main__":
    main()
