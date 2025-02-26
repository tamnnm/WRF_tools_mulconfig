from setuptools import setup, find_packages

setup(
    name='wrf_tools',
    version='0.1.0',
    author='Quang-Van Doan',
    author_email='doan.van.gb@...',
    description='Tools for processing WRF and downloading ERA5 data',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/your-repo/wrf_tools',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'xarray',
        'pandas',
        'cdsapi',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
