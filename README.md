# Ansible modules for Samson

[![Build Status](https://travis-ci.com/danihodovic/ansible-samson.svg?token=6sXanBXhj7Q9ifyk7ptK&branch=master)](https://travis-ci.com/danihodovic/ansible-samson)

This role contains modules to simplify working with
[Samson](https://github.com/zendesk/samson).

It supports:

- projects
- stages

### Example Playbook

```yml
---
- name: Samson
  hosts: localhost
  roles:
    - danihodovic.samson
  vars:
    samson_url: https://samson.mycompany.org
    # Hide this in the Ansible vault or pass it through the environment instead
    # of checking it in as plaintext
    samson_token: 967c19e2e223682d232935661f0675b0ddd4930f9e77ce32cad51bc65b24bbbc
  tasks:
    - name: Create dotfiles project
      register: project
      samson_project:
        url: '{{ samson_url }}'
        token: '{{ samson_token }}'
        permalink: dotfiles
        name: dotfiles
        repository_url: https://github.com/danihodovic/.dotfiles

    - name: Create staging
      samson_stage:
        url: '{{ samson_url }}'
        token: '{{ samson_token }}'
        name: staging
        permalink: staging
        project_permalink: '{{ project.project.permalink }}'

    - name: Create deployment command
      samson_command:
        url: '{{ samson_url }}'
        token: '{{ samson_token }}'
        project_id: '{{ project.project.id }}'
        command: |
          echo "deploying my project!"
```

License
-------

MIT

### Author Information

This role is created and maintained by Dani Hodovic.
