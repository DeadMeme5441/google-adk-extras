from setuptools import setup, find_packages
import os

# Read the contents of README.md
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read version from pyproject.toml
with open(os.path.join(this_directory, 'pyproject.toml'), encoding='utf-8') as f:
    import re
    content = f.read()
    version_match = re.search(r'version = "([^"]+)"', content)
    version = version_match.group(1) if version_match else '0.1.1'
    
    description_match = re.search(r'description = "([^"]+)"', content)
    description = description_match.group(1) if description_match else 'Custom implementations of Google ADK services'

setup(
    name="google-adk-extras",
    version=version,
    author="Your Name",
    author_email="your.email@example.com",
    description=description,
    long_description=long_description,
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
    python_requires=">=3.10",
    install_requires=[
        "google-genai>=1.0.0",
        "sqlalchemy>=2.0.0",
        "pymongo>=4.0.0",
        "redis>=4.0.0",
        "pyyaml>=6.0.0",
        "typing-extensions>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.15.0",
            "build>=0.10.0",
            "twine>=4.0.0",
        ],
    },
    keywords=["google", "adk", "session", "artifact", "memory", "storage", "database"],
    project_urls={
        "Bug Reports": "https://github.com/DeadMeme5441/google-adk-extras/issues",
        "Source": "https://github.com/DeadMeme5441/google-adk-extras",
        "Documentation": "https://github.com/DeadMeme5441/google-adk-extras#readme",
    },
)