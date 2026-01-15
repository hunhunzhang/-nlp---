# -*- coding: utf-8 -*-
import requests
import json

api_key = "sk-EEQLw6Rp2J64TGqc056fF8F3D3A748A8B28dC6C6DdDc33A2"
base_url = "https://api.bltcy.ai/v1/chat/completions"
max_steps = 10

# Load the system prompt from a file
with open("systemprompt.txt", "r", encoding="utf-8") as file:
    system_prompt = file.read().strip()

# Load AMC problems from JSON file
with open("amc.json", "r", encoding="utf-8") as file:
    amc_problems = json.load(file)



def _request_llm_for_trans(API_KEY, Base_url, system_prompt, user_prompt):
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1024,  # 限制长度
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 发送请求
    response = requests.post(Base_url, json=payload, headers=headers, timeout=90)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"].strip(), result["usage"]["completion_tokens"]
# 初始化统计指标
total_tokens = 0
total_cost = 0  # 假设每1000 tokens花费0.002美元
correct_count = 0

user_prompt=current_prompt="$\\overline{BC}$ is parallel to the segment through $A$, and $AB = BC$. What is the number of degrees represented by $x$?\n\n[asy]\ndraw((0,0)--(10,0));\ndraw((0,3)--(10,3));\ndraw((2,3)--(8,0));\ndraw((2,3)--(4,0));\nlabel(\"$A$\",(2,3),N);\nlabel(\"$B$\",(4,0),S);\nlabel(\"$C$\",(8,0),S);\nlabel(\"$124^{\\circ}$\",(2,3),SW);\nlabel(\"$x^{\\circ}$\",(4.5,3),S);\n[/asy]"
num_steps=0
while True:
    try:
        # 调用模型
        num_steps += 1
        response_content, tokens_used = _request_llm_for_trans(api_key, base_url, system_prompt, current_prompt)
        print(f"\n\n第{num_steps}步，模型输出: {response_content.replace('\n', '')}\ntokens_used: {tokens_used}\n")
        # 检查是否是最终答案
        if "<answer>" in response_content:
            final_answer =response_content.strip()
            break
        elif "<summary>" in response_content:
            current_prompt = response_content.strip()+user_prompt
        elif "<think>" in response_content:
            current_prompt = response_content.strip()+user_prompt
        else:
            print("未识别的输出格式，终止循环。")
            break
            
    except Exception as e:
        print(f"处理问题时出错: {e}")
        break
    if num_steps >= max_steps:
        print("超出最大步骤限制，终止循环。")
        break











