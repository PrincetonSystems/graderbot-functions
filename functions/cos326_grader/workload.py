import json
import tempfile
import os
import subprocess
import shutil

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
    assignment = state["metadata"]["assignment"]
    report_key = f"github/{state['repository']}/{state['commit']}/report"
    # Assignment definitions are under {github org}/assignments as a JSON string
    # that includes a "grading_script" key for each assignment
    assignments_def = json.loads(syscall.read_key(bytes(f'{state["repository"].split("/")[0]}/assignments', 'utf-8')).decode('utf8'))
    assignment_grading_script_ref = assignments_def[assignment]["grading_script"]
    grading_script = syscall.read_key(bytes(assignment_grading_script_ref, 'utf-8'))

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
        checkrun = subprocess.Popen("./precheck", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        checkout, _ = checkrun.communicate()
        if checkrun.returncode != 0:
            syscall.write_key(bytes(report_key, "utf-8"), checkout)
            return { "report": report_key }

        # compile grading executable
        os.system("cp grader/* submission")
        compilerun = subprocess.Popen("make -sef submission/Makefile", shell=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        compileout, _ = compilerun.communicate()
        if compilerun.returncode != 0:
            syscall.write_key(bytes(report_key, "utf-8"), b"\n".join([b"```", compileout, b"```"]))
            return { "report": report_key }

        # run tests
        testrun = subprocess.Popen("ocamlrun a.out", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        testout, _ = testrun.communicate()
        syscall.write_key(bytes(report_key, "utf-8"), testout)
        return { "report": report_key }
