from __future__ import (
    absolute_import,
    division,
    print_function,
)  # pylint: disable=unused-variable

__metaclass__ = type  # pylint: disable=unused-variable

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
    from ansible.module_utils import (
        samson_utils,
    )  # pylint: disable=no-name-in-module, ungrouped-imports

delete_entity = samson_utils.delete_entity
validate_permalink = samson_utils.validate_permalink
upsert_using_html = samson_utils.upsert_using_html


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
