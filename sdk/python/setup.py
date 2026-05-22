#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: facesdk/sdk/python/setup.py
Copyright (c) 2024 FaceSDK Contributors
MIT License

FaceSDK Python SDK - Setup Configuration
"""

from setuptools import setup, find_packages
import os

# 读取 README 文件
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "FaceSDK Python SDK - A comprehensive face recognition solution"

setup(
    name="facesdk-python",
    version="1.0.0",
    author="FaceSDK Team",
    author_email="team@facesdk.io",
    description="Python SDK for FaceSDK - A comprehensive face recognition solution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/facesdk/facesdk-python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "aiohttp>=3.8.0",
        "urllib3>=1.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "facesdk=facesdk.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
