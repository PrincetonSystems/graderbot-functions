import json
import tempfile
import os
from subprocess import Popen, PIPE, STDOUT, DEVNULL

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
    org_name = context["repository"].split("/")[0]

    key = f"github/{context['repository']}/{context['commit']}"
    report_key = key + "/report"
    results_key = key + "/results"

    assignments = json.loads(syscall.read_key(bytes(f"{org_name}/assignments", "utf-8")))
    assignment = context["metadata"]["assignment"]
    grading_script_ref = assignments[assignment]["grading_script"]
    grading_script = syscall.read_key(bytes(grading_script_ref, "utf-8")).strip()

    with tempfile.TemporaryDirectory() as submission_dir:
        with tempfile.TemporaryDirectory() as script_dir:
            # Fetch and untar submission tarball
            with syscall.open_unnamed(args["submission"]) as submission_tar_file:
                tarp = Popen(f"tar -C {submission_dir} -xz --strip-components=1", shell=True, stdin=PIPE)
                bs = submission_tar_file.read()
                while len(bs) > 0:
                    tarp.stdin.write(bs)
                    bs = submission_tar_file.read()
                tarp.stdin.close()
                tarp.communicate()

            # Fetch and untar grading script tarball
            with syscall.open_unnamed(grading_script) as grading_script_tar_file:
                tarp = Popen(f"tar -C {script_dir} -xz", shell=True, stdin=PIPE)
                bs = grading_script_tar_file.read()
                while len(bs) > 0:
                    tarp.stdin.write(bs)
                    bs = grading_script_tar_file.read()
                tarp.stdin.close()
                tarp.communicate()

            # OK, run tests
            os.putenv("GOCACHE", "%s/.cache" % script_dir)
            os.putenv("GOROOT", "/srv/usr/lib/go") 
            os.putenv("SOLUTION_DIR", submission_dir)
            os.putenv("PATH", "%s:%s" % ("/srv/usr/lib/go/bin", os.getenv("PATH")))
            os.chdir(script_dir)
            if os.path.exists("pretest") and os.access("pretest", os.X_OK):
                os.system("./pretest")
            compiledtest = Popen("go test -c -o /tmp/grader", shell=True,
                    stdout=PIPE, stderr=PIPE)
            compileout, compileerr = compiledtest.communicate()
            if compiledtest.returncode != 0:
                return { "error": { "compile": str(compileerr), "returncode": compiledtest.returncode } }
            testrun = Popen("/tmp/grader -test.v | /srv/usr/lib/go/pkg/tool/linux_amd64/test2json", shell=True,
                    stdout=PIPE, stderr=DEVNULL)
            final_results = []
            for test_result in testrun.stdout:
                tr = json.loads(test_result)
                if tr["Action"] in ["pass", "fail", "run"]:
                    tr = dict((name.lower(), val) for name, val in tr.items())
                    final_results.append(json.dumps(tr))
            key = f"github/{context['repository']}/{context['commit']}/test_results.jsonl"
            syscall.write_key(bytes(key, "utf-8"), bytes('\n'.join(final_results), "utf-8"))
            testrun.wait()
            if testrun.returncode >= 0:
                return { "test_results": key }
            else:
                _, errlog = testrun.communicate()
                return { "error": { "testrun": str(errlog), "returncode": testrun.returncode } }
    return {}
