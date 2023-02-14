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

run-sitl-arm: stop-sitl run-dependencies
	docker run --rm -d -p 5760-5780:5760-5780 --network acom-net --name acom-sitl ubcuas/uasitl:arm

run-sitl-wait: run-sitl-arm
	sleep 30

run-acom: docker run-dependencies
	docker run --rm -it -p 5000:5000 --network acom-net --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:latest

run-acom-arm: docker-arm run-dependencies
	docker run --rm --name acom-production -it -p 0.0.0.0:5000:5000 --network=host --device=/dev/ttyACM0 --device=/dev/ttyACM2 --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:arm

run-acom-arm-no-winch: docker-arm run-dependencies
	docker run --rm --name acom-production -it -p 0.0.0.0:5000:5000 --network=host --device=/dev/ttyACM0 --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:arm

run: run-sitl run-acom

run-arm: run-sitl-arm run-acom-arm

stop: stop-sitl

## Docker ##
docker:
	docker build . --pull=true --tag ubcuas/acom:latest

docker-arm:
	docker build . --pull=true --tag ubcuas/acom:arm --platform "linux/arm64"

docker-publish: docker
	docker push ubcuas/acom:latest

docker-publish-arm: docker-arm
	docker push ubcuas/acom:arm

## CI ##
ci-test: docker run-sitl
	docker run --rm --network acom-net ubcuas/acom:latest pytest -s
	
ci-test-arm: docker-arm run-sitl-arm
	docker run --rm --network acom-net ubcuas/acom:arm pytest -s
