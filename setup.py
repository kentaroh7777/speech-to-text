#!/usr/bin/env python3
"""Setup script for Speech-to-Text Transcriber."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README.md for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements.txt
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text(encoding="utf-8").strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="speech-to-text-transcriber",
    version="1.0.0",
    description="音声ファイル文字起こしCLI - ローカルWhisper & OpenAI API対応",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Hayashi",
    author_email="",
    url="https://github.com/yourusername/speech-to-text",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'stt=transcriber.cli:main',
        ],
    },
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
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="speech-to-text, whisper, openai, audio, transcription, cli",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/speech-to-text/issues",
        "Source": "https://github.com/yourusername/speech-to-text",
    },
) 