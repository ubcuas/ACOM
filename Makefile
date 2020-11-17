## Util ##
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

## Dependencies ##
delete-network:
	docker network rm acom-net

create-network:
	docker network create acom-net || echo "===== Network acom-net already exists ====="

run-dependencies: create-network

## Run ##
stop-sitl:
	docker kill acom-sitl || echo "===== Container acom-sitl already killed & removed ====="

run-sitl: stop-sitl run-dependencies
	docker run --rm -d -p 5760-5780:5760-5780 --network acom-net --name acom-sitl ubcuas/uasitl:latest

run-sitl-wait: run-sitl
	sleep 30

run-acom: docker run-dependencies
	docker run --rm -it -p 5000:5000 --network acom-net --name acom-acom ubcuas/acom:latest

run: run-sitl run-acom

stop: stop-sitl

## Docker ##
docker-multiarch-deps:
	DOCKER_CLI_EXPERIMENTAL=enabled DOCKER_BUILDKIT=enabled docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
	DOCKER_CLI_EXPERIMENTAL=enabled DOCKER_BUILDKIT=enabled docker buildx create --name mubuilder | echo "ok"
	DOCKER_CLI_EXPERIMENTAL=enabled DOCKER_BUILDKIT=enabled docker buildx use mubuilder
	DOCKER_CLI_EXPERIMENTAL=enabled DOCKER_BUILDKIT=enabled docker buildx inspect --bootstrap

docker:
	docker build . --pull=true --tag ubcuas/acom:latest

docker-publish: docker
	docker push ubcuas/acom:latest

docker-multiarch: docker-multiarch-deps
	DOCKER_CLI_EXPERIMENTAL=enabled \
	DOCKER_BUILDKIT=enabled \
	docker buildx build . --pull=true -t ubcuas/acom:latest --platform "linux/amd64"

docker-multiarch-publish: docker-multiarch-deps
	DOCKER_CLI_EXPERIMENTAL=enabled \
	DOCKER_BUILDKIT=enabled \
	docker buildx build . --pull=true -t ubcuas/acom:latest --push --platform "linux/amd64"

## CI ##
ci-test: docker run-sitl-wait
	docker run --rm --network acom-net ubcuas/acom:latest pytest -s
