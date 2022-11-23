from datetime import datetime, timezone
import json

def handle(req, syscall):
    login = req["login"]
    req = req["payload"]

    enrollments = json.loads(syscall.read_key(bytes(f"{req['course']}/enrollments.json", "utf-8")))
    if login not in enrollments or enrollments.get(login)["type"] != "Staff":
        return { "error": "Only course staff can view submissions" }
    assignments = json.loads(syscall.read_key(bytes(f"{req['course']}/assignments", "utf-8")))
    if req["asgn"] not in assignments:
        return { "error": "Could not find assignment" }

    repo_to_email = {}
    repo_to_commit = {}
    for email in enrollments:
        # skip staff repos
        if enrollments.get(email)["type"] == "Staff":
            continue

        repo = syscall.read_key(bytes(f"{req['course']}/assignments/{req['asgn']}/{email}", "utf-8")).decode("utf-8")
        if repo == "":
            continue
        if repo in repo_to_email:
            repo_to_email[repo].append(email)
            continue

        # find all repo commits if it is ungraded
        all_keys = list(syscall.read_dir(f"github/{repo}"))
        if "extra_grades" in all_keys:
            continue
        commits = [key for key in all_keys if key.endswith("/") and key != "refs/"]
        if len(commits) < 2: # assumes graderbot commit always exists
            continue

        # find latest commit of repo
        pairs = []
        for commit in commits:
            grade = syscall.read_key(bytes(f"github/{repo}/{commit}grade.json", "utf-8"))
            if grade == b"":
                continue
            pairs.append((json.loads(grade)["push_date"], commit))
        pairs.sort(key=lambda t: t[0], reverse=True)

        # only template repos should have no graded commits
        if len(pairs) > 1:
            repo_to_email[repo] = [email]
            repo_to_commit[repo] = pairs[0][1].strip('/')

    results = []
    for repo, emails in repo_to_email.items():
        students = " ".join([f"{email[:-14]} {enrollments.get(email)['name']}" for email in emails])
        results.append(f"https://github.com/{repo}/commit/{repo_to_commit[repo]} {students} {datetime.utcfromtimestamp(pairs[0][0]).replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%D %T %z')}")
    return { "results": results }
