from setuptools import setup, find_packages

setup(
    name="secure_lora",            # name of your package
    version="0.1.0",               # start with 0.1.0
    packages=find_packages(where="src"),  # finds packages under src/
    package_dir={"": "src"},       # tells Python that packages live in src/
    install_requires=[             # optional, list dependencies
        # "numpy",
        # "torch",
    ],
    python_requires=">=3.8",       # minimum Python version
)