import sys
import re

if sys.version_info.major == 3:
    # pylint: disable=E0611,E0401
    from urllib.error import URLError as HTTPError
else:
    from urllib2 import HTTPError


def entity_url(base_url, identifier=""):
    parts = [base_url]
    if identifier:
        parts.append(identifier)

    return "{}.json".format("/".join(parts))


def strip_disallowed_props(obj, disallowed_props):
    d = dict()
    for key in obj:
        if key not in disallowed_props:
            d[key] = obj[key]
    return d


def delete_entity(module, http_client, base_url, entity):
    try:
        url = entity_url(base_url, entity["permalink"])
        http_client.delete(url)
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
