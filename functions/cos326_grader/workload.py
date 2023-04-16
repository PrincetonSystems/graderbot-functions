import json
import os
import resource
import signal
import tempfile
from subprocess import Popen, PIPE, STDOUT

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

def set_cpu_limits(limit):
    """Limit the amount of CPU time a process can consume to `limit` seconds.
    The same limits are applied to all descendants of that process.
    """
    resource.setrlimit(resource.RLIMIT_CPU, (limit, limit))

def build(report_key, syscall):
    """Compile the grading executable and time out if 30 seconds in CPU time is reached.
    If compiling fails, write a report to the database key `report_key`.
    Return the exit code from compiling.
    """
    os.system("bash SETUP")

    if os.path.exists("Makefile"):
        # note that preexec_fn makes Popen thread-unsafe
        run = Popen("make -s", shell=True, stdout=PIPE, stderr=STDOUT,
                preexec_fn=set_cpu_limits(30))
    elif os.path.exists("dune-project"):
        # note that preexec_fn makes Popen thread-unsafe
        run = Popen("dune build", shell=True, stdout=PIPE, stderr=STDOUT,
                preexec_fn=set_cpu_limits(30))

    out = run.communicate()[0]
    if run.returncode != 0:
        if run.returncode == -signal.SIGKILL:
            syscall.write_key(bytes(report_key, "utf-8"), b"> Timed out while compiling your code.")
        else:
            syscall.write_key(bytes(report_key, "utf-8"), b"\n".join([b"```", out, b"```"]))
    return run.returncode

def do_run(report_key, results_key, limit, syscall):
    """Run the grading executable and time out if `limit` seconds in CPU time is reached.
    Write the report generated by the grading executable to the database key `report_key`.
    Write the grading executable progress results to the database key `results_key`.
    """
    if os.path.exists("a.out"):
        # note that preexec_fn makes Popen thread-unsafe
        run = Popen("ocamlrun a.out", shell=True, preexec_fn=set_cpu_limits(limit))
    else:
        # note that preexec_fn makes Popen thread-unsafe
        run = Popen("_build/default/test/grade.exe", shell=True,
                preexec_fn=set_cpu_limits(limit))
    run.communicate()

    report = Popen("cat cos326_report*", shell=True, stdout=PIPE).communicate()[0]
    if run.returncode == -signal.SIGKILL:
        report += (b"\n\n> Your program was forcefully killed. The most likely"
                   b" reason for this is your code taking too long to run.")
    syscall.write_key(bytes(report_key, "utf-8"), report)

    results = Popen("cat cos326_results*", shell=True, stdout=PIPE).communicate()[0]
    syscall.write_key(bytes(results_key, "utf-8"), results)

def app_handle(args, context, syscall):
    org_name = context["repository"].split("/")[0]

    key = f"github/{context['repository']}/{context['commit']}"
    report_key = key + "/report"
    results_key = key + "/results"
    keys = { "report": report_key }
    user_email = syscall.read_key(bytes(f"users/github/from/{context['pusher']}", "utf-8")).decode("utf-8").strip()
    if not (user_email in context["metadata"]["users"] or user_email == "graderbot"):
        keys["fixed"] = True

    assignments = json.loads(syscall.read_key(bytes(f"{org_name}/assignments", "utf-8")))
    assignment = context["metadata"]["assignment"]
    grading_script_ref = assignments[assignment]["grading_script"]
    grading_script = syscall.read_key(bytes(grading_script_ref, "utf-8")).strip()

    with tempfile.TemporaryDirectory() as workdir:
        os.chdir(workdir)

        with syscall.open_unnamed(args["submission"]) as submission_tar_file:
            os.mkdir("submission")
            tarp = Popen("tar -C submission -xz --strip-components=1", shell=True, stdin=PIPE)
            bs = submission_tar_file.read()
            while len(bs) > 0:
                tarp.stdin.write(bs)
                bs = submission_tar_file.read()
            tarp.stdin.close()
            tarp.communicate()

        with syscall.open_unnamed(grading_script) as grading_script_tar_file:
            os.mkdir("grader")
            tarp = Popen("tar -C grader -xz", shell=True, stdin=PIPE)
            bs = grading_script_tar_file.read()
            while len(bs) > 0:
                tarp.stdin.write(bs)
                bs = grading_script_tar_file.read()
            tarp.stdin.close()
            tarp.communicate()

        os.putenv("PATH", f"/srv/usr/bin:{os.getenv('PATH')}")
        os.putenv("OCAMLLIB", "/srv/usr/lib/ocaml")
        os.chdir("grader")

        if build(report_key, syscall) != 0:
            return keys

        do_run(report_key, results_key, assignments[assignment]["runtime_limit"], syscall)
        keys["results"] = results_key
        return keys
