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

    github_user = context["user"]
    user_email = syscall.read_key(bytes(f"users/github/from/{github_user}", "utf-8")).decode("utf-8").strip()

    org_name = context["repository"].split("/")[0]
    enrollment = json.loads(syscall.read_key(bytes(f"{org_name}/enrollments.json", "utf-8")))

    user = enrollment.get(user_email)
    if not user or user["type"] != "Staff":
        return {}

    extra = json.loads(syscall.read_key(bytes(key, "utf-8")) or "{}")
    p1 = re.compile(r" *grade +(\w+ +)?([+-]?\d+)( */ *(\d+))?", re.IGNORECASE)
    p2 = re.compile(r" *special +note: +(.+)", re.IGNORECASE)
    for num, line in enumerate(args["comment"].splitlines()):
        if line == "": # end of header indicator
            break
        match = p1.match(line)
        if match:
            grade = { "earned": int(match.group(2)) }
            if match.group(4):
                grade["total"] = int(match.group(4))

            if match.group(1):
                extra[match.group(1).strip().lower()] = grade
            else:
                extra = extra | grade
        else:
            match = p2.match(line)
            if match:
                extra["special note"] = match.group(1)
            else: # could not match header line to any pattern
                api_route = f"/repos/{context['repository']}/commits/{context['commit']}/comments"
                body = {
                    "body": f"Unable to parse comment line number {num+1}.\n"
                            f"@{github_user}, make sure the line is formatted correctly."
                }
                syscall.github_rest_post(api_route, body);
                return {}

    syscall.write_key(bytes(key, "utf-8"), bytes(json.dumps(extra), "utf-8"))
    return { "remarks": key }
