[![License: MIT](https://img.shields.io/github/license/vintasoftware/django-react-boilerplate.svg)](LICENSE.txt)

# UBC UAS ACOM

## About
Air Communcation (ACOM) is the aircrafts’ on-board software that will be accepting commands during mission flight and change waypoint pathing ‘on-the-fly’ for the intent of dynamic obstacle avoidance.

See the full documentation on UAS confluence [here](http://confluence.ubcuas.com/display/GCOM/ACOM+Documentation) (Note: You have to be using ubcsecure or the UBC VPN in order to access.)

## Setup
### Building using docker:

- First, install `docker`
- Second, to start the project run the following in the project base directory:

For x86:
```shell
    $ make run
```

For ARM:
```shell
    $ make run-arm
```
## Running with serial devices connected via USB
If you want to run ACOM with a serial device instead of SITL, you must change the `config.py`, and give Docker permission to access your serial device.

### Changing the configuration
Comment out the `IP_ADDRESS` and `PORT` constants.

After that, uncomment `SERIAL_PORT` and `BAUD_RATE`.

Then, change their values to match your serial device.

Example `config.py` with a serial device on COM8 with a baudrate of 115200
```py
...

# set optional default ip address & port
# IP_ADDRESS = "acom-sitl"
# PORT = 5760

# set optional default serial port & baud rate
SERIAL_PORT = "COM8"
BAUD_RATE = 115200
```

### Changing GCOM-X Endpoint
Depending on whether you are running ACOM locally or on an Odroid you will need to use different telemetry endpoints. In `vehicle.py` you will see the following. Make sure to select the one you need by uncommenting the respective endpoint (local is set by default).
```py

# Testing environment
GCOM_TELEMETRY_ENDPOINT = "http://host.docker.internal:8080/api/interop/telemetry"

# Production environment
# GCOM_TELEMETRY_ENDPOINT = "http://51.222.12.76:61633/api/interop/telemetry"
```
For flight change GCOM endpoint in  etc/config.json 

### Giving Docker containers access to serial devices
Docker containers do not have access to serial devices out of the box. Because of this, we need to give our container permission to access any devices we want to use.
- Find the name of your serial device (ex. COM8 on Windows || /dev/ttyACM0 on Linux )
- You will need to add the following flag to the Makefile: "--device DEVICENAME"

Example: 'run-acom-arm' without serial devices:
```bash
run-acom-arm: docker-arm run-dependencies
	docker run --rm -it -p 5000:5000 --network acom-net --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:arm
```
Example Continued: 'run-acom-arm' with access to '/dev/ttyACM0'
```bash
run-acom-arm: docker-arm run-dependencies
	docker run --rm -it -p 5000:5000 --device /dev/ttyACM0 --network acom-net --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:arm
```
NOTE: There is no simple way to access serial devices via Docker Desktop on Mac. This is an [open issue](https://github.com/docker/for-mac/issues/900) 😭
## Testing
- Run tests for the whole ACOM flask server:
```shell
	$ make ci-test
```

**Server URL**

- http://172.21.0.3:5000/

but it ultimately depends on what the Flask development URL binds itself to, look in the terminal after running
```
make run
```

## Troubleshooting

`[Errno -2] Name or service not known sleeping`
> When you run acom without uas-sitl, then you will have this error as it tries to connect to SITL through mavlink, but it can't find the address. To fix it, run SITL using `make run-sitl` or kill all the acom containers and run `make run`.

