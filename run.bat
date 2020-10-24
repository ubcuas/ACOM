docker-compose stop sitl
docker-compose run --rm flask pytest
docker-compose stop sitl