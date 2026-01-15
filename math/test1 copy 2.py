# -*- coding: utf-8 -*-
import requests
import json

api_key = "sk-EEQLw6Rp2J64TGqc056fF8F3D3A748A8B28dC6C6DdDc33A2"
base_url = "https://api.bltcy.ai/v1/chat/completions"
max_steps = 10

#加载系统提示词
# with open("s_prompt.txt", "r", encoding="utf-8") as file:
#     system_prompt = file.read().strip()
with open("systemprompt.txt", "r", encoding="utf-8") as file:
    system_prompt = file.read().strip()

# 加载数据集
with open("./data/difficulty_1.json", "r", encoding="utf-8") as file:
    amc_problems = json.load(file)

#调用api
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
    response = requests.post(Base_url, json=payload, headers=headers, timeout=100)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"].strip(), result["usage"]["completion_tokens"]
# 初始化统计指标
total_tokens = 0
total_cost = 0  # 假设每1000 tokens花费0.002美元
correct_count = 0

# 循环处理每个问题
for problem in amc_problems[:10]: 
    user_prompt = problem["problem"]
    correct_answer = problem["answer"]
    current_prompt = user_prompt
    final_answer = None
    print(f"问题: {user_prompt}")
    tokennum=0
    num_steps = 0  
    while True:
        try:
            # 调用模型
            num_steps += 1
            response_content, tokens_used = _request_llm_for_trans(api_key, base_url, system_prompt, current_prompt)
            print(f"\n\n第{num_steps}步，模型输出: {response_content}\ntokens_used: {tokens_used}\n")
            
            # 更新统计指标
            total_tokens += tokens_used
            tokennum += tokens_used
            total_cost += tokens_used / 1000 * 0.002
            
            # 检查是否是最终答案
            if "<answer>" in response_content:
                final_answer = response_content.strip()
                break
            elif "<summary>" in response_content:
                current_prompt = response_content.strip()+user_prompt
            elif "<think>" in response_content:
                current_prompt = response_content.strip()+user_prompt
            elif num_steps > max_steps:
                print("超出最大步骤限制，终止循环。")
                break
            else:
                print("未识别的输出格式，终止循环。")
                break
            
        except Exception as e:
            print(f"处理问题时出错: {e}")
            break
        
    # 对比最终答案与正确答案
    if final_answer and str(correct_answer) in final_answer:
        correct_count += 1
    print(f"正确答案: {correct_answer}")
    print(f"最终模型答案: {final_answer}")
    print(f"长度: {tokennum} tokens\n\n")

# 计算最终统计结果
accuracy = correct_count / 100 * 100  # 处理了100个问题
print(f"总输出长度: {total_tokens} tokens")
print(f"总花费: ${total_cost:.4f}")
print(f"准确度: {accuracy:.2f}%")
