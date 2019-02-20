from __future__ import (  # pylint: disable=unused-variable
    absolute_import,
    division,
    print_function,
)

__metaclass__ = type  # pylint: disable=unused-variable

import json
import os
from os.path import dirname, abspath, join
import sys

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
find_item = samson_utils.find_item
find_project_by_id = samson_utils.find_project_by_id


def find_outbound_webhook(http_client, base_url, params):
    condition = lambda webhook: (
        webhook["stage_id"] == params["stage_id"] and webhook["url"] == params["url"]
    )
    return find_item(http_client, base_url, "webhooks", condition)


def create(module, http_client, base_url, params):
    webhook = find_outbound_webhook(http_client, base_url, params)
    if webhook:
        module.exit_json(changed=False, outbound_webhook=webhook)

    url = entity_url(base_url)
    try:
        res = http_client.post(url, data=json.dumps(params))
        webhook = json.load(res)["outbound_webhook"]
        webhook["webhook_url"] = webhook["url"]
        del webhook["url"]
        module.exit_json(changed=True, outbound_webhook=webhook)
    except HTTPError as err:
        msg = err.msg
        if err.code == 422:
            msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def delete(module, http_client, base_url, params):
    webhook = find_outbound_webhook(http_client, base_url, params)
    if not webhook:
        module.exit_json(changed=False)

    try:
        url = entity_url(base_url, identifier=str(webhook["id"]))
        http_client.delete(url)

        module.exit_json(changed=True)
    except HTTPError as err:
        if err.code == 404:
            module.exit_json(changed=False)

        raise err


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        project_id=dict(required=True, type="int"),
        stage_id=dict(required=True, type="int"),
        webhook_url=dict(type="str", default=""),
        username=dict(type="str"),
        password=dict(type="str", no_log=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[["state", "present", ["stage_id", "webhook_url"]]],
    )

    state = module.params["state"]
    token = module.params["token"]
    params = module.params.copy()
    del params["url"]
    del params["state"]
    del params["token"]
    del params["project_id"]
    params["url"] = module.params["webhook_url"]
    del params["webhook_url"]

    http_client = Request(
        headers={
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }
    )

    project = find_project_by_id(
        http_client, module.params["url"], module.params["project_id"]
    )

    base_url = "/".join(
        [module.params["url"], "projects", project["permalink"], "outbound_webhooks"]
    )

    if state == "present":
        create(module, http_client, base_url, params)
    elif state == "absent":
        delete(module, http_client, base_url, params)


if __name__ == "__main__":
    main()
