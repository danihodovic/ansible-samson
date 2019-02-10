def entity_url(base_url, identifier="", json_suffix=True):
    parts = [base_url]
    if identifier:
        parts.append(identifier)

    if json_suffix:
        return "{}.json".format("/".join(parts))

    return "{}".format("/".join(parts))
