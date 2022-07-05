import json
import tempfile
import os
import time

def handle(req, syscall):
    owner, repo = req["repository"]["full_name"].split('/')
    full_repo_name = '-'.join([owner, repo])
    l_repo = syscall.new_dclabel([[full_repo_name]], [[owner]])
    metadata = json.loads(syscall.fs_read([l_repo, '_meta']) or "{}")
    workflow = json.loads(syscall.fs_read([l_repo, '_workflow']) or "[]")

    l_w = syscall.getCurrentLabel()
    l_w.integrity = [['gh_repo']]

    resp = syscall.github_rest_get("/repos/%s/tarball/%s" % (req_full_name, req["after"]))

    tarball_path = [l_w, req['after']+'.tgz']
    success = syscall.fs_createfile(tarball_path)
    success &= syscall.fs_write(tarball_path, resp.data)
    if not success:
        return { "error": "failed to download tarball" }

    if len(workflow) > 0:
        next_function = workflow.pop(0)
        payload = json.dumps({
            "args": {
                "submission": tarball_path
            },
            "workflow": workflow,
            "context": {
                "repository": req["repository"]["full_name"],
                "commit": req["after"],
                "push_date": req["repository"]["pushed_at"],
                "metadata": metadata
            }
        })
        data_handles = {}
        syscall.invoke(next_function, payload, data_handles)
    return { "written": len(resp.data), "path": tarball_path }
