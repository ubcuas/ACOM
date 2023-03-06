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

run-sitl-copter: stop-sitl run-dependencies
	docker run --rm -d -p 5760-5780:5760-5780 --network acom-net --name acom-sitl ubcuas/uasitl:copter

run-sitl-plane: stop-sitl run-dependencies
	docker run --rm -d -p 5760-5780:5760-5780 --network acom-net --name acom-sitl ubcuas/uasitl:plane

run-sitl-copter-arm: stop-sitl run-dependencies
	docker run --rm -d -p 5760-5780:5760-5780 --network acom-net --name acom-sitl ubcuas/uasitl:copter-arm

run-sitl-plane-arm: stop-sitl run-dependencies
	docker run --rm -d -p 5760-5780:5760-5780 --network acom-net --name acom-sitl ubcuas/uasitl:plane-arm

run-sitl-copter-wait: run-sitl-copter
	sleep 30

run-sitl-plane-wait: run-sitl-plane
	sleep 30

run-sitl-copter-arm-wait: run-sitl-copter-arm
	sleep 30

run-sitl-plane-arm-wait: run-sitl-plane-arm
	sleep 30

run-acom: docker run-dependencies
	docker run --rm -it -p 5000:5000 --network acom-net --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:latest

run-acom-arm: docker-arm run-dependencies
	docker run --rm --name acom-production -it -p 0.0.0.0:5000:5000 --network=host --device=/dev/ttyACM0 --device=/dev/ttyACM2 --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:arm

run-acom-arm-no-winch: docker-arm run-dependencies
	docker run --rm --name acom-production -it -p 0.0.0.0:5000:5000 --network=host --device=/dev/ttyACM0 --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:arm

run-copter: run-sitl-copter run-acom

run-plane: run-sitl-plane run-acom

run-copter-arm: run-sitl-copter-arm run-acom-arm

run-plane-arm: run-sitl-plane-arm run-acom-arm

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
ci-test-copter: docker run-sitl-copter
	docker run --rm --network acom-net ubcuas/acom:latest pytest -s

ci-test-plane: docker run-sitl-plane
	docker run --rm --network acom-net ubcuas/acom:latest pytest -s
	
ci-test-copter-arm: docker-arm run-sitl-copter-arm
	docker run --rm --network acom-net ubcuas/acom:arm pytest -s

ci-test-plane-arm: docker-arm run-sitl-plane-arm
	docker run --rm --network acom-net ubcuas/acom:arm pytest -s
