import json
import re

def handle(req, syscall):
    args = req["args"]
    workflow = req["workflow"]
    context = req["context"]
    result = app_handle(args, context, syscall)
    if len(workflow) > 0:
        next_function = workflow.pop(0)
        syscall.invoke(next_function, json.dumps({
            "args": result,
            "workflow": workflow,
            "context": context
        }))
    return result

def app_handle(args, context, syscall):
    key = f"github/{context['repository']}/extra_grades"
    api_route = f"/repos/{context['repository']}/commits/{context['commit']}/comments"

    github_user = context["user"]
    user_email = syscall.read_key(bytes(f"users/github/from/{github_user}", "utf-8")).decode("utf-8").strip()

    org_name = context["repository"].split("/")[0]
    enrollment = json.loads(syscall.read_key(bytes(f"{org_name}/enrollments.json", "utf-8")))

    user = enrollment.get(user_email)
    if not user:
        return {}

    extra = json.loads(syscall.read_key(bytes(key, "utf-8")) or "{}")
    p1 = re.compile(r" *grade +(\w+) +([+-]?\d+)( */ *(\d+))?", re.IGNORECASE)
    p2 = re.compile(r" *special +note: +(.+)", re.IGNORECASE)
    for num, line in enumerate(args["comment"].splitlines()):
        # end of header indicator
        if line == "":
            break

        match = p1.match(line)
        if match:
            grade = { "earned": int(match.group(2)) }
            if match.group(4):
                grade["total"] = int(match.group(4))
            extra[match.group(1).lower()] = grade
            continue

        match = p2.match(line)
        if match:
            extra.setdefault("special note", []).append(match.group(1))
            continue

        # could not match header line to any pattern
        if user["type"] == "Staff":
            body = {
                "body": (f"Unable to parse comment line number {num+1}.\n"
                         f"@{github_user}, make sure the line is formatted correctly.")
            }
            syscall.github_rest_post(api_route, body)
        return {}

    if user["type"] == "Staff":
        if "repo graders" in extra:
            extra["repo graders"] = list(set(extra["repo graders"]) | {github_user})
        else:
            extra["repo graders"] = [github_user]
        extra["commit graded"] = context["commit"]
        syscall.write_key(bytes(key, "utf-8"), bytes(json.dumps(extra), "utf-8"))
        return { "remarks": key }
    else:
        instructors = json.loads(syscall.read_key(bytes(f"{org_name}/instructors", "utf-8")))
        instructor_githubs = [syscall.read_key(bytes(f"users/github/for/user/{instructor}", "utf-8")).decode("utf-8").strip() for instructor in instructors]
        github_mentions = ", ".join([f"@{user}" for user in instructor_githubs])

        body = {
            "body": (f"@{github_user}, are you looking for trouble?\n"
                     f"{github_mentions}, there has been an unauthorized"
                      " attempt at creating a grader comment.")
        }
        syscall.github_rest_post(api_route, body)
        return {}
