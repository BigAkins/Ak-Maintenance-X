import argparse
import inspect
import json

from ak_maintenance_x.workflows import get_workflow, list_workflows


def build_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Ak Maintenance X command-line interface",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser(
        "list",
        help="List available workflows",
    )

    # run
    run_parser = subparsers.add_parser(
        "run",
        help="Run a workflow by name",
    )
    run_parser.add_argument(
        "workflow",
        choices=list_workflows(),
        help="Workflow name to run",
    )

    # Common optional overrides
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run mode on",
    )
    run_parser.add_argument(
        "--live",
        action="store_true",
        help="Force dry-run mode off",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        help="Override item limit for workflows that support it",
    )
    run_parser.add_argument(
        "--request-delay-seconds",
        type=float,
        help="Override delay between requests",
    )
    run_parser.add_argument(
        "--stop-on-rate-limit",
        action="store_true",
        help="Force stop_on_rate_limit=True",
    )
    run_parser.add_argument(
        "--no-stop-on-rate-limit",
        action="store_true",
        help="Force stop_on_rate_limit=False",
    )
    run_parser.add_argument(
        "--auto-wait-on-rate-limit",
        action="store_true",
        help="Force auto_wait_on_rate_limit=True",
    )
    run_parser.add_argument(
        "--no-auto-wait-on-rate-limit",
        action="store_true",
        help="Force auto_wait_on_rate_limit=False",
    )
    run_parser.add_argument(
        "--max-rate-limit-retries",
        type=int,
        help="Override max retry count after rate-limit waits",
    )
    run_parser.add_argument(
        "--start-time",
        type=str,
        help="Override start_time for date-based workflows (ISO 8601 / X API format)",
    )
    run_parser.add_argument(
        "--end-time",
        type=str,
        help="Override end_time for date-based workflows (ISO 8601 / X API format)",
    )
    run_parser.add_argument(
        "--exclude-reposts",
        action="store_true",
        help="Force exclude_reposts=True for workflows that support it",
    )
    run_parser.add_argument(
        "--include-reposts",
        action="store_true",
        help="Force exclude_reposts=False for workflows that support it",
    )
    run_parser.add_argument(
        "--exclude-replies",
        action="store_true",
        help="Force exclude_replies=True for workflows that support it",
    )
    run_parser.add_argument(
        "--include-replies",
        action="store_true",
        help="Force exclude_replies=False for workflows that support it",
    )

    return parser


def build_workflow_kwargs(args, workflow_func):
    """
    Build kwargs safely by only passing values that the selected workflow supports.
    """
    signature = inspect.signature(workflow_func)
    supported_params = set(signature.parameters.keys())

    kwargs = {}

    # dry_run
    if "dry_run" in supported_params:
        if args.live:
            kwargs["dry_run"] = False
        elif args.dry_run:
            kwargs["dry_run"] = True

    # limit
    if "limit" in supported_params and args.limit is not None:
        kwargs["limit"] = args.limit

    # request delay
    if (
        "request_delay_seconds" in supported_params
        and args.request_delay_seconds is not None
    ):
        kwargs["request_delay_seconds"] = args.request_delay_seconds

    # stop_on_rate_limit
    if "stop_on_rate_limit" in supported_params:
        if args.stop_on_rate_limit:
            kwargs["stop_on_rate_limit"] = True
        elif args.no_stop_on_rate_limit:
            kwargs["stop_on_rate_limit"] = False

    # auto_wait_on_rate_limit
    if "auto_wait_on_rate_limit" in supported_params:
        if args.auto_wait_on_rate_limit:
            kwargs["auto_wait_on_rate_limit"] = True
        elif args.no_auto_wait_on_rate_limit:
            kwargs["auto_wait_on_rate_limit"] = False

    # max_rate_limit_retries
    if (
        "max_rate_limit_retries" in supported_params
        and args.max_rate_limit_retries is not None
    ):
        kwargs["max_rate_limit_retries"] = args.max_rate_limit_retries

    # start_time / end_time
    if "start_time" in supported_params and args.start_time is not None:
        kwargs["start_time"] = args.start_time

    if "end_time" in supported_params and args.end_time is not None:
        kwargs["end_time"] = args.end_time

    # exclude_reposts
    if "exclude_reposts" in supported_params:
        if args.exclude_reposts:
            kwargs["exclude_reposts"] = True
        elif args.include_reposts:
            kwargs["exclude_reposts"] = False

    # exclude_replies
    if "exclude_replies" in supported_params:
        if args.exclude_replies:
            kwargs["exclude_replies"] = True
        elif args.include_replies:
            kwargs["exclude_replies"] = False

    return kwargs


def run_list_command():
    print("Available workflows:")
    for name in list_workflows():
        print(f"- {name}")


def run_workflow_command(args):
    workflow_func = get_workflow(args.workflow)
    kwargs = build_workflow_kwargs(args, workflow_func)

    print(f"Running workflow: {args.workflow}")
    if kwargs:
        print("Overrides:")
        for key, value in kwargs.items():
            print(f"- {key} = {value}")

    result = workflow_func(**kwargs)

    if result is not None:
        print("\n--- WORKFLOW RESULT ---")
        print(json.dumps(result, indent=2, default=str))


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list":
        run_list_command()
    elif args.command == "run":
        run_workflow_command(args)
    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()