import argparse
import inspect
import json

from ak_maintenance_x.workflows import get_workflow, list_workflows

WORKFLOW_NAMES = list_workflows()

# Short aliases -> canonical workflow names
WORKFLOW_ALIASES = {
    "me": "get-me",
    "non-followers": "find-non-followers",
    "reposts": "find-reposts",
    "likes-by-date": "find-likes-by-date",
    "posts-by-date": "find-posts-by-date",
    "unlike-candidates": "bulk-unlike-candidates",
    "unfollow-non-followers": "bulk-unfollow-non-followers",
    "unrepost": "bulk-unrepost",
    "delete-posts": "bulk-delete-posts",
}

ALL_COMMAND_NAMES = WORKFLOW_NAMES + list(WORKFLOW_ALIASES.keys())


def resolve_workflow_name(name):
    if name in WORKFLOW_NAMES:
        return name
    if name in WORKFLOW_ALIASES:
        return WORKFLOW_ALIASES[name]
    raise ValueError(
        f"Unknown workflow '{name}'. Available commands: {ALL_COMMAND_NAMES}"
    )


def add_common_arguments(parser):
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run mode on",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Force dry-run mode off",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Override item limit for workflows that support it",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        help="Override delay between requests",
    )
    parser.add_argument(
        "--stop-on-rate-limit",
        action="store_true",
        help="Force stop_on_rate_limit=True",
    )
    parser.add_argument(
        "--no-stop-on-rate-limit",
        action="store_true",
        help="Force stop_on_rate_limit=False",
    )
    parser.add_argument(
        "--auto-wait-on-rate-limit",
        action="store_true",
        help="Force auto_wait_on_rate_limit=True",
    )
    parser.add_argument(
        "--no-auto-wait-on-rate-limit",
        action="store_true",
        help="Force auto_wait_on_rate_limit=False",
    )
    parser.add_argument(
        "--max-rate-limit-retries",
        type=int,
        help="Override max retry count after rate-limit waits",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        help="Override start_time for date-based workflows (ISO 8601 / X API format)",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        help="Override end_time for date-based workflows (ISO 8601 / X API format)",
    )
    parser.add_argument(
        "--exclude-reposts",
        action="store_true",
        help="Force exclude_reposts=True for workflows that support it",
    )
    parser.add_argument(
        "--include-reposts",
        action="store_true",
        help="Force exclude_reposts=False for workflows that support it",
    )
    parser.add_argument(
        "--exclude-replies",
        action="store_true",
        help="Force exclude_replies=True for workflows that support it",
    )
    parser.add_argument(
        "--include-replies",
        action="store_true",
        help="Force exclude_replies=False for workflows that support it",
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Ak Maintenance X command-line interface",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list command
    subparsers.add_parser(
        "list",
        help="List available workflows and aliases",
        description="List all available workflows and aliases registered in the system.",
    )

    # legacy run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run a workflow by name",
        description="Run a workflow by explicit name or alias.",
    )
    run_parser.add_argument(
        "workflow",
        choices=ALL_COMMAND_NAMES,
        help="Workflow name or alias to run",
    )
    add_common_arguments(run_parser)

    # direct canonical workflow commands
    for workflow_name in WORKFLOW_NAMES:
        workflow_parser = subparsers.add_parser(
            workflow_name,
            help=f"Run the '{workflow_name}' workflow",
            description=f"Run the '{workflow_name}' workflow.",
        )
        add_common_arguments(workflow_parser)
        workflow_parser.set_defaults(workflow=workflow_name)

    # alias commands
    for alias_name, canonical_name in WORKFLOW_ALIASES.items():
        alias_parser = subparsers.add_parser(
            alias_name,
            help=f"Alias for '{canonical_name}'",
            description=f"Alias for '{canonical_name}'.",
        )
        add_common_arguments(alias_parser)
        alias_parser.set_defaults(workflow=alias_name)

    return parser


def build_workflow_kwargs(args, workflow_func):
    signature = inspect.signature(workflow_func)
    supported_params = set(signature.parameters.keys())

    kwargs = {}

    if "dry_run" in supported_params:
        if args.live:
            kwargs["dry_run"] = False
        elif args.dry_run:
            kwargs["dry_run"] = True

    if "limit" in supported_params and args.limit is not None:
        kwargs["limit"] = args.limit

    if (
        "request_delay_seconds" in supported_params
        and args.request_delay_seconds is not None
    ):
        kwargs["request_delay_seconds"] = args.request_delay_seconds

    if "stop_on_rate_limit" in supported_params:
        if args.stop_on_rate_limit:
            kwargs["stop_on_rate_limit"] = True
        elif args.no_stop_on_rate_limit:
            kwargs["stop_on_rate_limit"] = False

    if "auto_wait_on_rate_limit" in supported_params:
        if args.auto_wait_on_rate_limit:
            kwargs["auto_wait_on_rate_limit"] = True
        elif args.no_auto_wait_on_rate_limit:
            kwargs["auto_wait_on_rate_limit"] = False

    if (
        "max_rate_limit_retries" in supported_params
        and args.max_rate_limit_retries is not None
    ):
        kwargs["max_rate_limit_retries"] = args.max_rate_limit_retries

    if "start_time" in supported_params and args.start_time is not None:
        kwargs["start_time"] = args.start_time

    if "end_time" in supported_params and args.end_time is not None:
        kwargs["end_time"] = args.end_time

    if "exclude_reposts" in supported_params:
        if args.exclude_reposts:
            kwargs["exclude_reposts"] = True
        elif args.include_reposts:
            kwargs["exclude_reposts"] = False

    if "exclude_replies" in supported_params:
        if args.exclude_replies:
            kwargs["exclude_replies"] = True
        elif args.include_replies:
            kwargs["exclude_replies"] = False

    return kwargs


def run_list_command():
    print("Available workflows:")
    for name in WORKFLOW_NAMES:
        print(f"- {name}")

    print("\nAliases:")
    for alias, workflow in WORKFLOW_ALIASES.items():
        print(f"- {alias} -> {workflow}")


def run_workflow(workflow_name, args):
    canonical_name = resolve_workflow_name(workflow_name)
    workflow_func = get_workflow(canonical_name)
    kwargs = build_workflow_kwargs(args, workflow_func)

    print(f"Running workflow: {canonical_name}")
    if workflow_name != canonical_name:
        print(f"Alias used: {workflow_name}")

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
        return

    if args.command == "run":
        run_workflow(args.workflow, args)
        return

    run_workflow(args.workflow, args)


if __name__ == "__main__":
    main()