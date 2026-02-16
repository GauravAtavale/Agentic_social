"""
Final flow of Agentic Social Simulation:
"""
import random
import time
import re
import json
import utils

# Mock data for testing
person_role_dict = {
    "Gaurav_Atavale": "Gaurav",
    "Anagha_Palandye": "Anagha",
    "Kanishkha_S": "Kanishkha",
    "Nirbhay_R": "Nirbhay"
    }
role_person_dict = {v: k for k, v in person_role_dict.items()}

file_names_dict = {
    "Gaurav_Atavale": "agent_Gaurav.py",
    "Anagha_Palandye": "agent_Anagha.py",
    "Kanishkha_S": "agent_Kanishkha.py",
    "Nirbhay_R": "agent_Nirbhay.py"
    }

# Loop until NO ONE has credits left (everyone is 0)

# Run iterations of the simulation
# init_person = "Gaurav_Atavale"
with open("../conversational_history.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
init_person = role_person_dict[json.loads(lines[-1:][0])['role']] 

credits_left = {key: 100 for key in person_role_dict.keys()}

# print("Initial credits:", credits_left)

while any(credits_left[key] > 0 for key in credits_left):
    
    # FIX: Generate random bid ONLY if credits > 0, else bid is 0
    random_numbers = {}
    for key in person_role_dict:
        if credits_left[key] > 0:
            try:
                # generate_bid_score_each_user outputs percentage likelihood. It has to be scaled by credit left. 
                llm_bid_score = utils.generate_bid_score_each_user(key, credits_left, "claude-3-5-sonnet-20240620")                
                random_numbers[key] = int(0.01 * float(json.loads(llm_bid_score)["score"]) * credits_left[key])  # Scale bid by credits left
                print("claude model worked. Bid score:", random_numbers[key])
            except:
                # generate_bid_score_each_user outputs percentage likelihood. It has to be scaled by credit left.
                llm_bid_score = utils.generate_bid_score_each_user(key, credits_left, "llama-3.1-8b-instant")
                random_numbers[key] = int(0.01 * float(json.loads(llm_bid_score)["score"]) * credits_left[key])
                print("llama model worked. Bid score:", random_numbers[key])
        else:
            random_numbers[key] = 0  # Can't bid if no credits


    # Check if everyone is out of credits (bids are all 0) to avoid infinite loop or errors
    if all(val == 0 for val in random_numbers.values()):
        break

    # Select winner
    selected_person = max(random_numbers, key=random_numbers.get)
    winning_bid = random_numbers[selected_person]

    # Deduct credits
    if winning_bid > 0 and selected_person != init_person:
        # Only deduct if they actually bid something
        credits_left[selected_person] = max(0, credits_left[selected_person] - winning_bid)
        print(f"{selected_person} wins with bid {winning_bid} and will chat now.", "Credits left:", credits_left) 
        with open(file_names_dict[selected_person], "r") as f:
            exec(f.read())
        init_person = selected_person
    elif selected_person == init_person:
        # second higherst value from random_numbers dict
        second_highest_person = max((k for k in random_numbers if k != selected_person), key=random_numbers.get)
        selected_person = second_highest_person
        winning_bid = random_numbers[selected_person]
        credits_left[selected_person] = max(0, credits_left[selected_person] - winning_bid)
        print(f"{selected_person} wins with bid {winning_bid} and will chat now.", "Credits left:", credits_left) 
        with open(file_names_dict[selected_person], "r") as f:
            exec(f.read())
        init_person = selected_person        
    else:
        print("No valid bids this round.")
        continue
        
    # time.sleep(3)

print("Game Over. Final Credits:", credits_left)