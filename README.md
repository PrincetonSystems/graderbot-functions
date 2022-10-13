# Faasten Grading Functions for COS316 and COS326

## Directory structure

For each "function" `FUNC_NAME` there are three important artifacts:

1. `functions/FUNC_NAME/` is a subdirectory containing the function code, mounted as `/srv/` when
   the function is running.
2. `payloads/FUNC_NAME.jsonl` is a JSON-line formatted file where each line is
   a JSON encoded request payload to the function, useful for testing.
3. `output/FUNC_NAME.img` a "compiled" filesystem image from the function
   source automatically generated.

The `examples/` subdirectory contains sample graders and submissions for use in testing.

The `storage/` subdirectory is used to store LMDB data from test runs.

The `Makefile` contains rules for easily building filesystem images and for testing.

## Function workload descriptions

Most `functions/FUNC_NAME/workload.py` files contain the function declaration

```python
def app_handle(args, context, syscall):
```

where
- `args`: dictionary passed by the previous function in a workflow
- `context`: dictionary holding data that could be relevant to the workflow, set by `gh_repo`
- `syscall`: Syscall object

and which returns a dictionary.

A brief description of most functions and the keys used in their `args` and
returned dictionary is given below. Keys for the `args` parameter might be
indicated as optional, meaning the function will work properly without them.
Keys for the returned dictionary might have an \*, indicating that they may not
be present.

- `cos326_grader`: Grader for COS326 that runs a grading script on a submission.
    - `args`:
        - `submission`: a reference to a gzipped tarball of the submission
    - Returns:
        - `report`: the database key under which the output of the grading
            script is stored
        - `results`*: the database key under which grading script intermediate
            progress results are stored
        - `fixed`*: if this key is used, indicates that the commit was made by
            someone other than the student(s) working on the assignment (e.g. a
            grader making changes to make the code compile)
- `cos326_parse_comment`: Stores relevant data from commit comments.
    - `args`:
        - `comment`: byte array containing raw comment
    - Returns:
        - `remarks`*: the database key under which data from the comment is stored
- `cos326_parse_results`: To be used with `cos326_grader`, creates a report to
    be shown to students by parsing `results` and appending `report` to it.
    - `args`:
        - `report`: the database key under which an initial report is stored
        - `results` (optional): the database key under which intermediate
            progress results are stored
        - `fixed` (optional): indicates that the commit was made by someone
            other than the student(s) working on the assignment and should be
            appropriately recorded in the database
    - Returns:
        - `report`: the database key under which the finalized report is stored
- `generate_report`:
    - `args`:
        - `grade_report`:
    - Returns:
        - `report`:
- `go_grader`:
    - `args`:
        - `submission`:
    - Returns:
        - `test_results`*:
        - `error`*:
- `grades`:
    - `args`:
        - `test_results`:
    - Returns:
        - `grade`:
        - `grade_report`:
- `post_comment`: Posts a commit comment to a repository.
    - `args`:
        - `report`: the database key under which data to be added as a comment is stored
    - Returns: A JSON-serialized HTTP response from GitHub.

## Test functions

To run a function using the requests in its respective payload file, use the
Makefile in the root directory:

```
$ make run/FUNC_NAME
```

This will build the function image and run it using `fc_wrapper`, passing in
each of the requests from the payload one after the other. It stores the output
of in `run/FUNC_NAME`.

## Objects

- `cos316/assignments` - JSON object mapping assignment names to starter code repo and other metadata.
  Ex:
  ```json
  { "assignment0": { "starter_code": "cos316/assignment0-starter-code" } }
  ```

- `github/[owner]/[repo]/_meta` - JSON object with assignment and list of student NetIDs
  Ex: `github/cos316/assignment0-foobar/_meta`
  ```json
  { "assignment": "assignment0", "users": [ "aalevy", "kap" ] }
  ```

- `github/[owner]/[repo]/_workflow` - JSON array with workflow functions
  Ex: `github/cos316/assignment0-foobar/_workflow`
  ```json
  [ "go_grader", "grades", "generate_report", "post_comment" ]
  ```

- `cos316/[assignment]/grading_script` - tarball of the grading script

- `cos316/[assignment]/grader_config` - JSON configuration from grading script
