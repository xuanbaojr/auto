#!/bin/bash

# Allow X server connections from the local machine
xhost +local:docker

# Build and run the Docker container
docker-compose up --build

# Revoke X server access when done
xhost -local:docker
