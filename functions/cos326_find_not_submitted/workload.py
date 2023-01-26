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

    results = []
    for email in enrollments:
        if enrollments[email]["type"] != "StudentEnrollment":
            continue

        repo = syscall.read_key(bytes(f"{req['course']}/assignments/{req['asgn']}/{email}", "utf-8")).decode("utf-8")
        if repo == "":
            results.append(f"{email[:-14]} has not created an assignment repo")
            continue

        all_keys = syscall.read_dir(f"github/{repo}")
        commits = [key for key in all_keys if key.endswith("/") and key != "refs/"]
        if len(commits) < 2: # assumes graderbot commit always exists
            results.append(f"{email[:-14]} does not have any submission")

    return { "results": results }
