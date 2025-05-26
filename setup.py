from setuptools import setup, find_packages

setup(
    name="skincare-store",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "pandas",
        "openpyxl",
        "chromadb",
        "google-generativeai",
        "python-dotenv",
    ],
) 