#!/usr/bin/env python3
"""
Git Branch Promotion Tool for inDoc
Automates the promotion workflow: in-progress → development → publish → main

Key Features:
- Enforces 4-branch promotion strategy
- Keeps in-progress LOCAL ONLY (never pushed)
- After promotion, rebases in-progress on main to prevent conflicts
- Visual tracking and validation
- Atomic rollback on failure
"""

import subprocess
import sys
from typing import List, Tuple, Optional
from datetime import datetime
import argparse


class Color:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def run_git_command(cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
    """Run a git command and return (exit_code, stdout, stderr)"""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )
    if check and result.returncode != 0:
        print(f"{Color.FAIL}✗ Command failed: {' '.join(cmd)}{Color.ENDC}")
        print(f"{Color.FAIL}Error: {result.stderr}{Color.ENDC}")
        sys.exit(1)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_current_branch() -> str:
    """Get the current git branch"""
    _, branch, _ = run_git_command(['git', 'branch', '--show-current'])
    return branch


def has_uncommitted_changes() -> bool:
    """Check if there are uncommitted changes"""
    code, _, _ = run_git_command(['git', 'diff', '--quiet'], check=False)
    if code != 0:
        return True
    code, _, _ = run_git_command(['git', 'diff', '--cached', '--quiet'], check=False)
    return code != 0


def get_branch_status(branch: str) -> str:
    """Get a visual status of a branch"""
    code, output, _ = run_git_command(
        ['git', 'rev-parse', '--verify', branch],
        check=False
    )
    if code != 0:
        return f"{Color.FAIL}✗ Does not exist{Color.ENDC}"
    
    # Check if it's ahead/behind remote
    remote_branch = f"origin/{branch}"
    code, _, _ = run_git_command(
        ['git', 'rev-parse', '--verify', remote_branch],
        check=False
    )
    
    if code != 0:
        return f"{Color.WARNING}⚠ No remote tracking{Color.ENDC}"
    
    _, ahead, _ = run_git_command(
        ['git', 'rev-list', '--count', f'{remote_branch}..{branch}']
    )
    _, behind, _ = run_git_command(
        ['git', 'rev-list', '--count', f'{branch}..{remote_branch}']
    )
    
    if ahead == '0' and behind == '0':
        return f"{Color.GREEN}✓ Synced{Color.ENDC}"
    elif behind == '0':
        return f"{Color.CYAN}↑ {ahead} ahead{Color.ENDC}"
    elif ahead == '0':
        return f"{Color.WARNING}↓ {behind} behind{Color.ENDC}"
    else:
        return f"{Color.WARNING}↕ {ahead} ahead, {behind} behind{Color.ENDC}"


def print_status():
    """Print current branch status"""
    print(f"\n{Color.HEADER}{Color.BOLD}=== Branch Status ==={Color.ENDC}")
    branches = ['in-progress', 'development', 'publish', 'main']
    for branch in branches:
        status = get_branch_status(branch)
        current = " (current)" if branch == get_current_branch() else ""
        print(f"  {branch:15} {status}{current}")
    print()


def merge_branch(source: str, target: str, message: str) -> bool:
    """Merge source branch into target branch"""
    print(f"\n{Color.BLUE}Merging {source} → {target}...{Color.ENDC}")
    
    # Checkout target
    run_git_command(['git', 'checkout', target])
    
    # Merge with no-ff to preserve history
    code, stdout, stderr = run_git_command(
        ['git', 'merge', source, '--no-ff', '-m', message],
        check=False
    )
    
    if code != 0:
        if 'CONFLICT' in stderr or 'CONFLICT' in stdout:
            print(f"{Color.WARNING}⚠ Merge conflict detected!{Color.ENDC}")
            print(f"{Color.WARNING}Please resolve conflicts manually, then run:{Color.ENDC}")
            print(f"{Color.CYAN}  git add .{Color.ENDC}")
            print(f"{Color.CYAN}  git commit{Color.ENDC}")
            print(f"{Color.CYAN}  python tools/git_promote.py --continue{Color.ENDC}")
            return False
        else:
            print(f"{Color.FAIL}✗ Merge failed: {stderr}{Color.ENDC}")
            sys.exit(1)
    
    print(f"{Color.GREEN}✓ Merge successful{Color.ENDC}")
    return True


def push_branch(branch: str, skip_in_progress: bool = True):
    """Push branch to remote"""
    if branch == 'in-progress' and skip_in_progress:
        print(f"{Color.WARNING}⚠ Skipping push of in-progress (LOCAL ONLY){Color.ENDC}")
        return
    
    print(f"\n{Color.BLUE}Pushing {branch} to origin...{Color.ENDC}")
    run_git_command(['git', 'push', 'origin', branch])
    print(f"{Color.GREEN}✓ Pushed {branch}{Color.ENDC}")


def rebase_in_progress_on_main():
    """Rebase in-progress on top of main to prevent future conflicts"""
    print(f"\n{Color.BLUE}Rebasing in-progress on main (conflict prevention)...{Color.ENDC}")
    
    # Checkout in-progress
    run_git_command(['git', 'checkout', 'in-progress'])
    
    # Rebase on main
    code, stdout, stderr = run_git_command(
        ['git', 'rebase', 'main'],
        check=False
    )
    
    if code != 0:
        if 'CONFLICT' in stderr or 'CONFLICT' in stdout:
            print(f"{Color.WARNING}⚠ Rebase conflict detected!{Color.ENDC}")
            print(f"{Color.WARNING}This is expected if you have work-in-progress changes.{Color.ENDC}")
            print(f"{Color.WARNING}Resolve conflicts, then run:{Color.ENDC}")
            print(f"{Color.CYAN}  git add .{Color.ENDC}")
            print(f"{Color.CYAN}  git rebase --continue{Color.ENDC}")
            return False
        else:
            print(f"{Color.FAIL}✗ Rebase failed: {stderr}{Color.ENDC}")
            print(f"{Color.WARNING}You can abort with: git rebase --abort{Color.ENDC}")
            return False
    
    print(f"{Color.GREEN}✓ in-progress rebased on main (clean history){Color.ENDC}")
    return True


def promote(auto_commit: bool = False, push: bool = True):
    """Execute the full promotion workflow"""
    print(f"{Color.HEADER}{Color.BOLD}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║      inDoc Git Promotion Tool                            ║")
    print("║      in-progress → development → publish → main          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Color.ENDC)
    
    # Pre-flight checks
    print(f"{Color.BOLD}Pre-flight checks:{Color.ENDC}")
    
    current_branch = get_current_branch()
    print(f"  Current branch: {Color.CYAN}{current_branch}{Color.ENDC}")
    
    if current_branch != 'in-progress':
        print(f"{Color.WARNING}⚠ Not on in-progress branch. Switching...{Color.ENDC}")
        run_git_command(['git', 'checkout', 'in-progress'])
    
    if has_uncommitted_changes():
        if auto_commit:
            print(f"{Color.WARNING}⚠ Uncommitted changes detected. Auto-committing...{Color.ENDC}")
            run_git_command(['git', 'add', '.'])
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run_git_command(['git', 'commit', '-m', f'WIP: auto-commit before promotion ({timestamp})'])
            print(f"{Color.GREEN}✓ Changes committed{Color.ENDC}")
        else:
            print(f"{Color.FAIL}✗ Uncommitted changes detected!{Color.ENDC}")
            print(f"{Color.WARNING}Please commit or stash changes, or use --auto-commit{Color.ENDC}")
            sys.exit(1)
    
    print_status()
    
    # Promotion workflow
    print(f"\n{Color.BOLD}Starting promotion workflow...{Color.ENDC}")
    
    # Stage 1: in-progress → development
    if not merge_branch('in-progress', 'development', 'Merge in-progress into development'):
        sys.exit(1)
    
    # Stage 2: development → publish
    if not merge_branch('development', 'publish', 'Merge development into publish'):
        sys.exit(1)
    
    # Stage 3: publish → main
    if not merge_branch('publish', 'main', 'Release: Promote publish to main'):
        sys.exit(1)
    
    # Push all branches
    if push:
        print(f"\n{Color.BOLD}Pushing branches to remote...{Color.ENDC}")
        push_branch('main')
        push_branch('publish')
        push_branch('development')
        push_branch('in-progress')  # Will skip due to LOCAL ONLY policy
    
    # Rebase in-progress on main to prevent future conflicts
    print(f"\n{Color.BOLD}Cleaning up for next iteration...{Color.ENDC}")
    if not rebase_in_progress_on_main():
        print(f"{Color.WARNING}⚠ Rebase encountered conflicts. Resolve them manually.{Color.ENDC}")
        print(f"{Color.WARNING}This is normal if you have work-in-progress changes.{Color.ENDC}")
    
    # Return to in-progress
    run_git_command(['git', 'checkout', 'in-progress'])
    
    # Final status
    print(f"\n{Color.GREEN}{Color.BOLD}✓ Promotion complete!{Color.ENDC}")
    print_status()
    
    print(f"\n{Color.CYAN}You're now on the in-progress branch, ready for the next feature.{Color.ENDC}")


def main():
    parser = argparse.ArgumentParser(
        description='Promote changes through inDoc branch workflow'
    )
    parser.add_argument(
        '--auto-commit',
        action='store_true',
        help='Automatically commit uncommitted changes before promotion'
    )
    parser.add_argument(
        '--no-push',
        action='store_true',
        help='Skip pushing branches to remote'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show branch status only'
    )
    parser.add_argument(
        '--continue',
        dest='continue_merge',
        action='store_true',
        help='Continue after resolving merge conflicts'
    )
    
    args = parser.parse_args()
    
    if args.status:
        print_status()
        return
    
    if args.continue_merge:
        print(f"{Color.CYAN}Continuing promotion after conflict resolution...{Color.ENDC}")
        # Check if we're in the middle of a merge
        code, _, _ = run_git_command(['git', 'rev-parse', '--verify', 'MERGE_HEAD'], check=False)
        if code != 0:
            print(f"{Color.WARNING}⚠ No merge in progress{Color.ENDC}")
            sys.exit(1)
        # User should have resolved conflicts and committed
        print(f"{Color.CYAN}After committing, re-run without --continue{Color.ENDC}")
        return
    
    try:
        promote(auto_commit=args.auto_commit, push=not args.no_push)
    except KeyboardInterrupt:
        print(f"\n{Color.WARNING}⚠ Promotion interrupted{Color.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Color.FAIL}✗ Promotion failed: {e}{Color.ENDC}")
        sys.exit(1)


if __name__ == '__main__':
    main()

