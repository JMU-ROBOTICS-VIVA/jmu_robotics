from setuptools import find_packages, setup

package_name = 'jmu_tb4_fleet'

setup(
    name=package_name,
    version='0.5.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/web', ['web/index.html']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Kevin Molloy',
    maintainer_email='molloykp@jmu.edu',
    description='JMU TurtleBot 4 fleet monitoring utilities.',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'fleet_status = jmu_tb4_fleet.fleet_status:main',
        ],
    },
)
