# JMU CS354 TurtleBot lab-machine setup

## Proposed repository layout

```text
jmu_tb4_cs354/                 # Git repository
├── README.md
├── ros/
│   └── jmu_tb4_cs354/         # ROS package
│       ├── CMakeLists.txt
│       ├── package.xml
│       └── launch/
│           ├── sim.launch.py
│           ├── spawn.launch.py
│           └── tb4_sim.launch.py
└── lab_setup/
    ├── install.sh
    └── tb4_setup.bash
```

Move the existing ROS package files into `ros/jmu_tb4_cs354/`. The files in
this bundle do not replace those existing launch files.

## Machine installation

Run as an administrative account, without putting `sudo` in front:

```bash
./lab_setup/install.sh
```

The installer:

1. sources `/opt/ros/jazzy/setup.bash`;
2. builds the ROS packages beneath `ros/`;
3. installs that ROS install space under `/opt/jmu/cs354/ros`;
4. makes the installed files root-owned/non-writable by students;
5. installs `tb4_setup.bash` as `/opt/jmu/cs354/tb4_setup.bash`;
6. adds a small source hook to `/etc/bash.bashrc`.

Each new interactive Bash terminal then sources ROS environments in this
order:

```text
/opt/ros/jazzy
    -> /opt/jmu/cs354/ros
        -> ~/rosdev/install     (if the student has built an overlay)
```

## Student selection

The student runs:

```bash
tb4-select
```

and chooses:

- `S` for simulation, namespace `/robot9`
- `1` through `7` for physical robots `/robot1` through `/robot7`

Physical discovery uses the stable DNS names:

```text
tb1.cs.jmu.edu
...
tb7.cs.jmu.edu
```

A student's persistent selection is stored in:

```text
~/.config/jmu_tb4/selection
```

## Simulator namespace change

`tb4_sim.launch.py` should use `ROBOT_NAMESPACE` as the default value of its
`namespace` launch argument. See:

```text
ros_changes/tb4_sim_namespace_snippet.txt
```

## Teleoperation

`teleop_twist_keyboard` publishes to the relative topic `cmd_vel`, but the
JMU environment variable `ROBOT_NAMESPACE` does not automatically set the ROS
namespace of arbitrary programs.

The shell helper therefore provides:

```bash
tb4-teleop
```

which explicitly launches `teleop_twist_keyboard` in the currently selected
namespace.
