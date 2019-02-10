# Ansible modules for Samson

[![Build Status](https://travis-ci.com/danihodovic/ansible-samson.svg?token=6sXanBXhj7Q9ifyk7ptK&branch=master)](https://travis-ci.com/danihodovic/ansible-samson)

This role contains modules to simplify working with
[Samson](https://github.com/zendesk/samson).

It supports:

- projects
- stages

### Example Playbook

```yml
- name: Samson
  hosts: localhost
    - name: Create a project
      samson_project:
        url: https://samson.myorg.com
        token: '{{ samson_oauth_token }}'
        permalink: dotfiles
        name: dotfiles
        repository_url: https://github.com/danihodovic/.dotfiles

    - name: Delete a project
      samson_project:
        state: absent
        url: https://samson.myorg.com
        token: '{{ samson_oauth_token }}'
        permalink: dotfiles
        name: dotfiles
        repository_url: https://github.com/danihodovic/.dotfiles
```

License
-------

MIT

### Author Information

This role is created and maintained by Dani Hodovic.
