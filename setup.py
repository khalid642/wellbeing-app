from setuptools import setup, find_packages

setup(
    name="wellbeing-app",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "wellbeing_app.themes": ["*.css"],
        "wellbeing_app.storage": ["*.sql"],
    },
)
