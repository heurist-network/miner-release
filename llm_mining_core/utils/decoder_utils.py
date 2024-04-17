import re

def decode_prompt_llama(encoded_prompt):
    """
    Decodes and processes the encoded prompt for LLaMA models.
    
    Args:
        encoded_prompt (str): The encoded prompt string.
        
    Returns:
        list of dicts: A list where each item is a dictionary representing a message with 'role' and 'content' keys.
    """
    system_start_marker = "[INST] <<SYS>>\n"
    system_end_marker = "\n<</SYS>>\n [/INST]\n"
    user_start = "[INST] "
    user_end = " [/INST]\n"
    assistant_end = "</s>"

    messages = []
    current_pos = 0

    # Check for system message
    if system_start_marker in encoded_prompt:
        start_index = encoded_prompt.find(system_start_marker) + len(system_start_marker)
        end_index = encoded_prompt.find(system_end_marker, start_index)
        if end_index != -1:
            system_content = encoded_prompt[start_index:end_index].strip()
            messages.append({"role": "system", "content": system_content})
            current_pos = end_index + len(system_end_marker)

    # Process the rest of the prompt
    while current_pos < len(encoded_prompt):
        if encoded_prompt[current_pos:].startswith(user_start):
            current_pos += len(user_start)
            user_end_pos = encoded_prompt.find(user_end, current_pos)
            if user_end_pos != -1:
                user_content = encoded_prompt[current_pos:user_end_pos].strip()
                messages.append({"role": "user", "content": user_content})
                current_pos = user_end_pos + len(user_end)
        
        assistant_end_pos = encoded_prompt.find(assistant_end, current_pos)
        if assistant_end_pos != -1:
            assistant_content = encoded_prompt[current_pos:assistant_end_pos].strip()
            messages.append({"role": "assistant", "content": assistant_content})
            current_pos = assistant_end_pos + len(assistant_end)
        else:
            break

    return messages

def decode_prompt_mistral(encoded_prompt):
    """
    Decodes and processes the encoded prompt for Mistral models.
    
    Args:
        encoded_prompt (str): The encoded prompt string.
        
    Returns:
        list of dicts: A list where each item is a dictionary representing a message with 'role' and 'content' keys.
    """
    inst_start = "[INST]"
    inst_end = "[/INST]"
    assistant_end = "</s>"
    
    messages = []
    segments = encoded_prompt.split(inst_start)
    
    for segment in segments[1:]:  # Skip the initial empty segment
        if inst_end in segment:
            end_index = segment.find(inst_end)
            user_prompt = segment[:end_index].strip()
            following_content = segment[end_index + len(inst_end):].strip()
            
            if assistant_end in following_content:
                assistant_message_end_index = following_content.find(assistant_end)
                assistant_message = following_content[:assistant_message_end_index].strip()
            else:
                assistant_message = following_content
            
            messages.append({"role": "user", "content": user_prompt})
            if assistant_message:
                messages.append({"role": "assistant", "content": assistant_message})
    
    return messages

def decode_prompt_chatml(encoded_prompt):
    # Refined regular expression to match the role, im_start marker, content, and im_end marker
    # This pattern assumes that the role and content are concatenated without any separator
    pattern = re.compile(r"<|im_start|>(system|assistant|user)(.*?)<|im_end|>\n", re.DOTALL)

    messages = []

    matches = pattern.finditer(encoded_prompt)
    for match in matches:
        role, content = match.groups()
        # Ensure that both role and content are not empty before adding to the list
        if role and content:
            messages.append({"role": role, "content": content})

    return messages