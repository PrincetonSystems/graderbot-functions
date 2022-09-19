import json

def handle(req, syscall):
    login = req['login']
    req = req['payload']
    enrollments = json.loads(syscall.read_key(bytes(f"{req['course']}/enrollments.json", "utf-8")).decode("utf-8"))
    if not (enrollments.get(login) and enrollments.get(login)["type"] == "Staff"):
        return { "error": "Only course staff can view grades" }

    users = syscall.read_dir(f"{req['course']}/assignments/{req['assignment']}/")
    results = {}
    for user in users:
        repo = syscall.read_key(bytes(f"cos316-f22/assignments/{req['assignment']}/{user}", "utf-8")).decode('utf-8')
        grades = map(lambda g: g["grade"],
            map(json.loads,
                map(lambda s: syscall.read_key(bytes(f"github/{repo}/{s}grade.json", 'utf-8')).decode('utf-8'),
                    filter(lambda e: e != 'refs/' and e.endswith('/'), syscall.read_dir(f"github/{repo}"))
                )
            )
        )
        results[user] = max(grades)
    return { "results": results }

