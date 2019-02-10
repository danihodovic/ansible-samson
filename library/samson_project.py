from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import Request


def project_url(samson_url, project=None):
    if project:
        return "{}/projects/{}.json".format(samson_url, project["permalink"])

    return "{}/projects.json".format(samson_url)


def strip_disallowed_props(project):
    new_project = dict()
    disallowed_props = (
        "id",
        "created_at",
        "updated_at",
        "build_command_id",
        "docker_image_building_disabled",
        "build_with_gcb",
        "kubernetes_allow_writing_to_root_filesystem",
    )
    for key in project:
        if key not in disallowed_props:
            new_project[key] = project[key]
    return new_project


def create(module, http_client, samson_url, ansible_params):
    url = project_url(samson_url)
    res = http_client.post(url, data=json.dumps(ansible_params))
    project = json.load(res)["project"]

    # Samson doesn't use the permalink we give to it, so we have to update
    # the project post-creation to ensure the permalink is the one the user
    # provided
    url = "{}/projects/{}.json".format(samson_url, project["permalink"])
    data = {"permalink": ansible_params["permalink"]}
    try:
        res = http_client.patch(url, data=json.dumps(data))
        project = json.load(res)["project"]
        module.exit_json(changed=True, project=project)
    # pylint: disable=W0703
    except Exception as err:
        msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def update(module, http_client, samson_url, project, ansible_params):
    updated_project = project.copy()
    updated_project.update(ansible_params)
    updated_project = strip_disallowed_props(updated_project)
    project_copy = strip_disallowed_props(project)

    if project_copy == updated_project:
        module.exit_json(changed=False, project=project)

    try:
        url = project_url(samson_url, project)
        res = http_client.patch(url, data=json.dumps(updated_project))
        project = json.load(res)["project"]
        module.exit_json(changed=True, project=project)
    # pylint: disable=W0703
    except Exception as err:
        msg = json.load(err)
        module.fail_json(changed=False, msg=msg)


def upsert(module, http_client, samson_url, ansible_params):
    try:
        url = project_url(samson_url, ansible_params)
        res = http_client.get(url)
        project = json.load(res)["project"]
        update(module, http_client, samson_url, project, ansible_params)
    # pylint: disable=W0703
    except Exception as err:
        if not hasattr(err, "code"):
            raise err
        # pylint: disable=E1101
        if err.code != 404:
            msg = json.load(err)
            module.fail_json(changed=False, msg=msg)

        create(module, http_client, samson_url, ansible_params)


def delete(module, http_client, samson_url, project_params):
    try:
        http_client.delete(project_url(samson_url, project_params))
        module.exit_json(changed=True)
    # pylint: disable=W0703
    except Exception as err:
        # pylint: disable=E1101
        if hasattr(err, "code") and err.code == 404:
            module.exit_json(changed=False)

        raise err


def main():
    argument_spec = dict(
        state=dict(default="present", type="str", choices=["absent", "present"]),
        url=dict(required=True, type="str"),
        token=dict(required=True, type="str"),
        permalink=dict(required=True, type="str"),
        name=dict(type="str"),
        repository_url=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[["state", "present", ["name", "repository_url"]]],
    )

    samson_url = module.params["url"]
    state = module.params["state"]
    project_params = dict(
        (k, module.params[k]) for k in ("permalink", "repository_url", "name")
    )

    http_client = Request(
        headers={
            "Authorization": "Bearer {}".format(module.params["token"]),
            "Content-Type": "application/json",
        }
    )

    if state == "present":
        upsert(module, http_client, samson_url, project_params)

    if state == "absent":
        delete(module, http_client, samson_url, project_params)


if __name__ == "__main__":
    main()
