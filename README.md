[![License: MIT](https://img.shields.io/github/license/vintasoftware/django-react-boilerplate.svg)](LICENSE.txt)

# UBC UAS ACOM

## About
Air Communcation (ACOM) is the aircrafts’ on-board software that will be accepting commands during mission flight and change waypoint pathing ‘on-the-fly’ for the intent of dynamic obstacle avoidance.

See the full documentation on UAS confluence [here](http://confluence.ubcuas.com/display/GCOM/ACOM+Documentation) (Note: You have to be using ubcsecure or the UBC VPN in order to access.)

## Setup
** Building using docker:**

- First, install `docker` and `docker-compose`
- Second, to start the project run the following in the project base directory:

```shell
    $ sudo docker-compose up
```

**Server URL**

- http://127.0.0.1:5000/