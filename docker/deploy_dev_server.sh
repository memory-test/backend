#!/bin/bash
set -e

# change work directory to env or prod
cd ~/backend

# Convert multiple arguments for docker compose to short function
run_compose() {
    # merge yaml files for production
    local compose_files="-f docker-compose.yml -f docker/docker-compose.server.yml"
    local project_name="dev"
    # run command
    docker compose \
        -p "${project_name}" \
        ${compose_files} \
        "$@"
}


echo "Build new images"
run_compose build -q

echo "Start all production containers"
run_compose up -d

# if some container addresses changed, nginx restart is necessary
run_compose restart gateway

#wait for health checking
sleep 5

#show final result
run_compose ps

echo "Remove dangling images"
docker image prune -f

