import json
import os
import resource
import shutil
import signal
from subprocess import Popen, PIPE, STDOUT
import tempfile

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

def set_cpu_limits(lim):
    """Used to limit the amount of CPU time a process can consume to `lim` seconds.
    The same limits are applied to all descendants of that process.
    """
    resource.setrlimit(resource.RLIMIT_CPU, (lim, lim))

def build(report_key, syscall):
    """Compiles grading executable and times out if 30 seconds in CPU time is reached.
    If compiling fails, writes a report to the database key `report_key`.
    Returns the exit code from compiling.
    """
    # note that preexec_fn makes Popen thread-unsafe
    run = Popen("make -se", shell=True, stdout=PIPE, stderr=STDOUT,
            preexec_fn=set_cpu_limits(30))
    out = run.communicate()[0]

    if run.returncode != 0:
        if run.returncode == -signal.SIGKILL:
            syscall.write_key(bytes(report_key, "utf-8"), b"> Timed out while compiling your code.")
        else:
            syscall.write_key(bytes(report_key, "utf-8"), b"\n".join([b"```", out, b"```"]))
    return run.returncode

def do_run(report_key, results_key, limit, syscall):
    """Runs grading executable and times out if `limit` seconds in CPU time is reached.
    Writes grading executable output to the database key `report_key`.
    Writes grading executable intermediate progress output to the database key
    `results_key`.
    """
    # note that preexec_fn makes Popen thread-unsafe
    run = Popen("ocamlrun a.out", shell=True, preexec_fn=set_cpu_limits(limit))
    run.communicate()

    report = Popen("cat /tmp/report*", shell=True, stdout=PIPE).communicate()[0]
    if run.returncode == -signal.SIGKILL:
        report = b"\n".join([report, b"\n> Your program was forcefully killed."
                                     b" The most likely reason for this is your"
                                     b" code taking too long to run."])
    syscall.write_key(bytes(report_key, "utf-8"), report)

    results = Popen("cat /tmp/results*", shell=True, stdout=PIPE).communicate()[0]
    syscall.write_key(bytes(results_key, "utf-8"), results)

    # clean up temporary files
    os.system("rm -f /tmp/report* /tmp/results*")

def app_handle(args, context, syscall):
    org_name = context["repository"].split("/")[0]

    key = f"github/{context['repository']}/{context['commit']}"
    report_key = key + "/report"
    results_key = key + "/results"

    assignment = context["metadata"]["assignment"]
    assignments = json.loads(syscall.read_key(bytes(f"{org_name}/assignments", "utf-8")))
    grading_script_ref = assignments[assignment]["grading_script"]
    grading_script = syscall.read_key(bytes(grading_script_ref, "utf-8")).strip()

    limits = json.loads(syscall.read_key(bytes(f"{org_name}/limits", "utf-8")))

    with tempfile.TemporaryDirectory() as workdir:
        os.mkdir("shared")
        os.system(f"cp /srv/utils326.ml /srv/precheck {workdir}")

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
        os.putenv("SHARED", "shared")
        os.putenv("GRADER", "grader")
        os.chdir("submission")

        run = Popen("./shared/precheck", stdout=PIPE)
        out = run.communicate()[0]
        if run.returncode != 0:
            syscall.write_key(bytes(report_key, "utf-8"), out)
            return { "report": report_key }

        os.system("cp -r grader/* .")
        if build(report_key, syscall) != 0:
            return { "report": report_key }

        # prevent students from accessing source code files
        shutil.copy("a.out", workdir)
        os.chdir(workdir)
        os.system("rm -rf shared grader submission")

        do_run(report_key, results_key, limits[assignment], syscall)
        return { "report": report_key, "results": results_key }
