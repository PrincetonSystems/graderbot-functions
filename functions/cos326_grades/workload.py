import csv
from datetime import datetime, timedelta, timezone
import io
import json

def allocations(length, sum):
    """Yield all tuples of `length` nonnegative integers that add up to `sum`.
    """
    if length == 1:
        yield (sum,)
    else:
        for value in range(sum + 1):
            for permutation in allocations(length - 1, sum - value):
                yield (value,) + permutation

def find_max(submissions, deadline):
    """Return the point maximum of `submissions` under a deadline of `deadline`
    while taking into account "fixes" made by graders.
    """
    i, mpoints = 0, 0

    while i < len(submissions) and submissions[i][0] < deadline and not submissions[i][2]:
        mpoints = max(mpoints, submissions[i][1])
        i += 1

    if i < len(submissions) and submissions[i][2]:
        while i < len(submissions):
            if submissions[i][2]:
                mpoints = max(mpoints, submissions[i][1])
            i += 1

    return mpoints

def handle(req, syscall):
    login = req["login"]
    req = req["payload"]

    enrollments = json.loads(syscall.read_key(bytes(f"{req['course']}/enrollments.json", "utf-8")))
    if not (login in enrollments and enrollments[login]["type"] == "Staff"):
        return { "error": "Only course staff can view grades" }
    assignments = json.loads(syscall.read_key(bytes(f"{req['course']}/assignments", "utf-8")))
    maxes = json.loads(syscall.read_key(bytes(f"{req['course']}/maxes", "utf-8")))

    student_grades = []

    for email in enrollments:
        # skip staff
        if enrollments[email]["type"] == "Staff":
            continue

        name = enrollments[email]["name"].split()
        github = syscall.read_key(bytes(f"users/github/for/user/{email}", "utf-8")).decode("utf-8").strip()
        student = { "lastname": name[-1], "firstname": name[0], "netid": email[:-14], "github": github }

        autograded = {}
        for asgn in assignments:
            autograded[asgn] = []
            repo = syscall.read_key(bytes(f"{req['course']}/assignments/{asgn}/{email}", "utf-8")).decode("utf-8")
            if repo == "":
                continue

            all_keys = list(syscall.read_dir(f"github/{repo}"))
            commits = [key for key in all_keys if key.endswith("/") and key != "refs/"]

            for commit in commits:
                grade = syscall.read_key(bytes(f"github/{repo}/{commit}grade.json", "utf-8"))
                if grade == b"":
                    continue
                grade = json.loads(grade)
                autograded[asgn].append((grade["push_date"], grade.get("given", 0), grade.get("fixed", False)))
            autograded[asgn].sort(key=lambda t: t[0])

            # other categories
            if "extra_grades" in all_keys:
                extra_grades = json.loads(syscall.read_key(bytes(f"github/{repo}/extra_grades", "utf-8")))
                fields = [key for key in extra_grades if len(key.split()) == 1]
                for field in fields:
                    student[f"{asgn}-{field}"] = extra_grades[field]["earned"]

        max_grade, max_grade_alloc = 0, {}
        for late_days_alloc in allocations(len(assignments), 4):
            grade, grade_alloc = 0, {}
            for i, asgn in enumerate(assignments):
                extended = (datetime.strptime(assignments[asgn]["soft_deadline"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) + timedelta(days=late_days_alloc[i])).timestamp()
                if "hard_deadline" in assignments[asgn]:
                    points = find_max(autograded[asgn], min(extended, datetime.strptime(assignments[asgn]["hard_deadline"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()))
                else:
                    points = find_max(autograded[asgn], extended)
                total_earned = sum([student.get(f"{asgn}-{category}", 0) for category in maxes[asgn] if category != "autograder"]) + points
                grade += assignments[asgn]["weight"] * total_earned / sum(maxes[asgn].values())
                grade_alloc[asgn] = points
            if grade > max_grade:
                max_grade, max_grade_alloc = grade, grade_alloc

        for asgn in assignments:
            student[f"{asgn}-autograder"] = max_grade_alloc.get(asgn)
        student_grades.append(student)

    fieldnames = ["lastname", "firstname", "netid", "github"]
    max_student = {"lastname": "MAX", "firstname": "POSSIBLE"}
    for asgn, categories in maxes.items():
        for cname, cmax in categories.items():
            fieldnames.append(f"{asgn}-{cname}")
            max_student[f"{asgn}-{cname}"] = cmax

    s = io.StringIO()
    writer = csv.DictWriter(s, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerow(max_student)
    writer.writerows(student_grades)
    return { "results": s.getvalue() }
