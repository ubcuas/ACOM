[![License: MIT](https://img.shields.io/github/license/vintasoftware/django-react-boilerplate.svg)](LICENSE.txt)

# UBC UAS ACOM

## About
Air Communcation (ACOM) is the aircrafts’ on-board software that will be accepting commands during mission flight and change waypoint pathing ‘on-the-fly’ for the intent of dynamic obstacle avoidance.

See the full documentation on UAS confluence [here](http://confluence.ubcuas.com/display/GCOM/ACOM+Documentation) (Note: You have to be using ubcsecure or the UBC VPN in order to access.)

## Setup
** Building using docker:**

- First, install `docker`
- Second, run the build command

```shell
    $ sudo docker build -t acom:latest .
```

## Running - docker

```shell
    $ sudo docker run -d -p 5000:5000 acom
```

**Server URL**

- http://127.0.0.1:5000/