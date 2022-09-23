import copy
from datetime import datetime, timezone
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

def parse_results(results):
    """Parses `results` to calculate grades.
    Returns two dictionaries, the first of which contains
        "passed": number of problems passed
        "points": number of points given
        "probs": total number of problems
        "total_points": total number of points that are autograded
        "pending": total number of pending points
    and the second has the same field names as the first, but which correspond
    to the optional variant.
    """
    stats = {
        "passed": 0,
        "points": 0,
        "probs": 0,
        "total_points": 0,
        "pending": 0
    }
    opt_stats = copy.copy(stats)

    # mapping from `results` keywords to dictionary keys
    mapping = {
        "problems": "probs",
        "points": "total_points",
        "pending": "pending"
    }

    p1 = re.compile(r"Problem (passed|FAILED) \((\d+) */ *\d+ points\)")
    p2 = re.compile(r"Max (optional )?(problems|points|pending): (\d+)")
    p3 = re.compile(r"Optional problem (passed|FAILED) \((\d+) */ *\d+ points\)")
    for line in results.splitlines():
        match = p1.match(line)
        if match:
            if match.group(1) == "passed":
                stats["passed"] += 1
            stats["points"] += int(match.group(2))
            continue

        match = p2.match(line)
        if match:
            if match.group(1):
                opt_stats[mapping[match.group(2)]] = int(match.group(3))
            else:
                stats[mapping[match.group(2)]] = int(match.group(3))
            continue

        match = p3.match(line)
        if match:
            if match.group(1) == "passed":
                opt_stats["passed"] += 1
            opt_stats["points"] += int(match.group(2))

    return stats, opt_stats

def app_handle(args, context, syscall):
    key = f"github/{context['repository']}/{context['commit']}"
    report_key = key + "/final_report"

    final_report = []
    timestamp = datetime.utcfromtimestamp(context["push_date"]).replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%D %T %z")
    final_report.append(bytes(f"Submitted {timestamp}\n", "utf-8"))

    if "results" in args:
        stats, opt_stats = parse_results(syscall.read_key(bytes(args["results"], "utf-8")).decode("utf-8"))
    else:
        stats, opt_stats = parse_results("")

    summary = []
    if stats["total_points"] != 0:
        summary.append(f"## Grade: {100*stats['points']/stats['total_points']:.2f}%\n")
        summary.append(f"- Problems passed: {stats['passed']} / {stats['probs']}")
        summary.append("- Points awarded:")
        summary.append(f"    - Given: {stats['points']} / {stats['total_points']}")
        if stats["pending"] != 0:
            summary.append(f"    - Pending: _ / {stats['pending']}")
        if opt_stats["probs"] != 0:
            summary.append(f"- Optional problems passed: {opt_stats['passed']} / {opt_stats['probs']}")
            if opt_stats["total_points"] != 0:
                summary.append(f"    - Given: {opt_stats['points']} / {opt_stats['total_points']}")
            if opt_stats["pending"] != 0:
                summary.append(f"    - Pending: _ / {opt_stats['pending']}")
        summary[-1] += "\n"

        syscall.write_key(bytes(key + "/grade.json", "utf-8"), bytes(json.dumps({
            "grade": stats["points"] / stats["total_points"],
            "given": stats["points"],
            "total": stats["total_points"],
            "push_date": context["push_date"]
        }), "utf-8"))
    else:
        # grading code never got to run in this case
        summary.append("## Grade: 0.00%\n")
        syscall.write_key(bytes(key + "/grade.json", "utf-8"), bytes(json.dumps({
            "grade": 0,
            "push_date": context["push_date"]
        }), "utf-8"))

    final_report.extend([bytes(line, "utf-8") for line in summary])
    initial_report = syscall.read_key(bytes(args["report"], "utf-8"))
    if initial_report != b"":
        final_report.append(initial_report)
    else:
        final_report.append(b"Your code raised an exception before the grading"
                            b" code could run, so this is all we could do.")

    syscall.write_key(bytes(report_key, "utf-8"), b"\n".join(final_report))
    return { "report": report_key }
