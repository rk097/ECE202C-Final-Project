# Info

Project for ECE202C, using an agentic LLM to evaluate simulated firmware samples for potential security risks using provided tools and also its own reasoning capabilities.

# Setup

You will need an OpenAI API key, which you should put in a `.env` file. `.env.example` provides the format.

Setup python venv (assuming Linux). I am running Python 3.12.3.

```Shell
python -m venv [DIRECTORYNAME]
source .venv/bin/activate
```

Install packages from `requirements.txt`

```Shell
pip install requirements.txt
```

Run agent

```Shell
python run_agent.py samples
```