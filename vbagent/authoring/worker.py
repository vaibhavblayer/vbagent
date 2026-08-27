"""Detached process entrypoint for durable authoring execution."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from vbagent.authoring.service import AuthoringRunService
from vbagent.authoring.store import AuthoringStore

logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute one durable authoring run")
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dispatch-token", required=True)
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    output = Path(args.output).expanduser().resolve()
    try:
        if args.concurrency is not None and not 1 <= args.concurrency <= 32:
            raise ValueError("concurrency must be between 1 and 32")
        from vbagent.config import apply_provider_config

        apply_provider_config()
        with AuthoringStore(output) as store:
            service = AuthoringRunService(store)
            if args.resume:
                stats = service.resume(args.run_id, concurrency=args.concurrency)
            else:
                stats = service.execute(args.run_id, concurrency=args.concurrency)
        logger.info("authoring worker finished: %s", stats)
        with AuthoringStore(output) as store:
            store.finish_dispatch(
                args.run_id,
                args.dispatch_token,
                status="finished",
            )
        return 0
    except BaseException as exc:
        logger.exception("authoring worker failed for run %s", args.run_id)
        try:
            with AuthoringStore(output) as store:
                store.finish_dispatch(
                    args.run_id,
                    args.dispatch_token,
                    status="failed",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
        except Exception:
            logger.exception("failed to record worker dispatch failure")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
