from __future__ import (  # pylint: disable=unused-variable
    absolute_import,
    division,
    print_function,
)

__metaclass__ = type  # pylint: disable=unused-variable

import json
import sys
import os
from os.path import dirname, abspath, join

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import Request

if os.environ.get("ENV") == "dev":
    module_utils_path = join(dirname(dirname(abspath(__file__))), "module_utils")
    sys.path.append(module_utils_path)
    import samson_utils  # pylint: disable=no-name-in-module, import-error
else:
    from ansible.module_utils import (  # pylint: disable=no-name-in-module, ungrouped-imports
        samson_utils,
    )

HTTPError = samson_utils.HTTPError
entity_url = samson_utils.entity_url
delete_entity = samson_utils.delete_entity
validate_permalink = samson_utils.validate_permalink


def strip_none_props(d):
    return {k: v for k, v in d.items() if v is not None}


def find_stage_by_name(http_client, base_url, name):
    res = http_client.get(entity_url(base_url))
    stages = json.load(res)["stages"]
    for stage in stages:
        if stage["name"] == name:
            return stage
    return None


def create(module, http_client, base_url, ansible_params):
    try:
        url = entity_url(base_url)
        stage = strip_none_props(ansible_params)
        res = http_client.post(url, data=json.dumps({"stage": stage}))

        # The Samson API doesn't actually use the permalink we provided on
        # creation. Instead it uses the name with whitespace replaced by dashes.
        # We need to perform a creation post-update to ensure the permalink is
        # the one the user provided.
        stage = find_stage_by_name(http_client, base_url, ansible_params["name"])
        url = entity_url(base_url, stage["permalink"])
        res = http_client.patch(
            url, data=json.dumps({"permalink": ansible_params["permalink"]})
        )

        stage = json.load(res)["stage"]
        module.exit_json(changed=True, stage=stage)
    except HTTPError as err:
        msg = err.msg
        if err.code == 422:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def update(module, http_client, base_url, stage, ansible_params):
    ansible_params = strip_none_props(ansible_params)

    try:
        url = entity_url(base_url, identifier=ansible_params["permalink"])
        res = http_client.patch(url, data=json.dumps(ansible_params))

        stage = json.load(res)["stage"]
        module.exit_json(changed=True, stage=stage)

    except HTTPError as err:
        msg = err.msg
        if err.code == 422:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def upsert(module, http_client, base_url, ansible_params):
    try:
        url = entity_url(base_url, ansible_params["permalink"])
        res = http_client.get(url)
        stage = json.load(res)["stage"]
        update(module, http_client, base_url, stage, ansible_params)
    except HTTPError as err:
        if err.code != 404:
            raise err

        create(module, http_client, base_url, ansible_params)


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        # Required params
        project_permalink=dict(required=True, type="str"),
        permalink=dict(required=True, type="str"),
        name=dict(type="str"),
        command_ids=dict(type="list"),
        deploy_group_ids=dict(type="list"),
        allow_redeploy_previous_when_failed=dict(type="bool"),
        aws_sts_iam_role_arn=dict(type="str"),
        block_on_gcr_vulnerabilities=dict(type="bool"),
        builds_in_environment=dict(type="bool"),
        cancel_queued_deploys=dict(type="bool"),
        comment_on_zendesk_tickets=dict(type="bool"),
        confirm=dict(type="bool"),
        dashboard=dict(type="str"),
        datadog_tags=dict(type="str"),
        default_reference=dict(type="str"),
        deploy_on_release=dict(type="bool"),
        email_committers_on_automated_deploy_failure=dict(type="bool"),
        full_checkout=dict(type="bool"),
        is_template=dict(type="bool"),
        jenkins_build_params=dict(type="bool"),
        jenkins_email_committers=dict(type="bool"),
        jenkins_job_names=dict(type="str"),
        kubernetes=dict(type="bool"),
        next_stage_ids=dict(type="list"),
        no_code_deployed=dict(type="bool"),
        no_reference_selection=dict(type="bool"),
        notify_airbrake=dict(type="bool"),
        notify_assertible=dict(type="bool"),
        notify_email_address=dict(type="str"),
        periodical_deploy=dict(type="bool"),
        prerequisite_stage_ids=dict(type="list"),
        production=dict(type="bool"),
        run_in_parallel=dict(type="bool"),
        static_emails_on_automated_deploy_failure=dict(type="str"),
        update_github_pull_requests=dict(type="bool"),
        use_github_deployment_api=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec, required_if=[["state", "present", ["name"]]]
    )

    validate_permalink(module)

    state = module.params["state"]
    stage = module.params.copy()
    del stage["url"]
    del stage["state"]
    del stage["token"]
    del stage["project_permalink"]

    base_url = "/".join(
        [module.params["url"], "projects", module.params["project_permalink"], "stages"]
    )

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
        delete_entity(module, http_client, base_url, stage)


if __name__ == "__main__":
    main()
