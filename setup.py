from distutils.core import setup

setup(
    name='IMUload',
    version="1.0",
    description="Load data produced by James Tompkin's Java recorder",
    author="Malcolm Reynolds",
    author_email="malcolm.reynolds@gmail.com",
    packages=["imu_load"],
    requires=["numpy"],
)