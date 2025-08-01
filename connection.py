# mentor/core/engine/Connection.py

import os
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
# Required for type hinting the messages parameter in chat completion
from typing import List, Dict, Any, Union
from openai.types.chat import ChatCompletionMessageParam # For more specific type hinting

class Connection:
    def __init__(self):
        load_dotenv() # Load environment variables from .env file

        self.api_key = os.getenv("GPT4_API_KEY")
        self.azure_endpoint = os.getenv("GPT4_AZURE_ENDPOINT")
        # Ensure your API version matches your Azure deployment.
        # "2024-02-15" is a stable version for chat completions.
        self.api_version = os.getenv("GPT4_API_VERSION", "2024-02-15")

        # Your Azure OpenAI deployment name (e.g., "gpt-4", "gpt-35-turbo-16k")
        self.deployment_name = os.getenv("GPT4_DEPLOYMENT_NAME", "gpt-4.1") # Added to .env for flexibility

        if not all([self.api_key, self.azure_endpoint, self.deployment_name]):
            raise ValueError("Missing GPT4_API_KEY, GPT4_AZURE_ENDPOINT, or GPT4_DEPLOYMENT_NAME in environment variables. Please check your .env file.")

        # Initialize the AsyncAzureOpenAI client directly in __init__
        # This client object is what represents your "LLM" connection.
        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint,
        )

    def get_llm(self) -> AsyncAzureOpenAI:
        """
        Returns the initialized AsyncAzureOpenAI client instance.
        This client can then be used by the MentorEngine to make API calls.
        """
        return self.client

    def get_llm_deployment_name(self) -> str:
        """
        Returns the name of the LLM deployment (e.g., "gpt-4.1") to be used with the client.
        """
        return self.deployment_name

    # This is a new helper method that actually performs the chat completion.
    # MentorEngine will use the client obtained from get_llm() and call this method
    # (or directly call client.chat.completions.create)
    async def generate_chat_completion(
        self,
        messages: List[ChatCompletionMessageParam], # Expects OpenAI message format [{"role": "user", "content": "..."}]
        temperature: float = 0.3,
        max_tokens: int = 2024
    ) -> str:
        """
        Makes a chat completion call using the configured OpenAI client and deployment.
        This method encapsulates the actual API interaction.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name, # Use the stored deployment name
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ OpenAI API error in generate_chat_completion: {e}")
            # Depending on your error handling strategy, you might want to:
            # 1. Re-raise the exception: `raise`
            # 2. Return a default error message: `return "Sorry, I couldn't generate a response at this moment."`
            # For now, let's re-raise to propagate the error for debugging.
            raise


# Example usage (updated to reflect the new structure)
if __name__ == "__main__":
    import asyncio

    async def test():
        try:
            conn = Connection()
            # Get the LLM client and deployment name
            llm_client = conn.get_llm()
            llm_deployment = conn.get_llm_deployment_name()

            print(f"Obtained LLM Client: {type(llm_client)}")
            print(f"Using Deployment Name: {llm_deployment}")

            # Prepare messages in the format expected by OpenAI API
            messages_to_send: List[ChatCompletionMessageParam] = [{"role": "user", "content": "Tell me a short, funny story about a talking parrot."}]

            print(f"\nAttempting to generate chat completion...")
            # Use the new helper method to get the completion
            reply = await conn.generate_chat_completion(messages=messages_to_send)
            print("✅ LLM Response:\n", reply)

        except ValueError as ve:
            print(f"Configuration Error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred during test: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging

    asyncio.run(test())