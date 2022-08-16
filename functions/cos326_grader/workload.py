import json
import os
import resource
import shutil
import signal
import subprocess
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
    """Used to limit the amount of CPU time a process can consume to lim seconds.
    The same limits are applied to processes it creates.
    """
    resource.setrlimit(resource.RLIMIT_CPU, (lim, lim))

def build(report_key, syscall):
    """ Compiles grading executable.
    If code compiles succuessfully, returns 0 and nothing is written to the database.
    Otherwise returns the error code from compiling and writes an appropriate
    report to the database key `report_key`.
    """
    # note that preexec_fn makes Popen thread-unsafe
    compilerun = subprocess.Popen("make -sef submission/Makefile", shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    preexec_fn=set_cpu_limits(60))
    compileout = compilerun.communicate()[0]
    if compilerun.returncode != 0:
        if compilerun.returncode == -signal.SIGKILL:
            syscall.write_key(bytes(report_key, "utf-8"), b"> Compile time limit reached.")
        else:
            syscall.write_key(bytes(report_key, "utf-8"), b"\n".join([b"```", compileout, b"```"]))
        return -1
    return 0

def run(report_key, limit, syscall):
    """ Runs grading executable.
    If code compiles succuessfully, returns 0 and nothing is written to the database.
    Otherwise returns the error code from compiling and writes an appropriate
    report to the database key `report_key`.
    """
    # note that preexec_fn makes Popen thread-unsafe
    testrun = subprocess.Popen("ocamlrun a.out", shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, preexec_fn=set_cpu_limits(limit))
    testout = testrun.communicate()[0]
    if testrun.returncode == -signal.SIGKILL:
        syscall.write_key(bytes(report_key, "utf-8"), b"> Run time limit reached.")
    else:
        syscall.write_key(bytes(report_key, "utf-8"), testout)

def app_handle(args, state, syscall):
    """Compiles and runs an assignment-specific grading script for an assignment submission

    Parameters
    ----------
    args : dict
        A dictionary containing a reference to a gzipped tarball of the submission
        under the "submission" key
    state : dict
        A dictionary containing the assignment name (e.g. "a1", "a2", etc) under
        state["metadata"]["assignment"]. This is most likely set in the `_meta`
        repository prefix. This *must* correspond to a key in the 'cos326-f22/assignments'
        key containing a grading_script pointing to the grading script gzipped tarball.
    syscall : Syscall object
    """
    course_name = f'{state["repository"].split("/")[0]}'
    assignment = state["metadata"]["assignment"]
    report_key = f"github/{state['repository']}/{state['commit']}/report"
    # Assignment definitions are under {github org}/assignments as a JSON string
    # that includes a "grading_script" key for each assignment
    assignments_def = json.loads(syscall.read_key(bytes(f'{state["repository"].split("/")[0]}/assignments', 'utf-8')).decode('utf8'))
    assignment_grading_script_ref = assignments_def[assignment]["grading_script"]
    grading_script = syscall.read_key(bytes(assignment_grading_script_ref, 'utf-8')).strip()

    with tempfile.TemporaryDirectory() as workdir:
        shutil.copy("/srv/utils326.ml", workdir)
        shutil.copy("/srv/precheck", workdir)
        os.chdir(workdir)

        with syscall.open_unnamed(args["submission"]) as submission_tar_file:
            os.mkdir("submission")
            tarp = subprocess.Popen("tar -C submission -xz --strip-components=1", shell=True, stdin=subprocess.PIPE)
            bs = submission_tar_file.read()
            while len(bs) > 0:
                tarp.stdin.write(bs)
                bs = submission_tar_file.read()
            tarp.stdin.close()
            tarp.communicate()
            os.system("ls submission")

        with syscall.open_unnamed(grading_script) as grading_script_tar_file:
            os.mkdir("grader")
            tarp = subprocess.Popen("tar -C grader -xz", shell=True, stdin=subprocess.PIPE)
            bs = grading_script_tar_file.read()
            while len(bs) > 0:
                tarp.stdin.write(bs)
                bs = grading_script_tar_file.read()
            tarp.stdin.close()
            tarp.communicate()
            os.system("ls grader")

        # set up environment variables
        os.putenv("OCAMLLIB", "/srv/usr/lib/ocaml")
        os.putenv("PATH", f"/srv/usr/bin:{os.getenv('PATH')}")
        os.putenv("GRADER", "grader")
        os.putenv("SUBMISSION_DIR", "submission")

        # ensure preliminary checks pass
        checkrun = subprocess.Popen("./precheck", shell=True, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
        checkout = checkrun.communicate()[0]
        if checkrun.returncode != 0:
            syscall.write_key(bytes(report_key, "utf-8"), checkout)
            return { "report": report_key }

        os.system("cp grader/* submission")
        if build(report_key, syscall) != 0:
            return { "report": report_key }

        # prevent students from accessing source code files
        os.system("rm -rf utils326* precheck grader submission")

        limits = json.loads(syscall.read_key(bytes(f"{course_name}/limits", "utf-8")).decode("utf-8"))
        limit = limits[assignment]
        run(report_key, limit, syscall)
        return { "report": report_key }
