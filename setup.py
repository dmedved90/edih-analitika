"""
Setup script for EDIH Analytics Dashboard
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="edih-analytics",
    version="5.0.0",
    author="UNIRI / Syntagent",
    author_email="support@edihadria.eu",
    description="Analytics dashboard for EDIH ADRIA services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/edih-analytics",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "edih-analytics=app:main",
        ],
    },
)
