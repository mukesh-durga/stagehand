"""Worker entrypoint: `python -m worker.main`."""

import logging

from worker.consumer import RUN_QUEUE_KEY, run_worker_loop


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Stagehand worker started; consuming from %s", RUN_QUEUE_KEY)
    try:
        run_worker_loop()
    except KeyboardInterrupt:
        logger.info("Stagehand worker stopping (interrupted)")


if __name__ == "__main__":
    main()
