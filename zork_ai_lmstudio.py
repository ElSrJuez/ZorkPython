import openai

# By using an alias, the most suitable model will be downloaded 
# to your end-user's device.
# alias = "gpt-oss-20b-cuda-gpu"
alias = "Phi-3.5-mini-instruct-cuda-gpu"

# Create a FoundryLocalManager instance. This will start the Foundry 
# Local service if it is not already running and load the specified model.
manager = FoundryLocalManager(alias)

# The remaining code uses the OpenAI Python SDK to interact with the local model.

# Configure the client to use the local Foundry service
client = openai.OpenAI(
    base_url=manager.endpoint,
    api_key=manager.api_key  # API key is not required for local usage
)
