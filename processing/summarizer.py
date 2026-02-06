from openai import OpenAI
from config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)




def summarize(text):
    resp = client.responses.create(
    model="gpt-4.1-mini",
    input=f"Summarize this automotive article in 3 bullet points:\n{text}"
    )
    return resp.output[0].content[0].text