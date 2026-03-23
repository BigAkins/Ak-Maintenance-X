"""
Workflow registry for Ak_Maintenance_X.

This module maps CLI command names to callable run_* functions
from scripts so we can build a clean main.py entry point.
"""

# --- IMPORT RUN FUNCTIONS ---

# Utility
from scripts.get_me import run_get_me
from scripts.account_inspector import run_account_inspector
from scripts.dry_run_cleanup import run_dry_run_cleanup

# Analysis
from scripts.find_non_followers import run_find_non_followers
from scripts.find_reposts import run_find_reposts
from scripts.find_likes_by_date import run_find_likes_by_date
from scripts.find_posts_by_date import run_find_posts_by_date

# Actions
from scripts.bulk_unlike import run_bulk_unlike
from scripts.bulk_unlike_candidates import run_bulk_unlike_candidates
from scripts.bulk_unfollow import run_bulk_unfollow
from scripts.bulk_unfollow_non_followers import run_bulk_unfollow_non_followers
from scripts.bulk_unrepost import run_bulk_unrepost
from scripts.bulk_delete_posts_by_date import run_bulk_delete_posts_by_date


# --- WORKFLOW REGISTRY ---

WORKFLOWS = {
    # Utility
    "get-me": run_get_me,
    "inspect": run_account_inspector,
    "dry-run": run_dry_run_cleanup,

    # Analysis
    "find-non-followers": run_find_non_followers,
    "find-reposts": run_find_reposts,
    "find-likes-by-date": run_find_likes_by_date,
    "find-posts-by-date": run_find_posts_by_date,

    # Actions
    "bulk-unlike": run_bulk_unlike,
    "bulk-unlike-candidates": run_bulk_unlike_candidates,
    "bulk-unfollow": run_bulk_unfollow,
    "bulk-unfollow-non-followers": run_bulk_unfollow_non_followers,
    "bulk-unrepost": run_bulk_unrepost,
    "bulk-delete-posts": run_bulk_delete_posts_by_date,
}


def get_workflow(name):
    """
    Retrieve a workflow function by name.
    """
    if name not in WORKFLOWS:
        raise ValueError(
            f"Unknown workflow '{name}'. "
            f"Available workflows: {list(WORKFLOWS.keys())}"
        )
    return WORKFLOWS[name]


def list_workflows():
    """
    Return all available workflow names.
    """
    return list(WORKFLOWS.keys())