import sys
import re

if sys.version_info.major == 3:
    # pylint: disable=E0611,E0401
    from urllib.error import URLError as HTTPError
else:
    from urllib2 import HTTPError


def entity_url(base_url, identifier="", json_suffix=True):
    parts = [base_url]
    if identifier:
        parts.append(identifier)

    url = format("/".join(parts))

    if json_suffix:
        return url + ".json"

    return url


def strip_disallowed_props(obj, disallowed_props):
    d = dict()
    for key in obj:
        if key not in disallowed_props:
            d[key] = obj[key]
    return d


def delete_entity(module, http_client, base_url, entity, json_suffix=True):
    try:
        url = entity_url(base_url, entity["permalink"], json_suffix=json_suffix)
        http_client.delete(url, follow_redirects=True)
        module.exit_json(changed=True)
    except HTTPError as err:
        if err.code == 404:
            module.exit_json(changed=False)

        raise err


# Samson sanitizes permalinks. It transforms spaces and underscores to dashes.
# It's better to fail in this case as the permalink is the de-facto identifier.
def validate_permalink(module):
    VALID_PERMALINK_REGEX = "^[A-Za-z0-9-]+$"
    if not bool(re.search(VALID_PERMALINK_REGEX, module.params["permalink"])):
        msg = "Permalink should match `{}`".format(VALID_PERMALINK_REGEX)
        module.exit_json(msg=msg)
