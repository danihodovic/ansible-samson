from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import sys
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import Request

# pylint: disable=E0611,E0401
from ansible.module_utils.samson_utils import entity_url

if sys.version_info.major == 3:
    # pylint: disable=E0611,E0401
    from urllib.error import URLError as HTTPError
else:
    from urllib2 import HTTPError


def create(module, http_client, base_url, params):
    ids = find_commands(http_client, base_url, params)
    if ids:
        module.exit_json(changed=False, command=params)

    url = entity_url(base_url)
    try:
        res = http_client.post(url, data=json.dumps(dict(command=params)))
        command = json.load(res)["command"]
        module.exit_json(changed=True, command=command)
    except HTTPError as err:
        msg = err.msg
        if err.code == 400:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def delete(module, http_client, base_url, params):
    ids = find_commands(http_client, base_url, params)
    if not ids:
        module.exit_json(changed=False)

    try:
        for command_id in ids:
            url = entity_url(base_url, identifier=str(command_id))
            http_client.delete(url)

        module.exit_json(changed=True)
    except HTTPError as err:
        raise err


def find_commands(http_client, base_url, params):
    url = entity_url(base_url)
    res = http_client.get(url)
    body = json.load(res)

    ids = []
    for command in body["commands"]:
        if (
            params["command"] == command["command"]
            and params["project_id"] == command["project_id"]
        ):
            ids.append(command["id"])

    return ids


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        command=dict(required=True, type="str"),
        project_id=dict(type="int"),
    )

    module = AnsibleModule(argument_spec=argument_spec)

    base_url = "/".join([module.params["url"], "commands"])
    state = module.params["state"]
    token = module.params["token"]
    params = module.params.copy()
    del params["url"]
    del params["state"]
    del params["token"]

    http_client = Request(
        headers={
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }
    )

    if state == "present":
        create(module, http_client, base_url, params)
    elif state == "absent":
        delete(module, http_client, base_url, params)


if __name__ == "__main__":
    main()
