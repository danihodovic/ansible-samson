import sys
import re
import json

if sys.version_info.major == 3:
    from urllib.error import URLError as HTTPError  # pylint: disable=import-error
else:
    from urllib2 import HTTPError  # pylint: disable=import-error


DISALLOWED_PROPS = ["id", "created_at", "updated_at", "deleted_at"]


def create_using_html(module, http_client, base_url, ansible_params, item_type):
    try:
        url = entity_url(base_url, json_suffix=False)
        res = http_client.post(url, data=json.dumps(ansible_params))
        errors = extract_html_errors(res)
        if errors:
            module.fail_json(changed=False, msg=dict(errors=errors))

        # The Samson API doesn't actually use the permalink we provided on
        # creation. Instead it uses the name with whitespace replaced by dashes.
        # We need to perform a creation post-update to ensure the permalink is
        # the one the user provided.
        by_name = lambda item: item["name"] == ansible_params["name"]
        item = find_item(http_client, base_url, item_type + "s", by_name)
        url = entity_url(base_url, item["permalink"], json_suffix=False)
        http_client.patch(
            url,
            data=json.dumps(dict(permalink=ansible_params["permalink"])),
            follow_redirects=True,
        )

        by_permalink = lambda item: item["permalink"] == ansible_params["permalink"]
        item = find_item(http_client, base_url, item_type + "s", by_permalink)
        result = {"changed": True, item_type: item}
        module.exit_json(**result)
    except HTTPError as err:
        msg = err.msg
        module.fail_json(changed=False, msg=msg)


def update_using_html(module, http_client, base_url, item, ansible_params, item_type):
    new = strip_disallowed_props(item, DISALLOWED_PROPS)
    new.update(ansible_params)
    old = strip_disallowed_props(item, DISALLOWED_PROPS)

    if new == old:
        result = {"changed": False, item_type: item}
        module.exit_json(**result)

    try:
        url = entity_url(base_url, ansible_params["permalink"], json_suffix=False)
        res = http_client.patch(
            url, data=json.dumps({item_type: new}), follow_redirects=True
        )
        errors = extract_html_errors(res)
        if errors:
            module.fail_json(changed=False, msg=dict(errors=errors))

        by_permalink = lambda env: env["permalink"] == ansible_params["permalink"]
        item = find_item(http_client, base_url, item_type + "s", by_permalink)
        result = {"changed": True, item_type: item}
        module.exit_json(**result)
    except HTTPError as err:
        msg = err.msg
        module.fail_json(changed=False, msg=msg)


def upsert_using_html(
    module, http_client, base_url, ansible_params, item_type
):  # pylint: disable=unused-variable
    try:
        by_permalink = lambda dg: dg["permalink"] == ansible_params["permalink"]
        item = find_item(http_client, base_url, item_type + "s", by_permalink)

        if item:
            update_using_html(
                module, http_client, base_url, item, ansible_params, item_type
            )
        else:
            create_using_html(module, http_client, base_url, ansible_params, item_type)

    except HTTPError as err:
        module.fail_json(changed=False, msg=err.msg)


def entity_url(base_url, identifier="", json_suffix=True):
    parts = [base_url]
    if identifier:
        parts.append(identifier)

    url = format("/".join(parts))

    if json_suffix:
        return url + ".json"

    return url


def strip_disallowed_props(old, disallowed_props):
    new = old.copy()
    for key in old:
        if key in disallowed_props:
            del new[key]
    return json.loads(json.dumps(new))


def delete_entity(
    module, http_client, base_url, entity, json_suffix=True
):  # pylint: disable=unused-variable
    try:
        url = entity_url(base_url, entity["permalink"], json_suffix=json_suffix)
        http_client.delete(url, follow_redirects=True)
        module.exit_json(changed=True)
    except HTTPError as err:
        if err.code == 404:
            module.exit_json(changed=False)

        raise err


def find_item(http_client, base_url, json_key, condition):
    url = entity_url(base_url)
    res = http_client.get(url)
    items = json.load(res)[json_key]
    for item in items:
        if condition(item):
            return item
    return None


def find_project_by_id(
    http_client, base_url, project_id
):  # pylint: disable=unused-variable
    base_url = "/".join([base_url, "projects"])
    condition = lambda project: project["id"] == project_id
    return find_item(http_client, base_url, "projects", condition)


# Samson sanitizes permalinks. It transforms spaces and underscores to dashes.
# It's better to fail in this case as the permalink is the de-facto identifier.
def validate_permalink(module):  # pylint: disable=unused-variable
    VALID_PERMALINK_REGEX = "^[A-Za-z0-9-]+$"
    if not bool(re.search(VALID_PERMALINK_REGEX, module.params["permalink"])):
        msg = "Permalink should match `{}`".format(VALID_PERMALINK_REGEX)
        module.exit_json(changed=False, msg=msg)


def extract_html_errors(res):
    html = res.read()
    lines = html.split("\n")
    err_line_idx = None
    for idx, line in enumerate(lines):
        if re.search("There was an error", line):
            err_line_idx = idx

    if not err_line_idx:
        return []

    err_line = lines[err_line_idx + 1]
    errors = (
        err_line.strip()
        .replace("<ul>", "")
        .replace("</ul>", "")
        .replace("<li>", "")
        .split("</li>")
    )

    # Filter out any whitespace entries
    return [e for e in errors if e != ""]
