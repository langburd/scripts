"""
Clones or updates all private or internal repositories from a GitHub
organization.
"""

import os
import subprocess
import sys

import requests

# Configuration from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORGANIZATION = os.getenv("ORGANIZATION")
TARGET_DIRECTORY = os.getenv("TARGET_DIRECTORY")


def get_repositories(org):
    """
    Fetches the list of private or internal repositories from the specified
    organization.

    :param org: GitHub organization name
    :return: List of repository names
    """
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
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
            print("Request timed out. Please check your network connection and " "try again.")
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
    if not GITHUB_TOKEN or not ORGANIZATION or not TARGET_DIRECTORY:
        print(
            "Please ensure that GITHUB_TOKEN, ORGANIZATION, "
            "and TARGET_DIRECTORY environment variables are set."
        )
        sys.exit(1)

    repositories = get_repositories(ORGANIZATION)
    clone_or_pull_repositories(repositories)
