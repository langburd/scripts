"""
Clones or updates all private or internal repositories from a GitHub
organization using browser-based bearer token authentication.

This script uses a bearer token extracted from browser developer tools instead
of a GitHub API token (Personal Access Token). This can be useful when you need
to access repositories using your browser session credentials.

================================================================================
HOW TO OBTAIN A BROWSER BEARER TOKEN:
================================================================================

IMPORTANT: GitHub's web interface primarily uses COOKIES for authentication,
NOT bearer tokens. Bearer tokens are only present in specific API requests.
Follow these steps carefully to find requests that contain bearer tokens.

1. LOG INTO GITHUB:
   - Open your web browser and log into GitHub (https://github.com)
   - Make sure you're logged into the account that has access to the
     organization's private/internal repositories

2. OPEN DEVELOPER TOOLS:
   - Press F12 (or Cmd+Option+I on Mac) to open Developer Tools
   - Alternatively: Right-click → "Inspect" → "Network" tab

3. NAVIGATE TO THE NETWORK TAB:
   - Click on the "Network" tab in Developer Tools
   - Make sure "All" or "Fetch/XHR" filter is selected
   - IMPORTANT: Check "Preserve log" to keep requests across page navigations

4. TRIGGER REQUESTS THAT USE BEARER TOKENS:
   GitHub uses bearer tokens in specific scenarios. Try these actions:

   BEST OPTIONS (most likely to show bearer tokens):
   * GitHub CLI in browser: Visit https://cli.github.com and click "Download"
   * GitHub Mobile setup: Go to Settings → Mobile → scan QR code flow
   * OAuth App authorization: Visit any GitHub OAuth app authorization page
   * GitHub Desktop: If installed, check its network requests

   OTHER OPTIONS (may show bearer tokens):
   * GraphQL Explorer: https://docs.github.com/en/graphql/overview/explorer
   * GitHub Actions: Trigger a workflow run and watch for API calls
   * GitHub Codespaces: Start/stop a codespace
   * GitHub Copilot settings: https://github.com/settings/copilot

5. FILTER AND FIND THE AUTHORIZATION HEADER:
   - In the Network tab filter box, type: "api.github.com" or "graphql"
   - Click on each request and check the "Headers" tab
   - Look in "Request Headers" section for:
     Authorization: Bearer gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     OR
     Authorization: token ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

   TOKEN PREFIXES:
   * gho_ = OAuth token (from browser/OAuth apps)
   * ghp_ = Personal Access Token
   * ghs_ = GitHub App server-to-server token
   * ghu_ = GitHub App user-to-server token

6. COPY THE TOKEN:
   - Copy only the token value (the part after "Bearer " or "token ")
   - Set it as the GITHUB_BEARER_TOKEN environment variable

================================================================================
TROUBLESHOOTING - IF YOU CAN'T FIND THE AUTHORIZATION HEADER:
================================================================================

PROBLEM: Most requests show "Cookie" header but no "Authorization" header

EXPLANATION: GitHub's web interface uses cookie-based session authentication
for most requests. Bearer tokens are only used for specific API integrations.

SOLUTIONS:

1. USE GITHUB'S GRAPHQL EXPLORER (RECOMMENDED):
   - Visit: https://docs.github.com/en/graphql/overview/explorer
   - Sign in if prompted
   - Open DevTools Network tab BEFORE clicking any button
   - Click "Run" or execute any query
   - Look for requests to "api.github.com/graphql"
   - The Authorization header should be present

2. CHECK GITHUB CLI AUTHENTICATION:
   If you have GitHub CLI (gh) installed:
   $ gh auth token
   This will print your token directly (works if you've logged in via gh)

3. USE GITHUB'S API DIRECTLY IN BROWSER CONSOLE:
   Open browser console (F12 → Console) on any GitHub page and run:

   fetch('https://api.github.com/user', {
     headers: { 'Accept': 'application/json' },
     credentials: 'include'
   }).then(r => r.json()).then(console.log)

   Then check the Network tab - some browsers may show auth headers.

4. BROWSER EXTENSIONS THAT MAY HIDE HEADERS:
   - Privacy Badger, uBlock Origin, AdBlock may filter requests
   - Try in Incognito/Private mode with extensions disabled
   - Some corporate proxies strip or modify headers

5. USE A DIFFERENT BROWSER:
   - Firefox DevTools may show different details than Chrome
   - Safari's Web Inspector has a different layout

6. CHECK IF YOUR ORG USES SAML/SSO:
   - Organizations with SAML SSO may require special token authorization
   - You may need to authorize the token for SSO after creation
   - Check: https://github.com/settings/tokens → Configure SSO

================================================================================
ALTERNATIVE: EXTRACT SESSION COOKIE (ADVANCED, USE WITH CAUTION)
================================================================================

If bearer tokens are unavailable, you might extract the session cookie:
1. Find the "Cookie" header in request headers
2. Look for "_gh_sess" or "user_session" values
3. Note: Cookie-based auth is NOT recommended for API access and may not work
   with api.github.com endpoints - this script uses bearer tokens by design.

================================================================================
IMPORTANT LIMITATIONS AND CONSIDERATIONS:
================================================================================

- EXPIRATION: Browser tokens are session-based and will expire when:
  * You log out of GitHub
  * Your session times out (typically after extended inactivity)
  * GitHub rotates session tokens (can happen periodically)
  * You revoke sessions from GitHub security settings

- SECURITY WARNINGS:
  * Never share or commit bearer tokens - they grant full account access
  * Treat these tokens with the same security as your password
  * Browser tokens may have broader permissions than scoped API tokens

- SCOPE: Browser tokens typically have the same permissions as your logged-in
  session, which may include all repositories and organizations you can access

- RATE LIMITING: GitHub applies rate limits to API requests. Browser tokens
  may have different rate limits than authenticated API tokens

- SSO/SAML ORGANIZATIONS: If your org uses SAML SSO, tokens may need explicit
  SSO authorization. Check token settings if you get 403 errors.

================================================================================
"""

import os
import subprocess
import sys

import requests

# Configuration from environment variables
GITHUB_BEARER_TOKEN = os.getenv("GITHUB_BEARER_TOKEN")
ORGANIZATION = os.getenv("ORGANIZATION")
TARGET_DIRECTORY = os.getenv("TARGET_DIRECTORY")


def get_repositories(org):
    """
    Fetches the list of private or internal repositories from the specified
    organization using browser bearer token authentication.

    :param org: GitHub organization name
    :return: List of repository names
    """
    headers = {
        "Authorization": f"Bearer {GITHUB_BEARER_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/orgs/{org}/repos?type=private"
    repos = []
    page = 1

    while True:
        try:
            response = requests.get(
                url + f"&page={page}", headers=headers, timeout=10
            )  # Added timeout
            if response.status_code != 200:
                print(f"Error fetching repositories: {response.json()}")
                break

            data = response.json()
            if not data:
                break  # No more pages

            for repo in data:
                if repo["private"] or repo.get("visibility", "") == "internal":
                    repos.append(repo["ssh_url"])  # Use SSH URL for cloning

            page += 1

        except requests.exceptions.Timeout:
            print(
                "Request timed out. Please check your network connection and "
                "try again."
            )
            break
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break

    return repos


def clone_or_pull_repositories(repos):
    """
    Clones or updates repositories to the target directory.

    :param repos: List of repository URLs
    """
    if TARGET_DIRECTORY is None:
        raise ValueError("TARGET_DIRECTORY environment variable is not set")

    if not os.path.exists(TARGET_DIRECTORY):
        os.makedirs(TARGET_DIRECTORY)

    os.chdir(TARGET_DIRECTORY)

    for repo_url in repos:
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        if os.path.exists(repo_name):
            print(f"Updating {repo_name}...")
            os.chdir(repo_name)
            try:
                subprocess.run(["git", "pull"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to update {repo_name}: {e}")
            os.chdir("..")
        else:
            print(f"Cloning {repo_name}...")
            try:
                subprocess.run(["git", "clone", repo_url], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone {repo_name}: {e}")


if __name__ == "__main__":
    if not GITHUB_BEARER_TOKEN or not ORGANIZATION or not TARGET_DIRECTORY:
        print(
            "Please ensure that GITHUB_BEARER_TOKEN, ORGANIZATION, "
            "and TARGET_DIRECTORY environment variables are set."
        )
        sys.exit(1)

    repositories = get_repositories(ORGANIZATION)
    clone_or_pull_repositories(repositories)
