
import json
import anthropic
from groq import Groq
# import CodeC_helpers
import re
import json
import anthropic

def read_recent_history(turns=10):
    with open("../conversational_history.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
        recent_history = [json.loads(line) for line in lines[-turns:]]  # Last 'turns' turns
    return recent_history


# def format_history_as_string(turns = 10):
#     formatted_string = ""
    
#     with open("../conversational_history.txt", "r", encoding="utf-8") as f:
#         lines = f.readlines()[-turns:]        
#         for line in lines:
#             entry = json.loads(line)
#             # Format: "Agent1: Hello\n"
#             formatted_string += f"{entry['role'].capitalize()}: {entry['content']}\n"
            
#     return formatted_string
def format_history_as_string(turns=10):
    formatted_string = ""
    
    try:
        with open("../conversational_history.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Take the last N lines
            lines = lines[-turns:]
            
            for line in lines:
                # 1. Strip whitespace
                line = line.strip()
                
                # 2. Skip if empty
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    role = entry.get('role', 'Unknown').capitalize()
                    content = entry.get('content', '')
                    formatted_string += f"{role}: {content}\n"
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line: {line}")
                    continue
                    
    except FileNotFoundError:
        return "No history found."
            
    return formatted_string



def agent_sim(model_LLM, plan_sys_prompt, user_query):
    # Add your Groq API key here (get one for free at https://console.groq.com/keys)
    # api_key = "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"  # Replace with your actual API key

#   client = Groq(api_key=api_key)
#   completion = client.chat.completions.create(
#       model= model_LLM, #"llama-3.1-8b-instant", #"llama-3.3-70b-versatile",
#       messages=[
#           {
#               "role": "system",
#               "content": plan_sys_prompt  # Your system prompt here
#           },
#         {
#           "role": "user",
#           "content": user_query          
#         },
#       ],
#       temperature=1,
#       max_completion_tokens=1024,
#       top_p=1,
#       stream=True,
#       stop=None
#   )
    client = anthropic.Anthropic(api_key="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" ) # Replace with your actual key    
    response = client.messages.create(
        model=model_LLM,
        max_tokens=2048,
        temperature=1.0,  # Claude supports temperature
        system=plan_sys_prompt,  # System prompt goes here (not in messages)
        messages=[
            {
                "role": "user",
                "content": user_query
            }
        ]
    )
    return response.content[0].text

#   response_content = ""
#   for chunk in completion:
#       chunk_content = chunk.choices[0].delta.content or ""
#       response_content += chunk_content
#       # print(chunk_content, end="")  # Optional: Still print to console if you want to see it live
#   return response_content
