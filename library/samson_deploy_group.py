from __future__ import absolute_import, division, print_function, unicode_literals

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
        extract_html_errors,
        find_item,
        upsert_using_html,
    )
else:
    # pylint: disable=no-name-in-module, import-error
    from ansible.module_utils.samson_utils import (
        entity_url,
        strip_disallowed_props,
        delete_entity,
        validate_permalink,
        extract_html_errors,
        find_item,
        upsert_using_html,
    )


if sys.version_info.major == 3:
    # pylint: disable=no-name-in-module, import-error
    from urllib.error import URLError as HTTPError
else:
    from urllib2 import HTTPError


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        permalink=dict(required=True, type="str"),
        name=dict(type="str"),
        env_value=dict(required=False, type="str"),
        environment_id=dict(required=True, type="int"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec, required_if=[["state", "present", ["name"]]]
    )

    validate_permalink(module)

    base_url = "/".join([module.params["url"], "deploy_groups"])
    state = module.params["state"]
    params = dict(
        (k, module.params[k])
        for k in ("permalink", "name", "env_value", "environment_id")
    )
    params = dict((k, v) for k, v in params.iteritems() if v)

    http_client = Request(
        headers={
            "Authorization": "Bearer {}".format(module.params["token"]),
            "Content-Type": "application/json",
        }
    )

    if state == "present":
        upsert_using_html(module, http_client, base_url, params, "deploy_group")

    if state == "absent":
        delete_entity(module, http_client, base_url, params, json_suffix=False)


if __name__ == "__main__":
    main()
