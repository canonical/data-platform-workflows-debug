import dataclasses
import json
import logging
import os
import subprocess

import boto3
import pytest
import random
import string


@dataclasses.dataclass(frozen=True)
class ConnectionInformation:
    access_key_id: str
    secret_access_key: str
    bucket: str


def _gen_random_string(length):
    return ''.join(
        random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits
        ) for _ in range(10)
    )


def _create_new_keys(access_key, secret_key):
    logger.info("Creating keys")
    subprocess.run(
        [
            "sudo",
            "microceph.radosgw-admin",
            "key",
            "create",
            "--uid=test",
            "--key-type=s3",
            "--access-key", access_key,
            "--secret-key", secret_key,
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
    ).stdout


@pytest.fixture(scope="session")
def microceph():
    if not os.environ.get("CI") == "true":
        raise Exception("Not running on CI. Skipping microceph installation")
    if "microceph" in subprocess.check_output(
        ["snap", "list"]
    ).decode("utf-8"):
        logger.info("Microceph already installed, keeping it")
        access_key = _gen_random_string(10)
        secret_key = _gen_random_string(24)
        _create_new_keys(access_key, secret_key)
        return ConnectionInformation(access_key, secret_key, _BUCKET)

    logger.info("Setting up microceph")
    subprocess.run(["sudo", "snap", "install", "microceph"], check=True)
    subprocess.run(["sudo", "microceph", "cluster", "bootstrap"], check=True)
    subprocess.run(
        ["sudo", "microceph", "disk", "add", "loop,4G,3"],
        check=True
    )
    subprocess.run(["sudo", "microceph", "enable", "rgw"], check=True)
    output = subprocess.run(
        [
            "sudo",
            "microceph.radosgw-admin",
            "user",
            "create",
            "--uid",
            "test",
            "--display-name",
            "test",
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
    ).stdout
    key = json.loads(output)["keys"][0]
    key_id = key["access_key"]
    secret_key = key["secret_key"]
    logger.info("Creating microceph bucket")
    boto3.client(
        "s3",
        endpoint_url="http://localhost",
        aws_access_key_id=key_id,
        aws_secret_access_key=secret_key,
    ).create_bucket(Bucket=_BUCKET)
    logger.info("Set up microceph")
    return ConnectionInformation(key_id, secret_key, _BUCKET)


_BUCKET = "testbucket"
logger = logging.getLogger(__name__)
