from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import re
import sys

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import Request

if sys.version_info.major == 3:
    # pylint: disable=E0611,E0401
    from urllib.error import URLError as HTTPError
else:
    from urllib2 import HTTPError

# Samson sanitizes permalinks. It transforms spaces and underscores to dashes.
# It's better to fail in this case as the permalink is the de-facto identifier.
VALID_PERMALINK_REGEX = "^[A-Za-z0-9-]+$"


def strip_disallowed_props(stage):
    new_project = dict()
    disallowed_props = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "order",
        "template_stage_id",
        "project_id",
        "average_deploy_time",
    )
    for key in stage:
        if key not in disallowed_props:
            new_project[key] = stage[key]
    return new_project


def stage_url(base_url, permalink=""):
    parts = [base_url]
    if permalink:
        parts.append(permalink)

    return "{}.json".format("/".join(parts))


def extract_html_error(html):
    lines = html.split("\n")
    err_line_idx = None
    for idx, line in enumerate(lines):
        if re.search("There was an error", line):
            err_line_idx = idx
    err_msg = lines[err_line_idx + 1]
    err_msg = re.sub("<.*?>", "", err_msg)
    err_msg = err_msg.strip()
    return err_msg


def create(module, http_client, base_url, ansible_params):
    try:
        url = stage_url(base_url)
        url = url.replace(".json", "")
        res = http_client.post(url, data=json.dumps(ansible_params))

        html = res.read()
        m = re.search("There was an error", html)
        if m:
            msg = extract_html_error(html)
            module.fail_json(msg=msg)

        # Samson uses the name as the permalink on create so we have to send
        # another request to rename the permalink to the one that was provided.
        # This allows users to change the project name in the web UI without
        # breaking Ansible since permalink becomes the de-facto identifier.
        url = stage_url(base_url, ansible_params["name"])
        res = http_client.patch(
            url,
            data=json.dumps({"permalink": ansible_params["permalink"]}),
            follow_redirects="yes",
        )

        url = stage_url(base_url, ansible_params["permalink"])
        res = http_client.get(url)
        stage = json.load(res)["stage"]
        module.exit_json(changed=True, stage=stage)
    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def update(module, http_client, base_url, stage, ansible_params):
    updated_stage = stage.copy()
    updated_stage.update(ansible_params)
    updated_stage = strip_disallowed_props(updated_stage)
    stage = strip_disallowed_props(stage)

    if stage == updated_stage:
        module.exit_json(changed=False, stage=stage)

    try:
        url = stage_url(base_url, ansible_params["permalink"])
        res = http_client.patch(
            url, data=json.dumps(updated_stage), follow_redirects="yes"
        )

        html = res.read()
        m = re.search("There was an error", html)

        if m:
            msg = extract_html_error(html)
            module.fail_json(msg=msg)

        url = stage_url(base_url, ansible_params["permalink"])
        res = http_client.get(url)
        stage = json.load(res)["stage"]
        module.exit_json(changed=True, stage=stage)

    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def upsert(module, http_client, base_url, ansible_params):
    try:
        url = stage_url(base_url, ansible_params["permalink"])
        res = http_client.get(url)
        stage = json.load(res)["stage"]
        update(module, http_client, base_url, stage, ansible_params)
    except HTTPError as err:
        if err.code != 404:
            raise err

        create(module, http_client, base_url, ansible_params)


def delete(module, http_client, base_url, stage):
    try:
        http_client.delete(
            stage_url(base_url, stage["permalink"]), follow_redirects="yes"
        )
        module.exit_json(changed=True)
    except HTTPError as err:
        if err.code == 404:
            module.exit_json(changed=False)

        raise err


def valid_permalink(permalink):
    return bool(re.search(VALID_PERMALINK_REGEX, permalink))


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        # Required params
        project_permalink=dict(required=True, type="str"),
        permalink=dict(required=True, type="str"),
        # Required for state=present
        name=dict(type="str"),
        # Optional params
        allow_redeploy_previous_when_failed=dict(type="bool", default=False),
        aws_sts_iam_role_arn=dict(type="str", default=""),
        #  aws_sts_iam_role_session_duration": null,
        block_on_gcr_vulnerabilities=dict(type="bool", default=False),
        builds_in_environment=dict(type="bool", default=False),
        cancel_queued_deploys=dict(type="bool", default=False),
        comment_on_zendesk_tickets=dict(type="bool", default=False),
        confirm=dict(type="bool", default=True),
        dashboard=dict(type="str", default=""),
        datadog_monitor_ids=dict(type="str", default=""),
        datadog_tags=dict(type="str", default=""),
        default_reference=dict(type="str", default=""),
        deploy_on_release=dict(type="bool", default=False),
        email_committers_on_automated_deploy_failure=dict(type="bool", default=False),
        full_checkout=dict(type="bool", default=False),
        is_template=dict(type="bool", default=False),
        jenkins_build_params=dict(type="bool", default=False),
        jenkins_email_committers=dict(type="bool", default=False),
        jenkins_job_names=dict(type="str", default=""),
        kubernetes=dict(type="bool", default=False),
        next_stage_ids=dict(type="list", default=[]),
        no_code_deployed=dict(type="bool", default=False),
        no_reference_selection=dict(type="bool", default=False),
        notify_airbrake=dict(type="bool", default=False),
        notify_assertible=dict(type="bool", default=False),
        notify_email_address=dict(type="str", default=""),
        periodical_deploy=dict(type="bool", default=False),
        prerequisite_stage_ids=dict(type="list", default=[]),
        production=dict(type="bool", default=False),
        run_in_parallel=dict(type="bool", default=False),
        static_emails_on_automated_deploy_failure=dict(type="str", default=""),
        #  template_stage_id": null,
        update_github_pull_requests=dict(type="bool", default=False),
        use_github_deployment_api=dict(type="bool", default=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec, required_if=[["state", "present", ["name"]]]
    )

    if not valid_permalink(module.params["permalink"]):
        msg = "Permalink should match `{}`".format(VALID_PERMALINK_REGEX)
        module.exit_json(msg=msg)

    state = module.params["state"]
    stage = module.params.copy()
    base_url = "/".join(
        [module.params["url"], "projects", module.params["project_permalink"], "stages"]
    )
    del stage["url"]
    del stage["state"]
    del stage["token"]
    del stage["project_permalink"]

    http_client = Request(
        headers={
            "Authorization": "Bearer {}".format(module.params["token"]),
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if state == "present":
        upsert(module, http_client, base_url, stage)
    elif state == "absent":
        delete(module, http_client, base_url, stage)


if __name__ == "__main__":
    main()
