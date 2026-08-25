# JMU TurtleBot Fleet Monitor

This directory installs the fleet monitor only on the dedicated monitoring/web
host. It is intentionally separate from `lab_setup/install.sh`.

## Ownership model

* `rosrpt` is a dedicated system account:
  * home: `/var/lib/rosrpt`
  * shell: `/usr/sbin/nologin`
  * no personal SSH keys or login dependency
* `jmu-tb4-fleet.service` runs as `rosrpt`.
* Configuration and executables are root-owned.
* `/var/www/html/turtlebot` is root-owned.
* The short-lived publisher service runs as root only to copy validated JSON
  into the web tree.

## Data flow

    ROS fleet
        |
        v
    jmu-tb4-fleet.service (User=rosrpt)
        |
        v
    /var/lib/rosrpt/status.json
        |
        | PathChanged
        v
    jmu-tb4-publish.path
        |
        v
    jmu-tb4-publish.service (oneshot)
        |
        | copy to status.json.new
        | atomic rename
        v
    /var/www/html/turtlebot/status.json
        |
        v
    /var/www/html/turtlebot/index.html

## Install

First update the normal JMU ROS installation:

    ./lab_setup/install.sh

Then install the special fleet monitor:

    ./fleet_monitor/install.sh

Useful checks:

    systemctl status jmu-tb4-fleet.service
    systemctl status jmu-tb4-publish.path
    journalctl -u jmu-tb4-fleet.service -f
    journalctl -u jmu-tb4-publish.service
    sudo -u rosrpt cat /var/lib/rosrpt/status.json
    curl http://localhost/turtlebot/status.json


## Low-overhead sampling

Battery and dock topics remain subscribed continuously. LiDAR and camera
CameraInfo topics are subscribed only for `SAMPLE_WINDOW` seconds before each
`WRITE_INTERVAL` snapshot. With the defaults, the high-rate subscriptions are
active for 5 seconds out of each 60-second cycle. Odometry monitoring has been
removed.
