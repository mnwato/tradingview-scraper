import argparse
import logging
import shutil
import tarfile
from pathlib import Path

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def archive_runs(runs_dir: str | None, archive_dir: str | None, keep: int, dry_run: bool = False):
    settings = get_settings()
    runs_path = Path(runs_dir) if runs_dir else settings.summaries_runs_dir
    archive_path = Path(archive_dir) if archive_dir else settings.artifacts_dir / "archive"

    if not dry_run:
        archive_path.mkdir(parents=True, exist_ok=True)

    if not runs_path.exists():
        logger.warning(f"Runs directory not found: {runs_path}")
        return

    # Find run directories (assuming format YYYYMMDD-HHMMSS)
    runs = []
    for d in runs_path.iterdir():
        if d.is_dir() and d.name[0].isdigit():
            runs.append(d)

    # Sort by name (which effectively sorts by date for this format)
    runs.sort(key=lambda x: x.name, reverse=True)

    if len(runs) <= keep:
        logger.info(f"Found {len(runs)} runs. Keeping {keep}. Nothing to archive.")
        return

    to_archive = runs[keep:]
    logger.info(f"Found {len(runs)} total runs. Retaining top {keep}.")
    logger.info(f"Candidates for archival: {len(to_archive)}")

    for run_dir in to_archive:
        run_id = run_dir.name
        archive_file = archive_path / f"{run_id}.tar.gz"

        if dry_run:
            logger.info(f"[DRY RUN] Would compress {run_dir} -> {archive_file}")
            logger.info(f"[DRY RUN] Would delete {run_dir}")
        else:
            logger.info(f"Compressing {run_dir} -> {archive_file}")
            try:
                with tarfile.open(archive_file, "w:gz") as tar:
                    tar.add(run_dir, arcname=run_id)

                # Verify archive exists
                if archive_file.exists():
                    logger.info(f"Removing original directory: {run_dir}")
                    shutil.rmtree(run_dir)
                else:
                    logger.error(f"Failed to create archive for {run_id}")
            except Exception as e:
                logger.error(f"Error archiving {run_id}: {e}")

    if dry_run:
        logger.info("[DRY RUN] Archive simulation complete.")
    else:
        logger.info("Archive complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive old run artifacts")
    parser.add_argument("--runs-dir", default=None, help="Directory containing run artifacts")
    parser.add_argument("--archive-dir", default=None, help="Destination directory for archives")
    parser.add_argument("--keep", type=int, default=10, help="Number of recent runs to keep unarchived")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without modifying files")

    args = parser.parse_args()
    archive_runs(args.runs_dir, args.archive_dir, args.keep, args.dry_run)
