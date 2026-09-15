from glob import glob
from setuptools import find_packages, setup

package_name = 'tf_package_reference'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='molloykp',
    maintainer_email='molloykp@jmu.edu',
    description='CS 354 reference showing relative topics and namespaced TF.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'frame_demo = tf_package_reference.frame_demo:main',
        ],
    },
)
