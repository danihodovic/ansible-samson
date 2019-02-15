from __future__ import absolute_import, division, print_function

__metaclass__ = type

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
    from samson_utils import delete_entity, validate_permalink, upsert_using_html
else:
    # pylint: disable=no-name-in-module, import-error
    from ansible.module_utils.samson_utils import (
        delete_entity,
        validate_permalink,
        upsert_using_html,
    )


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
        upsert_using_html(module, http_client, base_url, params, "environment")

    if state == "absent":
        delete_entity(module, http_client, base_url, params, json_suffix=False)


if __name__ == "__main__":
    main()
