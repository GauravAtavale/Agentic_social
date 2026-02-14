from groq import Groq
# import CodeC_helpers
import re
import json
import utils

plan_model = "meta-llama/llama-4-scout-17b-16e-instruct"
action_model = "llama-3.1-8b-instant"
fallback_model = "meta-llama/llama-4-scout-17b-16e-instruct"

init_model = "claude-sonnet-4-5-20250929"#"llama-3.1-8b-instant" #"meta-llama/llama-4-scout-17b-16e-instruct"    

# ================================== Get System Prompt ==================================

person_name = "Gaurav_Atavale"
person_role_dict = {
    "Gaurav_Atavale": "Gaurav",
    "Anagha_Palandye": "Anagha",
    "Kanishkha_S": "Kanishkha",
    "Nirbhay_R": "Nirbhay"
    }
role = person_role_dict[person_name]
# print(role)

with open("sys_prompt.txt", "r") as f:
    action_prompt = f.read()
# print(action_prompt)

with open(f"{person_name}_persona_prompt.txt", "r") as f:
    persona_prompt = f.read()
# print(persona_prompt)    

sys_prompt = persona_prompt + action_prompt
# print(sys_prompt)
# print()

# ================================== Get conversation history ==================================
conversation_hist_format = utils.format_history_as_string(turns = 10)

# print(conversation_hist_format) 
# print()

# role = "Gaurav"  # or "agent2" depending on which agent is speaking
agent_resp = utils.agent_sim(init_model, sys_prompt, conversation_hist_format)

# Clean response 
agent_resp = re.sub(r"^[^:\n]+\s*:\s*", "", agent_resp, count=1)

# print(agent_resp)

# Create the JSON object
log_entry = json.dumps({"role": role, "content": agent_resp})

# Append to file
with open("../conversational_history.txt", "a", encoding="utf-8") as f:
    f.write(log_entry + "\n")