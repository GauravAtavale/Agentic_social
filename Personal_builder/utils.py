
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
    if model_LLM.split("-")[0] == 'claude':
        # print("Claude model selected")
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

    elif model_LLM.split("-")[0] in ['llama', 'meta']:
        # print("LLaMA model selected")
        # Add your Groq API key here (get one for free at https://console.groq.com/keys)
        api_key = "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"  # Replace with your actual API key

        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model= model_LLM, #"llama-3.1-8b-instant", #"llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": plan_sys_prompt  # Your system prompt here
                },
                {
                "role": "user",
                "content": user_query          
                },
            ],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=True,
            stop=None
        )

        response_content = ""
        for chunk in completion:
            chunk_content = chunk.choices[0].delta.content or ""
            response_content += chunk_content
            # print(chunk_content, end="")  # Optional: Still print to console if you want to see it live
        return response_content

def generate_bid_score_each_user(person_name, credits_left, model_LLM):
    """
    Updates: Function updated to generate bid for each person upon request.
    TO DO: get percentage as a response.
    """
    # bid_scores = {}
    with open(f"{person_name}_persona_prompt.txt", "r") as f:
        persona_prompt = f.read()
    
    conversation_hist_format = format_history_as_string(turns = 10)
    
    with open(f"bidding_sys_prompt.txt", "r") as f:
        bidding_system_prompt = f.read()
    
    bidding_system_prompt = bidding_system_prompt.replace("||", str(credits_left[person_name]))
    
    # bidding_system_prompt = bidding_system_prompt + "\n\n" + "Persona: " + persona_prompt + "\n\n" + "Conversation History: \n" + conversation_hist_format
    plan_sys_prompt = bidding_system_prompt
    user_query = "Persona: " + persona_prompt + "\n\n" + "Conversation History: \n" + conversation_hist_format

    history = []
    history.append({"role": "user", "content": bidding_system_prompt})
    bid_score = agent_sim(model_LLM, plan_sys_prompt, user_query) #conversation(history)        
    # bid_scores[person_name] = bid_score

    return bid_score

    # bid_scores = {}
    # for person_name, person_role in person_role_dict.items():
    #     with open(f"{person_name}_persona_prompt.txt", "r") as f:
    #         persona_prompt = f.read()
        
    #     conversation_hist_format = format_history_as_string(turns = 10)
        
    #     with open(f"bidding_sys_prompt.txt", "r") as f:
    #         bidding_system_prompt = f.read()
        
    #     bidding_system_prompt = bidding_system_prompt.replace("||", str(credits_left[person_name]))
        
    #     # bidding_system_prompt = bidding_system_prompt + "\n\n" + "Persona: " + persona_prompt + "\n\n" + "Conversation History: \n" + conversation_hist_format
    #     plan_sys_prompt = bidding_system_prompt
    #     user_query = "Persona: " + persona_prompt + "\n\n" + "Conversation History: \n" + conversation_hist_format

    #     history = []
    #     history.append({"role": "user", "content": bidding_system_prompt})
    #     bid_score = agent_sim(model_LLM, plan_sys_prompt, user_query) #conversation(history)        
    #     bid_scores[person_name] = bid_score

    # return bid_scores
