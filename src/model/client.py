import requests

class ModelClient:
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

    def chat(self, messages: list) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def ask(self, question: str) -> str:
        messages = [{"role": "user", "content": question}]
        return self.chat(messages)

    def chat_with_system(self, system_prompt: str, messages: list) -> str:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        return self.chat(full_messages)

    def ask_with_system(self, system_prompt: str, question: str) -> str:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
        return self.chat(messages)
