import json
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

def get_repo_collaborators(access_token, org_name, repo_name):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def fetch_collaborators():
        response = requests.get(f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators", headers=headers)
        response.raise_for_status()
        return response.json()

    return fetch_collaborators()

def get_repositories_with_secrets_and_collaborators(access_token, org_name):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    repos_with_secrets_and_collaborators = []

    page = 1
    while True:
        response = requests.get(f"https://api.github.com/orgs/{org_name}/repos?page={page}", headers=headers)
        response.raise_for_status()
        repos = response.json()

        if not repos:
            break

        for repo in repos:
            secrets_response = requests.get(f"https://api.github.com/repos/{org_name}/{repo['name']}/actions/secrets", headers=headers)
            secrets_response.raise_for_status()
            secrets_data = secrets_response.json()

            if secrets_data.get('total_count', 0) > 0:
                secrets_info = {
                    "name": repo["name"],
                    "private": repo["private"],
                    "secrets": [],
                    "collaborators": []
                }

                # Paginate through secrets
                secrets_page = 1
                while True:
                    secrets_response = requests.get(f"https://api.github.com/repos/{org_name}/{repo['name']}/actions/secrets", headers=headers, params={"page": secrets_page})
                    secrets_response.raise_for_status()
                    secrets_data = secrets_response.json()

                    secrets_info["secrets"].extend([secret["name"] for secret in secrets_data["secrets"]])

                    if len(secrets_data["secrets"]) == 0:
                        break

                    secrets_page += 1

                # Get collaborators
                collaborators = get_repo_collaborators(access_token, org_name, repo["name"])
                for collaborator in collaborators:
                    if collaborator["permissions"]["admin"] or collaborator["permissions"]["maintain"]:
                        role = "admin" if collaborator["permissions"]["admin"] else "maintainer"
                        secrets_info["collaborators"].append({
                            "login": collaborator["login"],
                            "role": role
                        })

                if secrets_info["collaborators"]:  # Check if collaborators list is not empty
                    repos_with_secrets_and_collaborators.append(secrets_info)

        page += 1

    return repos_with_secrets_and_collaborators

def main():
    with open("github_config.json") as config_file:
        config = json.load(config_file)

    access_token = config["access_token"]
    org_name = config["org_name"]

    repos_with_secrets_and_collaborators = get_repositories_with_secrets_and_collaborators(access_token, org_name)

    with open("repos_with_secrets_and_collaborators.json", "w") as output_file:
        json.dump(repos_with_secrets_and_collaborators, output_file, indent=4)

if __name__ == "__main__":
    main()
