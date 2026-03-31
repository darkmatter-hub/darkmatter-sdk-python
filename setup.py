from setuptools import setup, find_packages

setup(
    name="darkmatter",
    version="0.1.0",
    description="Replay, fork, and verify any AI workflow. Execution record for AI agent pipelines.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Ben Gunvl",
    author_email="hello@darkmatterhub.ai",
    url="https://darkmatterhub.ai",
    project_urls={
        "Documentation": "https://darkmatterhub.ai/docs",
        "Source": "https://github.com/bengunvl/darkmatter",
        "Changelog": "https://github.com/bengunvl/darkmatter/releases",
    },
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],  # zero dependencies — stdlib only
    extras_require={
        "langgraph":  ["langgraph>=0.1.0"],
        "anthropic":  ["anthropic>=0.20.0"],
        "openai":     ["openai>=1.0.0"],
        "all":        ["langgraph>=0.1.0", "anthropic>=0.20.0", "openai>=1.0.0"],
    },
    entry_points={
        "console_scripts": [
            "darkmatter=darkmatter.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="ai agents llm execution record replay fork verify lineage audit anthropic openai langgraph",
)
