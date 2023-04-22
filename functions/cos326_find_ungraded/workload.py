import json

def handle(req, syscall):
    login = req["login"]
    req = req["payload"]

    enrollments = json.loads(syscall.read_key(bytes(f"{req['course']}/enrollments.json", "utf-8")))
    if not (login in enrollments and enrollments[login]["type"] == "Staff"):
        return { "error": "Only course staff can view submissions" }
    assignments = json.loads(syscall.read_key(bytes(f"{req['course']}/assignments", "utf-8")))
    if req["asgn"] not in assignments:
        return { "error": "Could not find assignment" }

    repo_to_emails = {}
    for email in enrollments:
        if enrollments[email]["type"] != "StudentEnrollment":
            continue

        repo = syscall.read_key(bytes(f"{req['course']}/assignments/{req['asgn']}/{email}", "utf-8")).decode("utf-8")
        if repo == "":
            continue
        if repo in repo_to_emails:
            repo_to_emails[repo].append(email)
            continue

        all_keys = list(syscall.read_dir(f"github/{repo}"))
        if "extra" in all_keys:
            continue
        commits = [key for key in all_keys if key.endswith("/") and key != "refs/"]
        if len(commits) > 1: # assumes graderbot commit always exists
            repo_to_emails[repo] = [email]

    results = []
    for repo, emails in repo_to_emails.items():
        students = " ".join([f"{email[:-14]} {enrollments[email]['name']}" for email in emails])
        results.append(f"https://github.com/{repo} {students}")
    return { "results": results }
