import json
import tempfile
import os
import time

def commit_comment(req, syscall):
    workflow_key = "%s/_comment_workflow" % (req["repository"]["full_name"].split("/")[0])
    workflow = json.loads(syscall.read_key(bytes(workflow_key, "utf-8")) or "[]")

    if len(workflow) > 0:
        next_function = workflow.pop(0)
        syscall.invoke(next_function, json.dumps({
            "args": {
                "comment": req["comment"]["body"]
            },
            "workflow": workflow,
            "context": {
                "repository": req["repository"]["full_name"],
                "commit": req["comment"]["commit_id"],
                "user": req["comment"]["user"]["login"]
            }
        }))
        return { "read": len(req["comment"]["body"]) }
    else:
        return {}

def push(req, syscall):
    key = "github/%s/%s.tgz" % (req["repository"]["full_name"], req["after"])
    branch_key = "github/%s/%s.tgz" % (req["repository"]["full_name"], req["ref"])
    meta_key = "github/%s/_meta" % (req["repository"]["full_name"])
    workflow_key = "github/%s/_workflow" % (req["repository"]["full_name"])

    workflow = json.loads(syscall.read_key(bytes(workflow_key, "utf-8")) or "[]")
    while isinstance(workflow, str):
        workflow = json.loads(syscall.read_key(bytes(workflow, "utf-8")) or "[]")
    metadataString = syscall.read_key(bytes(meta_key, "utf-8")) or "{}"
    if len(workflow):
        metadata = json.loads(metadataString)

        resp = syscall.github_rest_get("/repos/%s/tarball/%s" % (req["repository"]["full_name"], req["after"]), toblob=True);
        syscall.write_key(bytes(key, "utf-8"), resp.data)
        syscall.write_key(bytes(branch_key, "utf-8"), resp.data)

        if len(workflow) > 0:
            next_function = workflow.pop(0)
            syscall.invoke(next_function, json.dumps({
                "args": {
                    "submission": resp.data.decode('utf-8')
                },
                "workflow": workflow,
                "context": {
                    "repository": req["repository"]["full_name"],
                    "commit": req["after"],
                    "push_date": req["repository"]["pushed_at"],
                    "pusher": req["pusher"]["name"],
                    "metadata": metadata
                }
            }))
        return { "written": len(resp.data), "key": key }
    else:
        return {}

handlers = { "commit_comment": commit_comment, "push": push }

def handle(req, syscall):
    handler = handlers.get(req.get("event"))
    if handler:
        return handler(req, syscall)
    else:
        return {}

