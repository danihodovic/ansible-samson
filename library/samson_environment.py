from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os
import sys
import re

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


DISALLOWED_PROPS = ["id", "created_at", "updated_at", "deleted_at"]


def find_environment(http_client, base_url, condition):
    url = entity_url(base_url)
    res = http_client.get(url)
    envs = json.load(res)["environments"]
    for env in envs:
        if condition(env):
            return env
    return None


def extract_html_error(res):
    html = res.read()
    lines = html.split("\n")
    err_line_idx = None
    for idx, line in enumerate(lines):
        if re.search("There was an error", line):
            err_line_idx = idx

    if not err_line_idx:
        return None

    err_msg = lines[err_line_idx + 1]
    err_msg = re.sub("<.*?>", "", err_msg)
    err_msg = err_msg.strip()
    return err_msg


def create(module, http_client, base_url, ansible_params):
    try:
        url = entity_url(base_url, json_suffix=False)
        res = http_client.post(url, data=json.dumps(ansible_params))
        err = extract_html_error(res)
        if err:
            module.fail_json(changed=False, msg=err)

        # The Samson API doesn't actually use the permalink we provided on
        # creation. Instead it uses the name with whitespace replaced by dashes.
        # We need to perform a creation post-update to ensure the permalink is
        # the one the user provided.
        by_name = lambda env: env["name"] == ansible_params["name"]
        env = find_environment(http_client, base_url, by_name)
        url = entity_url(base_url, env["permalink"], json_suffix=False)
        http_client.patch(
            url,
            data=json.dumps(dict(permalink=ansible_params["permalink"])),
            follow_redirects=True,
        )

        by_permalink = lambda env: env["permalink"] == ansible_params["permalink"]
        env = find_environment(http_client, base_url, by_permalink)
        module.exit_json(changed=True, environment=env)
    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def update(module, http_client, base_url, env, ansible_params):
    updated_env = strip_disallowed_props(env, DISALLOWED_PROPS)
    updated_env.update(ansible_params)
    env = strip_disallowed_props(env, DISALLOWED_PROPS)

    if updated_env == env:
        module.exit_json(changed=False, environment=env)

    try:
        url = entity_url(base_url, ansible_params["permalink"], json_suffix=False)
        res = http_client.patch(
            url, data=json.dumps(dict(environment=updated_env)), follow_redirects=True
        )
        err = extract_html_error(res)
        if err:
            module.fail_json(changed=False, msg=err)

        by_permalink = lambda env: env["permalink"] == ansible_params["permalink"]
        env = find_environment(http_client, base_url, by_permalink)
        module.exit_json(changed=True, environment=env)
    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def upsert(module, http_client, base_url, ansible_params):
    try:
        by_permalink = lambda env: env["permalink"] == ansible_params["permalink"]
        env = find_environment(http_client, base_url, by_permalink)

        if env:
            update(module, http_client, base_url, env, ansible_params)
        else:
            create(module, http_client, base_url, ansible_params)

    except HTTPError as err:
        module.fail_json(changed=False, msg=err.msg)


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        permalink=dict(required=True, type="str"),
        name=dict(type="str"),
        production=dict(type="bool", default=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec, required_if=[["state", "present", ["name"]]]
    )

    validate_permalink(module)

    base_url = "/".join([module.params["url"], "environments"])
    state = module.params["state"]
    params = dict((k, module.params[k]) for k in ("permalink", "name", "production"))

    http_client = Request(
        headers={
            "Authorization": "Bearer {}".format(module.params["token"]),
            "Content-Type": "application/json",
        }
    )

    if state == "present":
        upsert(module, http_client, base_url, params)

    if state == "absent":
        delete_entity(module, http_client, base_url, params, json_suffix=False)


if __name__ == "__main__":
    main()
