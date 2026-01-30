import glob
import logging
import os

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup")


def cleanup():
    settings = get_settings()
    # Use settings.export_dir
    pattern = str(settings.export_dir / "*.json")
    files = glob.glob(pattern)
    count = 0
    for f in files:
        try:
            os.remove(f)
            count += 1
        except Exception as e:
            logger.error(f"Failed to delete {f}: {e}")

    logger.info(f"Deleted {count} files from {settings.export_dir}")


if __name__ == "__main__":
    cleanup()
