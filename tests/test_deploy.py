# pylint: disable=redefined-outer-name,invalid-name
import time

import pytest
import requests
import testinfra


@pytest.fixture
def docker_host(host):
    def fn(container_name):
        container = host.docker(container_name)
        assert container.is_running
        return testinfra.get_host(f"docker://{container.id}")

    return fn


def test_containers_running(docker_host):
    docker_host("samson")
