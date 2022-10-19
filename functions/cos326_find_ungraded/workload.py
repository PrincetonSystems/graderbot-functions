from datetime import datetime, timezone
import json

def handle(req, syscall):
    login = req["login"]
    req = req["payload"]

    enrollments = json.loads(syscall.read_key(bytes(f"{req['course']}/enrollments.json", "utf-8")))
    if login not in enrollments or enrollments.get(login)["type"] != "Staff":
        return { "error": "Only course staff can view grades" }
    assignments = json.loads(syscall.read_key(bytes(f"{req['course']}/assignments", "utf-8")))
    if req["asgn"] not in assignments:
        return { "error": "Could not find assignment" }

    all_repos = syscall.read_dir(f"github/{req['course']}")
    assignment_repos = [repo for repo in all_repos if repo.startswith(req["asgn"] + "-")]

    results = []
    for repo in assignment_repos:
        # skip repos for students that dropped and staff repos
        meta = syscall.read_key(bytes(f"github/{req['course']}/{repo}_meta", "utf-8"))
        if meta == b"":
            continue
        email = json.loads(meta)["users"][0] # assumes one user only
        if email not in enrollments or enrollments.get(email)["type"] == "Staff":
            continue

        # find all commits of repo if it is ungraded
        all_keys = list(syscall.read_dir(f"github/{req['course']}/{repo}"))
        if "extra_grades" in all_keys:
            continue
        commits = [key for key in all_keys if key.endswith("/") and key != "refs/"]

        # find latest commit of repo
        pairs = []
        for commit in commits:
            grade = syscall.read_key(bytes(f"github/{req['course']}/{repo}{commit}grade.json", "utf-8"))
            if grade == b"":
                continue
            push_date = json.loads(grade)["push_date"]
            pairs.append((push_date, commit))
        pairs.sort(key=lambda t: t[0], reverse=True)

        # only template repos should have not graded commits
        # exclude repos that don't have any student commits
        if len(pairs) > 1:
            results.append(f"https://github.com/{req['course']}/{repo}commit/{pairs[0][1].strip('/')} {email[:-14]} {enrollments.get(email)['name']} {datetime.utcfromtimestamp(pairs[0][0]).replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%D %T %z')}")

    return { "results": results }
