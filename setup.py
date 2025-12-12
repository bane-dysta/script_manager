from setuptools import setup, find_packages

setup(
    name="script_manager",
    version="1.1.0",
    packages=find_packages(),
    install_requires=[
        "tkinterdnd2",
        "pyyaml",
    ],
    entry_points={
        'console_scripts': [
            'script_manager=main:main',
        ],
    },
    author="Your Name",
    description="Python脚本管理器",
    python_requires=">=3.6",
) 