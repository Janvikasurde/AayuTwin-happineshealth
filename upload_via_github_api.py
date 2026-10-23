"""
AAYU-TWIN GitHub API Direct Uploader (Zero Git Required)
=========================================================
Uploads the entire AAYU-TWIN project directly to GitHub using GitHub's REST API.
Does NOT require Git to be installed!
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def make_request(url, method="GET", data=None, token=None):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AayuTwin-Publisher"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    req_body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_text = response.read().decode("utf-8")
            return json.loads(res_text) if res_text else {}, response.status
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        return {"error": err_msg}, e.code

def create_or_verify_repo(token, repo_name):
    # Check if repo exists
    user_info, code = make_request("https://api.github.com/user", token=token)
    if code != 200:
        print(f"Error authenticating with GitHub token: {user_info.get('error', 'Invalid token')}")
        return None, None
    
    username = user_info["login"]
    repo_info, code = make_request(f"https://api.github.com/repos/{username}/{repo_name}", token=token)
    if code == 200:
        print(f"Repository '{username}/{repo_name}' already exists. Updating files...")
        return username, repo_name
    
    # Create public repository
    print(f"Creating new Public repository: {repo_name}...")
    new_repo, code = make_request("https://api.github.com/user/repos", method="POST", data={
        "name": repo_name,
        "description": "Multi-Scale Healthcare Digital Twin for the Indian Phenotype (Happiest Health 2026)",
        "private": False,
        "auto_init": False
    }, token=token)
    
    if code in (200, 201):
        print("Repository successfully created!")
        return username, repo_name
    else:
        print(f"Failed to create repo: {new_repo}")
        return None, None

def upload_file(username, repo_name, token, file_path, rel_path):
    with open(file_path, "rb") as f:
        content_bytes = f.read()
    b64_content = base64.b64encode(content_bytes).decode("utf-8")
    
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{rel_path}"
    
    # Check if file already exists to get its SHA
    existing, code = make_request(url, token=token)
    sha = existing.get("sha") if code == 200 else None
    
    payload = {
        "message": f"Upload {rel_path} for Happiest Health 2026",
        "content": b64_content
    }
    if sha:
        payload["sha"] = sha
        
    res, status = make_request(url, method="PUT", data=payload, token=token)
    if status in (200, 201):
        print(f"  ✓ Uploaded: {rel_path}")
        return True
    else:
        print(f"  ✗ Failed: {rel_path} - {res.get('error', '')}")
        return False

def main():
    print("===========================================================")
    print("  AAYU-TWIN Direct GitHub API Uploader (Zero Git Needed)")
    print("  Happiest Health Digital Twin Challenge 2026")
    print("===========================================================")
    print(f"Directory: {BASE_DIR}\n")
    
    print("To upload via API, you need a GitHub Personal Access Token.")
    print("1. Go to: https://github.com/settings/tokens/new")
    print("2. Set Note: 'AayuTwin', Expiration: 7 days, check 'repo' scope.")
    print("3. Click 'Generate token' and paste it below.\n")
    
    token = input("Enter your GitHub Personal Access Token:\n> ").strip()
    if not token:
        print("No token provided. Exiting.")
        return
        
    repo_name = input("\nEnter repository name (default: AayuTwin_HappiestHealth2026):\n> ").strip()
    if not repo_name:
        repo_name = "AayuTwin_HappiestHealth2026"
        
    username, repo = create_or_verify_repo(token, repo_name)
    if not username:
        return
        
    print(f"\nStarting upload to https://github.com/{username}/{repo}...\n")
    
    success_count = 0
    total_count = 0
    
    # Walk and upload all files
    for root, dirs, files in os.walk(BASE_DIR):
        # Skip pycache or git metadata
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".github")]
        for file in files:
            if file.endswith((".pyc", ".zip", ".log")):
                continue
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, BASE_DIR).replace("\\", "/")
            total_count += 1
            if upload_file(username, repo, token, abs_path, rel_path):
                success_count += 1
                
    print(f"\n===========================================================")
    print(f" Upload Complete: {success_count}/{total_count} files successfully uploaded!")
    print(f" Public Repository URL:")
    print(f" https://github.com/{username}/{repo}")
    print("===========================================================")

if __name__ == "__main__":
    main()
