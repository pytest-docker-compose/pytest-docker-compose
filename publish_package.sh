#!/usr/bin/env bash


VERSION=$(python setup.py --version)
python setup.py sdist

curl -i -L --fail -F package=@dist/pytest-docker-compose-niva-${VERSION}.tar.gz https://${FURY_TOKEN}@push.fury.io/niva/
