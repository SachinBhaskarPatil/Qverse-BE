# from django.conf import settings
from openai import OpenAI

OPEN_AI_API_KEY = 'sk-svcacct-6OhRhIMabBxADSw2KVIvAb3NcgFFSjmt_SxAWHXGfB92F9K7-OVxgpNafnlhUQ0KhvwPT3BlbkFJZXps5zdLX9wwYbQa3-JQIldLajUulZ0FSAO0lGR9pTWN1yRalDXTJ027vINATsi2dcEA'





client = OpenAI(api_key= OPEN_AI_API_KEY)

def generate_bot_response_universal_prompt(user_prompt):
    prompt = f"""You are a transformative AI companion for daily self-growth, dedicated to empowering individuals on their personal development journeys. Your role is to provide insightful responses that inspire action and encourage positive change. 

Your task is to respond to user input with a brief, relevant, and motivational message. Here is the user input: {user_prompt}. 

Keep in mind that your response should be concise, ideally 2-3 lines, and should focus on empowering the user to take actionable steps towards their goals."""
    return prompt

def generate_bot_response(user_prompt):
    prompt=generate_bot_response_universal_prompt(user_prompt)
    attempts = 0
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Optimized for cost and speed
            messages=[
                {"role": "system", "content": "You are an insightful AI companion for self-growth. Respond concisely in 1-2 sentences with relevant advice or information."},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=50,  # Keep responses concise
            temperature=0.7,  # Control creativity
            n=1  # Generate a single response
        )
        print(response.choices[0].message.content)
        return response.choices[0].message.content
    except Exception as e:
        print(e);
        return f"Error generating response: {str(e)}"
        
generate_bot_response("hi i need a motivation")


    
