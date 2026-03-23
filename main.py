import argparse
import inspect
import json

from ak_maintenance_x.workflows import get_workflow, list_workflows

WORKFLOW_NAMES = list_workflows()

# Short aliases -> canonical workflow names
WORKFLOW_ALIASES = {
    "me": "get-me",
    "whoami": "get-me",
    "inspect-account": "inspect",
    "preview": "dry-run",
    "non-followers": "find-non-followers",
    "reposts": "find-reposts",
    "likes-by-date": "find-likes-by-date",
    "posts-by-date": "find-posts-by-date",
    "unlike-candidates": "bulk-unlike-candidates",
    "unfollow-non-followers": "bulk-unfollow-non-followers",
    "unrepost": "bulk-unrepost",
    "delete-posts": "bulk-delete-posts",
}

WORKFLOW_GROUPS = {
    "Utility": [
        "get-me",
        "inspect",
        "dry-run",
    ],
    "Analysis": [
        "find-non-followers",
        "find-reposts",
        "find-likes-by-date",
        "find-posts-by-date",
    ],
    "Actions": [
        "bulk-unlike",
        "bulk-unlike-candidates",
        "bulk-unfollow",
        "bulk-unfollow-non-followers",
        "bulk-unrepost",
        "bulk-delete-posts",
    ],
}

WORKFLOW_DESCRIPTIONS = {
    "get-me": "Show the authenticated X account profile.",
    "inspect": "Inspect account activity like likes and following.",
    "dry-run": "Preview cleanup targets without making changes.",
    "find-non-followers": "Analyze non-followers and save candidate file.",
    "find-reposts": "Find repost candidates in a date range.",
    "find-likes-by-date": "Find liked posts by the liked post's created_at date.",
    "find-posts-by-date": "Find your own posts in a date range for deletion review.",
    "bulk-unlike": "Bulk unlike directly from liked posts.",
    "bulk-unlike-candidates": "Bulk unlike from reviewed like candidate file.",
    "bulk-unfollow": "Bulk unfollow from following list.",
    "bulk-unfollow-non-followers": "Bulk unfollow from reviewed non-follower candidates.",
    "bulk-unrepost": "Bulk unrepost from reviewed repost candidates.",
    "bulk-delete-posts": "Bulk delete from reviewed post-delete candidates.",
}


def resolve_workflow_name(name):
    if name in WORKFLOW_NAMES:
        return name
    if name in WORKFLOW_ALIASES:
        return WORKFLOW_ALIASES[name]
    raise ValueError(f"Unknown workflow '{name}'.")


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
        epilog="Use 'python main.py list' to view workflows and aliases.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "list",
        help="List workflows and aliases",
        description="List all available workflows and aliases grouped by purpose.",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run a workflow by canonical name or alias",
        description="Run a workflow by explicit canonical name or alias.",
    )
    run_parser.add_argument(
        "workflow",
        choices=WORKFLOW_NAMES + list(WORKFLOW_ALIASES.keys()),
        help="Workflow name or alias to run",
    )
    add_common_arguments(run_parser)

    for workflow_name in WORKFLOW_NAMES:
        workflow_parser = subparsers.add_parser(
            workflow_name,
            help=WORKFLOW_DESCRIPTIONS.get(workflow_name, f"Run '{workflow_name}'"),
            description=WORKFLOW_DESCRIPTIONS.get(workflow_name, f"Run '{workflow_name}'"),
        )
        add_common_arguments(workflow_parser)
        workflow_parser.set_defaults(workflow=workflow_name)

    for alias_name, canonical_name in WORKFLOW_ALIASES.items():
        alias_parser = subparsers.add_parser(
            alias_name,
            help=f"Alias for '{canonical_name}'",
            description=f"Alias for '{canonical_name}': {WORKFLOW_DESCRIPTIONS.get(canonical_name, '')}",
        )
        add_common_arguments(alias_parser)
        alias_parser.set_defaults(workflow=alias_name)

    return parser


def validate_args(parser, args):
    conflicting_pairs = [
        ("dry_run", "live", "--dry-run", "--live"),
        ("stop_on_rate_limit", "no_stop_on_rate_limit", "--stop-on-rate-limit", "--no-stop-on-rate-limit"),
        ("auto_wait_on_rate_limit", "no_auto_wait_on_rate_limit", "--auto-wait-on-rate-limit", "--no-auto-wait-on-rate-limit"),
        ("exclude_reposts", "include_reposts", "--exclude-reposts", "--include-reposts"),
        ("exclude_replies", "include_replies", "--exclude-replies", "--include-replies"),
    ]

    for left_attr, right_attr, left_flag, right_flag in conflicting_pairs:
        if hasattr(args, left_attr) and hasattr(args, right_attr):
            if getattr(args, left_attr) and getattr(args, right_attr):
                parser.error(f"Cannot use {left_flag} and {right_flag} together.")

    if hasattr(args, "limit") and args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than 0.")

    if (
        hasattr(args, "request_delay_seconds")
        and args.request_delay_seconds is not None
        and args.request_delay_seconds < 0
    ):
        parser.error("--request-delay-seconds must be 0 or greater.")

    if (
        hasattr(args, "max_rate_limit_retries")
        and args.max_rate_limit_retries is not None
        and args.max_rate_limit_retries < 0
    ):
        parser.error("--max-rate-limit-retries must be 0 or greater.")


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
    print("Available workflows by group:\n")

    for group_name, workflows in WORKFLOW_GROUPS.items():
        print(f"{group_name}:")
        for workflow in workflows:
            description = WORKFLOW_DESCRIPTIONS.get(workflow, "")
            print(f"  - {workflow}: {description}")
        print()

    print("Aliases:")
    for alias, workflow in WORKFLOW_ALIASES.items():
        print(f"  - {alias} -> {workflow}")


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
    validate_args(parser, args)

    if args.command == "list":
        run_list_command()
        return

    if args.command == "run":
        run_workflow(args.workflow, args)
        return

    run_workflow(args.workflow, args)


if __name__ == "__main__":
    main()