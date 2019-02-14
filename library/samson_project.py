from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os
import sys

from os.path import dirname, abspath, join
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import Request


# Handle running in debug mode as we can't import from module_utils if we're
# running outside of Ansible, e.g:
# cat stage_args.json | ENV=dev python2 library/samson_stage.py
if os.environ.get("ENV") == "dev":
    module_utils_path = join(dirname(dirname(abspath(__file__))), "module_utils")
    sys.path.append(module_utils_path)
    # pylint: disable=no-name-in-module, import-error
    from samson_utils import (
        entity_url,
        strip_disallowed_props,
        delete_entity,
        validate_permalink,
    )
else:
    # pylint: disable=no-name-in-module, import-error
    from ansible.module_utils.samson_utils import (
        entity_url,
        strip_disallowed_props,
        delete_entity,
        validate_permalink,
    )


if sys.version_info.major == 3:
    # pylint: disable=no-name-in-module, import-error
    from urllib.error import URLError as HTTPError
else:
    from urllib2 import HTTPError


PROJECT_DISALLOWED_PROPS = [
    "id",
    "created_at",
    "updated_at",
    "build_command_id",
    "docker_image_building_disabled",
    "build_with_gcb",
    "kubernetes_allow_writing_to_root_filesystem",
]


def create(module, http_client, base_url, ansible_params):
    url = entity_url(base_url)
    res = http_client.post(url, data=json.dumps(ansible_params))
    project = json.load(res)["project"]

    try:
        # Samson doesn't use the permalink we give to it, so we have to update
        # the project post-creation to ensure the permalink is the one the user
        # provided
        url = entity_url(base_url, project["permalink"])
        data = {"permalink": ansible_params["permalink"]}
        res = http_client.patch(url, data=json.dumps(data))
        project = json.load(res)["project"]
        module.exit_json(changed=True, project=project)
    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def update(module, http_client, base_url, project, ansible_params):
    updated_project = project.copy()
    updated_project.update(ansible_params)
    updated_project = strip_disallowed_props(updated_project, PROJECT_DISALLOWED_PROPS)
    project_copy = strip_disallowed_props(project, PROJECT_DISALLOWED_PROPS)

    if project_copy == updated_project:
        module.exit_json(changed=False, project=project)

    try:
        url = entity_url(base_url, project["permalink"])
        res = http_client.patch(url, data=json.dumps(updated_project))
        project = json.load(res)["project"]
        module.exit_json(changed=True, project=project)
    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def upsert(module, http_client, base_url, ansible_params):
    try:
        url = entity_url(base_url, ansible_params["permalink"])
        res = http_client.get(url)
        project = json.load(res)["project"]
        update(module, http_client, base_url, project, ansible_params)
    # pylint: disable=W0703
    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)

        if err.code != 404:
            module.fail_json(changed=False, msg=msg)

        create(module, http_client, base_url, ansible_params)


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        permalink=dict(required=True, type="str"),
        name=dict(type="str"),
        repository_url=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[["state", "present", ["name", "repository_url"]]],
    )

    validate_permalink(module)

    base_url = "/".join([module.params["url"], "projects"])
    state = module.params["state"]
    project_params = dict(
        (k, module.params[k]) for k in ("permalink", "repository_url", "name")
    )

    http_client = Request(
        headers={
            "Authorization": "Bearer {}".format(module.params["token"]),
            "Content-Type": "application/json",
        }
    )

    if state == "present":
        upsert(module, http_client, base_url, project_params)

    if state == "absent":
        delete_entity(module, http_client, base_url, project_params)


if __name__ == "__main__":
    main()
