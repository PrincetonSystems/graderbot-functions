import csv
import io
import json
from datetime import datetime, timedelta, timezone

def find_latest(submissions):
    """Return the latest in `submissions` while taking into account "fixes" made
    by graders.
    """
    i = len(submissions) - 1
    while i >= 0 and submissions[i][2]:
        i -= 1
    return submissions[i] if i >= 0 else None

def handle(req, syscall):
    login = req["login"]
    req = req["payload"]

    enrollments = json.loads(syscall.read_key(bytes(f"{req['course']}/enrollments.json", "utf-8")))
    if not (login in enrollments and enrollments[login]["type"] == "Staff"):
        return { "error": "Only course staff can view grades" }
    assignments = json.loads(syscall.read_key(bytes(f"{req['course']}/assignments", "utf-8")))
    maxes = json.loads(syscall.read_key(bytes(f"{req['course']}/maxes", "utf-8")))
    deadlines = { asgn: datetime.strptime(assignment["deadline"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) for asgn, assignment in assignments.items() }

    all_student_grades = []
    all_student_late_days = []

    for email in enrollments:
        if enrollments[email]["type"] != "StudentEnrollment":
            continue

        name = enrollments[email]["name"].split()
        github = syscall.read_key(bytes(f"users/github/for/user/{email}", "utf-8")).decode("utf-8").strip()
        student_grades = { "lastname": name[-1], "firstname": name[0], "netid": email[:-14], "github": github }
        student_late_days = { "netid": email[:-14] }

        autograded = {}
        for asgn in assignments:
            autograded[asgn] = []
            student_grades[f"{asgn}-autograder"] = None
            student_late_days[asgn] = 0
            repo = syscall.read_key(bytes(f"{req['course']}/assignments/{asgn}/{email}", "utf-8")).decode("utf-8")
            if repo == "":
                continue

            all_keys = list(syscall.read_dir(f"github/{repo}"))
            commits = [key for key in all_keys if key.endswith("/") and key != "refs/"]

            # retrieve all autograded grades
            for commit in commits:
                grade = syscall.read_key(bytes(f"github/{repo}/{commit}grade.json", "utf-8"))
                if grade == b"":
                    continue
                grade = json.loads(grade)
                autograded[asgn].append((grade["push_date"], grade.get("given", 0), grade.get("fixed", False)))
            autograded[asgn].sort(key=lambda t: t[0])

            extended = (deadlines[asgn] + timedelta(days=1)).timestamp()
            latest = find_latest(autograded[asgn])
            student_grades[f"{asgn}-autograder"] = latest[1]
            if latest and latest[0] >= extended:
                student_late_days[asgn] = timedelta(seconds=latest[0]-extended) // timedelta(days=1) + 1

            # other categories
            if "extra" in all_keys:
                extra = json.loads(syscall.read_key(bytes(f"github/{repo}/extra", "utf-8")))
                fields = [key for key in extra if len(key.split()) == 1]
                for field in fields:
                    if field not in maxes[asgn]:
                        return {}
                    student_grades[f"{asgn}-{field}"] = extra[field]["earned"]
        all_student_grades.append(student_grades)
        all_student_late_days.append(student_late_days)

    # grades csv
    fieldnames = ["lastname", "firstname", "netid", "github"]
    max_student = {"lastname": "MAX", "firstname": "POSSIBLE"}
    for asgn, categories in maxes.items():
        for cname, cmax in categories.items():
            fieldnames.append(f"{asgn}-{cname}")
            max_student[f"{asgn}-{cname}"] = cmax

    grades_csv = io.StringIO()
    writer = csv.DictWriter(grades_csv, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow(max_student)
    writer.writerows(all_student_grades)

    # late days csv
    fieldnames = ["netid"] + list(assignments.keys())
    late_days_csv = io.StringIO()
    writer = csv.DictWriter(late_days_csv, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_student_late_days)

    return { "grades": grades_csv.getvalue(), "late days": late_days_csv.getvalue() }
