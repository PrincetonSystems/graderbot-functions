import csv
import io
import json

def handle(req, syscall):
    login = req["login"]
    req = req["payload"]

    enrollments = json.loads(syscall.read_key(bytes(f"{req['course']}/enrollments.json", "utf-8")))
    if login not in enrollments or enrollments.get(login)["type"] != "Staff":
        return { "error": "Only course staff can view grades" }
    assignments = json.loads(syscall.read_key(bytes(f"{req['course']}/assignments", "utf-8")))
    maxes = json.loads(syscall.read_key(bytes(f"{req['course']}/maxes", "utf-8")))

    student_grades = []

    for email in enrollments:
        # skip staff
        if enrollments.get(email)["type"] == "Staff":
            continue

        name = enrollments.get(email)["name"].split()
        github = syscall.read_key(bytes(f"users/github/for/user/{email}", "utf-8")).decode("utf-8").strip()
        student = {"lastname": name[-1], "firstname": name[0], "netid": email[:-14], "github": github}

        for asgn in assignments:
            repo = syscall.read_key(bytes(f"{req['course']}/assignments/{asgn}/{email}", "utf-8")).decode("utf-8")
            if repo == "":
                continue

            all_keys = list(syscall.read_dir(f"github/{repo}"))
            commits = [key for key in all_keys if key.endswith("/") and key != "refs/"]

            # find latest commit of repo
            pairs = []
            for commit in commits:
                grade = syscall.read_key(bytes(f"github/{repo}/{commit}grade.json", "utf-8"))
                if grade == b"":
                    continue
                grade = json.loads(grade)
                pairs.append((grade["push_date"], grade["given"] if "given" in grade else 0))
            pairs.sort(key=lambda t: t[0], reverse=True)

            if len(pairs) > 1:
                student[f"{asgn}-autograder"] = pairs[0][1]

            # other categories
            if "extra_grades" in all_keys:
                extra_grades = json.loads(syscall.read_key(bytes(f"github/{repo}/extra_grades", "utf-8")))
                fields = [key for key in extra_grades.keys() if len(key.split()) == 1]
                for field in fields:
                    student[f"{asgn}-{field}"] = extra_grades[field]["earned"]

        student_grades.append(student)

    fieldnames = ["lastname", "firstname", "netid", "github"]
    max_student = {"lastname": "MAX", "firstname": "POSSIBLE", "netid": "", "github": ""}
    for asgn in maxes:
        for category in maxes[asgn]:
            fieldnames.append(f"{asgn}-{category}")
            max_student[f"{asgn}-{category}"] = maxes[asgn][category]
    s = io.StringIO()
    writer = csv.DictWriter(s, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow(max_student)
    writer.writerows(student_grades)
    return { "results": s.getvalue() }
