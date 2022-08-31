#! /usr/bin/env python3
import requests
import urllib.parse
import re
import json
import os

# https://community.canvaslms.com/t5/Admin-Guide/How-do-I-manage-API-access-tokens-as-an-admin/ta-p/89
CANVAS_BASE = "https://princeton.instructure.com"

link_re = re.compile("<(.*)>; rel=\"next\"")

def canvas_request(endpoint, params=None, data=None, token=None, autopage=True):
    
    params = params or dict()
    params["per_page"] = "200"
    
    json_data = []

    next_link = urllib.parse.urljoin(CANVAS_BASE, endpoint)
    
    while next_link:
        response = requests.get(
            url=next_link,
            headers={
                "Authorization": "Bearer {}".format(token),
            },
            params=params,
            data=data,
        )

        # FIXME: here assuming json_data is list, should check
        json_data += response.json()
        
        #########
        # detect next link if paged
        next_link = next(
                (link.group(1) for link in map(lambda l: link_re.match(l), response.headers["Link"].split(",")) if link),
                None)
        #########
    
    return json_data

def get_students(course_id, token):
    
    #enrollments = course_enrollment(course_id=course_code, token=token)
    enrollments = canvas_request(
        endpoint="/api/v1/courses/{}/enrollments".format(course_id),
        #params={"include[]": "avatar_url"},
        token=token,
    )

    students = dict([
        (row["user"]["login_id"] + "@princeton.edu", {
            "email": row["user"]["login_id"] + "@princeton.edu",
            "puid": row["user"]["sis_user_id"],
            "name": row["user"]["name"],
            "last": row["user"]["sortable_name"].split(", ")[0],
            "first": row["user"]["sortable_name"].split(", ")[1],
            "type": "Staff" if row["type"] != "StudentEnrollment" else row["type"],
        })
        for row in enrollments if row["type"] != "StudentViewEnrollment"
    ])
    
    return students

def handle(request, syscalls):
    course = bytes(request["course"], "utf-8");
    token = syscalls.read_key(course + b'/canvas/token')
    course_id = syscalls.read_key(course + b'/canvas/course_id')
    if token and course_id:
        token = token.decode('utf-8')
        course_id = course_id.decode('utf-8')
        students = get_students(course_id,token=token)
        syscalls.write_key(course + b'/enrollments.json', bytes(json.dumps(students), "utf-8"))
        return { "enrollments": len(students) }
    else:
        return {}
