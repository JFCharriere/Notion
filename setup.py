from setuptools import setup, find_packages

setup(
    name="notion-api-client",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "notion-cli=cli:main",
        ],
    },
    python_requires=">=3.10",
)
