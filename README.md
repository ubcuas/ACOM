[![License: MIT](https://img.shields.io/github/license/vintasoftware/django-react-boilerplate.svg)](LICENSE.txt)

# UBC UAS ACOM

## About
Air Communcation (ACOM) is the aircrafts’ on-board software that will be accepting commands during mission flight and change waypoint pathing ‘on-the-fly’ for the intent of dynamic obstacle avoidance.

See the full documentation on UAS confluence [here](http://confluence.ubcuas.com/display/GCOM/ACOM+Documentation) (Note: You have to be using ubcsecure or the UBC VPN in order to access.)

## Setup
### Building using docker:

- First, install `docker`
- Second, to start the project run the following in the project base directory:

```shell
    $ make run
```

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

