from setuptools import setup, find_packages
import os
import re

ROOT = os.path.abspath(os.path.dirname(__file__))


def read(fname: str) -> str:
    with open(os.path.join(ROOT, fname), encoding="utf-8") as f:
        return f.read()


def meta_from_pyproject():
    content = read("pyproject.toml")
    version = re.search(r'\nversion\s*=\s*"([^"]+)"', content)
    desc = re.search(r'\ndescription\s*=\s*"([^"]+)"', content)
    return (
        version.group(1) if version else "0.1.5",
        desc.group(1) if desc else "Production-ready services and FastAPI wiring for Google ADK",
    )


version, description = meta_from_pyproject()

setup(
    name="google-adk-extras",
    version=version,
    author="DeadMeme5441",
    author_email="deadunderscorememe@gmail.com",
    description=description,
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/DeadMeme5441/google-adk-extras",
    packages=find_packages(where="src", include=["google_adk_extras", "google_adk_extras.*"]),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10,<3.13",
    install_requires=[
        "google-adk",
        "google-genai",
    ],
    extras_require={
        # Storage backends
        "sql": ["sqlalchemy"],
        "mongodb": ["pymongo"],
        "redis": ["redis"],
        "yaml": ["pyyaml"],
        "s3": ["boto3"],
        # Credentials
        "jwt": ["PyJWT"],
        # Web
        "web": ["fastapi", "watchdog"],
        # Dev
        "dev": ["pytest", "pytest-asyncio", "build", "twine"],
        # Everything
        "all": ["google-adk-extras[sql,mongodb,redis,yaml,s3,jwt,web]"],
    },
    keywords=["google", "adk", "session", "artifact", "memory", "storage", "database"],
    project_urls={
        "Bug Reports": "https://github.com/DeadMeme5441/google-adk-extras/issues",
        "Source": "https://github.com/DeadMeme5441/google-adk-extras",
        "Documentation": "https://github.com/DeadMeme5441/google-adk-extras#readme",
    },
)
