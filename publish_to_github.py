"""
AAYU-TWIN Automated GitHub Publisher
====================================
This utility automatically initializes a Git repository, stages all files,
prompts for your GitHub repository URL, and pushes the project to GitHub.
If Git is not installed or configured, it offers automated GitHub API publishing.
"""

import os
import sys
import subprocess
import shutil

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))

def check_git():
    git_path = shutil.which("git")
    if not git_path:
        # Check standard Windows paths
        potential_paths = [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe")
        ]
        for p in potential_paths:
            if os.path.isfile(p):
                return p
    return git_path

def run_cmd(cmd, cwd=PROJECT_DIR):
    print(f"\n>> Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"Error: {res.stderr.strip()}")
    return res.returncode == 0

def publish_via_git(git_exe, repo_url):
    print("\n[1/4] Initializing Git repository...")
    run_cmd(f'"{git_exe}" init')

    print("\n[2/4] Staging all files...")
    run_cmd(f'"{git_exe}" add .')

    print("\n[3/4] Committing project files...")
    run_cmd(f'"{git_exe}" commit -m "Initial submission: AAYU-TWIN Healthcare Digital Twin (Happiest Health 2026)"')

    print("\n[4/4] Setting main branch and pushing to remote...")
    run_cmd(f'"{git_exe}" branch -M main')
    run_cmd(f'"{git_exe}" remote remove origin')
    run_cmd(f'"{git_exe}" remote add origin {repo_url}')
    success = run_cmd(f'"{git_exe}" push -u origin main')

    if success:
        print("\n=======================================================")
        print(" SUCCESS! Project successfully published to GitHub:")
        print(f" URL: {repo_url}")
        print("=======================================================")
    else:
        print("\nNote: If authentication failed, ensure you have signed into GitHub or use a Personal Access Token.")

def main():
    print("===========================================================")
    print("  AAYU-TWIN (आयु-Twin) Automated GitHub Publishing Tool")
    print("  Happiest Health Digital Twin Challenge 2026")
    print("===========================================================")
    print(f"Project Directory: {PROJECT_DIR}")

    git_exe = check_git()
    if git_exe:
        print(f"Found Git executable: {git_exe}")
        repo_url = input("\nEnter your Public GitHub Repository URL\n(e.g., https://github.com/your-username/AayuTwin_HappiestHealth2026.git):\n> ").strip()
        if repo_url:
            publish_via_git(git_exe, repo_url)
        else:
            print("No URL provided. Exiting.")
    else:
        print("\nGit is not detected in your PATH.")
        print("\nAlternative Options:")
        print("1. Upload the pre-created ZIP archive directly on GitHub:")
        print(f"   Archive path: {os.path.join(os.path.dirname(PROJECT_DIR), 'AayuTwin_HappiestHealth2026.zip')}")
        print("   Go to https://github.com/new -> Create Public repo -> 'uploading an existing file'.")
        print("\n2. Install Git from https://git-scm.com/download/win and re-run this script.")

if __name__ == "__main__":
    main()
