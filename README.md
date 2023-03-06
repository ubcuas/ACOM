[![License: MIT](https://img.shields.io/github/license/vintasoftware/django-react-boilerplate.svg?label=License&labelColor=323940)](LICENSE)
[![Docker](https://badgen.net/badge/icon/Docker%20Hub?icon=docker&label&labelColor=323940)](https://hub.docker.com/r/ubcuas/acom/tags)
[![Docker CI](https://github.com/ubcuas/ACOM/actions/workflows/docker.yml/badge.svg)](https://github.com/ubcuas/ACOM/actions/workflows/docker.yml)

# UBC UAS ACOM

## About
Air Communication (ACOM) is the aircraft's on-board software that will be accepting commands during mission flight and change waypoint pathing ‘on-the-fly’ for the intent of dynamic obstacle avoidance.

## Setup
### Building using docker:

- First, install `docker`
- Second, to start the project run the following in the project base directory:

For x86:
```shell
ArduCopter: make run-copter
ArduPlane: make run-plane
```

For ARM:
```shell
ArduCopter: $ make run-copter-arm
ArduPlane: $ make run-plane-arm
```

See the [`Makefile`](Makefile) for other run options

## Running with serial devices connected via USB
If you want to run ACOM with a serial device instead of SITL, you must change the devices passed to docker in the [`Makefile`](Makefile), which gives Docker permission to access your serial device. Some of these have already been set up (such as the winch) and can simply be enabled in [`config.py`](config.json) and run with the associated [`Makefile`](Makefile) command. See [`Giving Docker containers access to serial devices`](README.md#giving-docker-containers-access-to-serial-devices) for more details

### Running Mode
You can choose between running in `"development"` and `"production"`. This is specified in [`config.py`](config.json) under `"runMode"` and changes which Flask config file is used (from [`instance`](/instance))

### Changing the configuration
See [`config.py`](config.json) to configure options. For IP address connection to SITL (usually testing), set `connectionMode` to `"ip"`. For a serial connection (real flight), set `connectionMode` to `"serial"`. For each, change their section values to match the desired settings.

Example with a serial device on COM8 with a baudrate of 115200
```json
{
    "setup": {
        "connectionMode": "serial",
    },
    "ip": {
        "ipAddress": "acom-sitl",
        "port": 5760
    },
    "serial": {
        "serialPort": "/dev/ttyACM0",
        "baudRate": 115200
    }
}
```

### Changing GCOM-X Endpoint
Depending on whether you are running ACOM locally or on an Odroid you will need to use different telemetry endpoints. In [`config.json`](config.json) you will see the following configurable variable. Make sure to select the endpoint you need by replacing the respective endpoint with the one listed below (testing is set by default).
```
Testing environment
"GCOMEndpoint": "http://host.docker.internal:8080/api/interop/telemetry"

Production environment
"GCOMEndpoint": "http://51.222.12.76:61633/api/interop/telemetry"
```

### Enabling Winch
The winch can be enabled and disabled in [`config.json`](config.json) by modifying the variable "winchEnable". `"winchEnable": true` will allow winch to be used, `false` will ignore winch code block (the default value is set to false). Do not use enable when the winch is not attached.

The winch statuses are as follows:
```
0 - Disconnected
1 - Standby
2 - In Progress
3 - Error
4 - Complete
5 - Emergency Reel
```

### Giving Docker containers access to serial devices
Docker containers do not have access to serial devices out of the box. Because of this, we need to give our container permission to access any devices we want to use.
- Find the name of your serial device (ex. COM8 on Windows || /dev/ttyACM0 on Linux )
- You will need to add the following flag to the Makefile: "--device DEVICENAME"

Example: 'run-acom-copter-arm' without serial devices:
```bash
run-acom-copter-arm: docker-arm run-dependencies
	docker run --rm -it -p 5000:5000 --network acom-net --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:copter-arm
```
Example Continued: 'run-acom-copter-arm' with access to '/dev/ttyACM0'
```bash
run-acom-copter-arm: docker-arm run-dependencies
	docker run --rm -it -p 5000:5000 --device /dev/ttyACM0 --network acom-net --add-host host.docker.internal:host-gateway --name acom-acom ubcuas/acom:copter-arm
```
NOTE: There is no simple way to access serial devices via Docker Desktop on Mac. This is an [open issue](https://github.com/docker/for-mac/issues/900) 😭
## Testing
- Run tests for the whole ACOM flask server:
```shell
ArduCopter: $ make ci-test-copter
ArduPlane: $ make ci-test-plane
```

**Server URL**

- [127.0.0.1:5000](http://127.0.0.1:5000) (or localhost)

but it ultimately depends on what the Flask development URL binds itself to, look in the terminal after running
```
make run-[copter/plane]
```

## Troubleshooting

`[Errno -2] Name or service not known sleeping`
> When you run acom without uas-sitl, then you will have this error as it tries to connect to SITL through mavlink, but it can't find the address. To fix it, run SITL using `make run-sitl-[copter/plane]` or kill all the acom containers and run `make run-[copter/plane]`.

