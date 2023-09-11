import httpx
from fastapi import APIRouter, HTTPException

# Create a router
ParserRoute = APIRouter()


@ParserRoute.get("/parse")
async def parse():
    pass


@ParserRoute.get("/handle_github_url")
async def handle_github_url(github_url: str) -> dict:
    try:
        client = httpx.AsyncClient()
        # check that the url is a github url
        if "github.com" not in github_url:
            raise HTTPException(
                status_code=404,
                detail={
                    "proc_err_msg": "URL is not a valid GitHub URL",
                    "github_url": github_url,
                },
            )

        # Extract owner and repo from the URL
        # Assuming the URL is like: https://github.com/owner/repo
        parts = github_url.split("/")
        if len(parts) < 5 or parts[2] != "github.com":
            raise HTTPException(
                status_code=404,
                detail={
                    "proc_err_msg": "Invalid GitHub URL format",
                    "github_url": github_url,
                },
            )
        owner, repo = parts[3], parts[4]

        # get content from url
        url_content: list[dict] = await read_github_content(github_url, owner, repo)
        if not url_content:
            raise HTTPException(
                status_code=404,
                detail={
                    "proc_err_msg": "Empty file content received from GitHub",
                    "github_url": github_url,
                },
            )
        # url_content = await fetch_directory(github_url)
        repo_contents = {
            "package_owner": owner,
            "package_name": repo,
            "contents": {},
        }
        repo_contents["contents"]: dict = await parse_github_content(
            url_content, owner, repo
        )
        if repo_contents:
            return {
                "status": "success",
                "message": "Proc - Success",
                "results": repo_contents,
            }

        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "proc_err_msg": "Could not parse content returned from GitHub",
                    "github_url": github_url,
                },
            )
    except HTTPException as exc:
        # Handle network errors
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "proc_err_msg": f'Error requesting GitHub URL: {exc.detail["proc_err_msg"]}',
                "github_url": github_url,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "proc_err_msg": "An error occurred while processing the GitHub URL",
                "github_url": github_url,
            },
        ) from exc
    finally:
        await client.aclose()


async def read_github_content(
    url: str, owner: str, repo: str, path: str = ""
) -> list[dict]:
    try:
        client = httpx.AsyncClient()

        # Construct the API URL
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

        headers = {
            "Accept": "application/vnd.github.v3+json",
            # Uncomment and set your token if you have one
            # "Authorization": "your token here",
        }

        response = await client.get(api_url, headers=headers, follow_redirects=False)

        if response.status_code == 200:
            json_data = response.json()
            if not json_data:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "proc_err_msg": "No data returned from GitHub API",
                        "url": url,
                        "api_url": api_url,
                    },
                )

            # Remove unnecessary data from the response
            for item in json_data:
                item.pop("sha", None)
                item.pop("url", None)
                item.pop("git_url", None)
                item.pop("_links", None)

            return json_data
        else:
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "proc_err_msg": "GitHub API returned 404",
                        "url": url,
                        "api_url": api_url,
                    },
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "proc_err_msg": "GitHub API returned an error",
                        "url": url,
                        "api_url": api_url,
                        "status_code": response.status_code,
                    },
                )
    except httpx.RequestError as exc:
        # Handle network errors
        raise HTTPException(
            status_code=500,
            detail={
                "proc_err_msg": "Error while attempting to set up request url & headers",
                "url": url,
                "api_url": api_url,
            },
        ) from exc


async def parse_github_content(file_content, owner, repo) -> dict:
    try:
        # Check that the file content is a list
        if not file_content or not isinstance(file_content, list):
            raise HTTPException(
                status_code=500,
                detail={
                    "proc_err_msg": "Invalid file content format",
                    "file_content": file_content,
                },
            )

        # Process directories
        results = {}
        directories: list = [item for item in file_content if item["type"] == "dir"]
        files: list = [item for item in file_content if item["type"] == "file"]

        for dir in directories:
            dir_content = await read_github_content("", owner, repo, dir["path"])
            parsed_dir_content = await parse_github_content(dir_content, owner, repo)
            dir_name = dir["name"]
            results[dir_name] = parsed_dir_content

        # Process files
        top_files = []
        for file in files:
            file_name = file["name"]
            top_files.append(file_name)

        if top_files:
            results["files"] = top_files

        return results
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "proc_err_msg": "Error when parsing GitHub content",
                "file_content": file_content,
            },
        ) from exc
