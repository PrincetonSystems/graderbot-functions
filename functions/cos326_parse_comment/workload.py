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

    match = enrollment.get(user_email)
    if not match or match["type"] != "Staff":
        return {}

    extra = {}
    pattern = re.compile(r"[ \t]*grade +(\w+ +)?(\d+)( */ *(\d+))?", re.IGNORECASE)
    for line in args["comment"].splitlines():
        reg = pattern.match(line)
        if reg:
            grade = { "earned": int(reg.group(2)) }
            if reg.group(4):
                grade["total"] = int(reg.group(4))

            if reg.group(1):
                extra[reg.group(1).strip().lower()] = grade
            else:
                extra = extra | grade
        else:
            break

    syscall.write_key(bytes(key, "utf-8"), bytes(json.dumps(extra), "utf-8"))
    return { "remarks": key }
