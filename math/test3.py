# -*- coding: utf-8 -*-
import json
import requests
import time
import os
import regex as re
from datetime import datetime
import random

api_key = "sk-EEQLw6Rp2J64TGqc056fF8F3D3A748A8B28dC6C6DdDc33A2"
base_url = "https://api.bltcy.ai/v1/chat/completions"

#加载系统提示词
eval_prompt="""Your assigned task is to check if two math answers are equivalent. You are a wordclass expert for this task.
Given a problem and two answers, determine if they are mathematically equivalent. Do not solve the problem.
Instead, analyze whether the two answers represent the same mathematical value or expression, even if written differently.
Guidelines for equivalence:
- Different forms of the same number (e.g., 0.5 = 1/2 = 50%)
- Algebraically equivalent expressions (e.g., (x+1)^2 = x^2 + 2x + 1)
- Geometrically equivalent expressions (e.g., r²π = πr²)
- Trigonometrically equivalent expressions (e.g., sin²θ + cos²θ = 1)
- Semantic equivalence (e.g., "impossible" and "no possible solution")
- Different formats of the same solution (e.g., (1,1,1,3) and a=1,b=1,c=1,p=3)
- Solutions with different or no units (e.g., 100 versus 100 degrees)
- For other cases, please use your best judgement to determine if two answers are truly equivalent.
Your output must follow the following format:
1) Explain your reasoning for why the answers are equivalent or not.
2) Then provide your final verdict in the format: [[YES]] or [[NO]]
-----
Examples:
Problem: What is the area of a circle with radius 2?
Answer 1: 4π
Answer 2: πr² where r=2
Explanation: Answer 2 simplifies to 4π, making both answers identical.
[[YES]]
Problem: Solve for x: x² + 2x + 1 = 0
Answer 1: x = -1
Answer 2: x = -1 ± 0
Explanation: While Answer 2 includes ± 0, this reduces to just -1, making them equivalent.
[[YES]]
Problem: Find all positive integers $a,b,c$ and prime $p$ satisfying that\n\\[ 2^a p^b=(p+2)^c+1.\\]
Answer 1: a=1, b=1, c=1, p=3
Answer 3:  (1, 1, 1, 3)
Explanation: Both answers represent exactly the same solution, just written in different formats. Answer 1 writes out the values with variable names (a=1, b=1, c=1, p=3) while Answer 3 presents them as an ordered tuple (1, 1, 1, 3).
[[YES]]
Problem: The sides of a $99$ -gon are initially colored so that consecutive sides are red, blue, red, blue,..., red, blue, yellow. We make a sequence of modifications in the coloring, changing the color of one side at a time to one of the three given colors (red, blue, yellow), under the constraint that no two adjacent sides may be the same color. By making a sequence of such modifications, is it possible to arrive at the coloring in which consecutive sides \nare red, blue, red, blue, red, blue,..., red, yellow, blue?
Answer 1: There is no such coloring.
Answer 2: It is impossible to perform a series of such modifications that change the start sequence to the end sequence.
Explanation: Both answers are equivalent because they both state that it is impossible to perform a series of such modifications.
[[YES]]
Problem: Find the slope of the line y = 2x + 1
Answer 1: 2
Answer 2: 3
Explanation: These are different numbers and cannot be equivalent.
[[NO]]
-----
"""

system_prompt = """Let's think step by step and output the final answer.
**REQUIRED OUTPUT FORMAT**:
   - The FINAL answer must be the LAST line of your response
   - Enclose ONLY the final answer in <answer> tags like this: <answer>expression</answer>
   - Never add any text/comments after the <answer> tag
   - Examples:
     - Integer: <answer>5</answer>
     - Fraction: <answer>\dfrac{1}{2}</answer>
     - Angle: <answer>180^\circ</answer>
     - Vector: <answer>(1, -2)</answer> 
**STRICT PROHIBITIONS**:
   - DO NOT include any text after <answer>
   - DO NOT use multiple <answer> tags
   - DO NOT omit the tags (e.g., "The answer is 5" is FORBIDDEN)
FAILURE EXAMPLE (REJECTED):
    "The result is approximately 3.14" 
    CORRECT EXAMPLE:
<answer>\pi</answer>"""

def request_llm(system_prompt, user_prompt):
    """请求LLM并返回响应内容、token使用量和时延"""
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    response = requests.post(base_url, json=payload, headers=headers, timeout=500)
    latency = time.time() - start_time
    
    response.raise_for_status()
    result = response.json()
    
    content = result["choices"][0]["message"]["content"].strip()
    usage = result["usage"]
    
    return content, usage, latency

def extract_final_answer(response_content):
    """从LLM响应中提取最终答案"""
    # 使用正则表达式提取<answer>标签中的内容
    match = re.search(r"<answer>(.*?)</answer>", response_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None

def compare_answers(final_answer, correct_answer):
    """比较LLM的答案和正确答案"""
    # 处理答案，去除空格和换行符
    final_answer = final_answer.replace(" ", "").replace("\n", "")
    correct_answer = correct_answer.replace(" ", "").replace("\n", "")
    
    # 直接比较字符串
    return final_answer == correct_answer

def evaluate_answers_ai(problem: str, answer1: str, answer2: str) -> bool:
    user_prompt = f"Problem: {problem}\nAnswer 1: {answer1}\nAnswer 2: {answer2}"
    response,_,_ = request_llm(eval_prompt, user_prompt)
    if "[[YES]]" in response:
        return True
    elif "[[NO]]" in response:
        return False

def process_difficulty_level(difficulty):
    """处理单个难度级别的问题集"""
    filename = f"./data/difficulty_{difficulty}.json"
    
    if not os.path.exists(filename):
        print(f"文件不存在: {filename}")
        return None
    
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
        problems = data["questions"]  
        problems = problems[20:30]
    
    # 初始化统计指标
    metrics = {
        "difficulty": difficulty,
        "total_problems": len(problems),
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_cost": 0.0,
        "total_latency": 0.0,
        "correct_count": 0,
        "processed_problems": 0,
        "problem_details": [],
        "flops": 0,  # 新增：记录每个问题的FLOPs
    }
    
    print(f"\n{'='*50}")
    print(f"开始处理难度 {difficulty} 的问题集 ({len(problems)}个问题)")
    
    for i, problem in enumerate(problems, 1):
        user_prompt = problem["problem"]
        correct_answer = str(problem["answer"])
        
        try:
            # 请求LLM
            response_content, usage, latency = request_llm(system_prompt, user_prompt)
            
            # 更新统计指标
            metrics["total_tokens"] += usage["total_tokens"]
            metrics["prompt_tokens"] += usage["prompt_tokens"]
            metrics["completion_tokens"] += usage["completion_tokens"]
            metrics["total_latency"] += latency
            metrics["processed_problems"] += 1
            metrics["flops"] += usage["total_tokens"] **2

            # 计算花费（DeepSeek定价：输入$2/1M tokens，输出$8/1M tokens）
            cost = (usage["prompt_tokens"] * 2 / 1e6) + (usage["completion_tokens"] * 8 / 1e6)
            metrics["total_cost"] += cost
            
            # 提取答案并验证
            final_answer = extract_final_answer(response_content)
            # is_correct = compare_answers(final_answer, correct_answer)
            is_correct = evaluate_answers_ai(user_prompt, final_answer, correct_answer)
            if is_correct:
                metrics["correct_count"] += 1
            
            # 保存问题详情
            problem_detail = {
                "problem": user_prompt,
                "model_answer": final_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "tokens": usage["total_tokens"],
                "latency": latency,
                "cost": cost,
                "flops": usage["total_tokens"] ** 2,
            }
            metrics["problem_details"].append(problem_detail)
            
            # 打印进度
            print(f"问题 {i}/{len(problems)}: ", end="")
            print(f"答案: {final_answer or '未找到'} | 正确答案: {correct_answer} | ", end="")
            print(f"用时: {latency:.2f}s | Tokens: {usage['total_tokens']} | ", end="")
            print(f"FLOPs: {usage['total_tokens'] ** 2} | ", end="")
            print(f"花费: ${cost:.6f} | {'✓' if is_correct else '✗'}")
            
        except Exception as e:
            print(f"问题 {i} 处理失败: {str(e)}")
            metrics["problem_details"].append({
                "problem": user_prompt,
                "error": str(e)
            })
    
    # 计算准确度和平均指标
    if metrics["processed_problems"] > 0:
        metrics["accuracy"] = metrics["correct_count"] / metrics["processed_problems"] * 100
        metrics["avg_latency"] = metrics["total_latency"] / metrics["processed_problems"]
        metrics["avg_tokens_per_problem"] = metrics["total_tokens"] / metrics["processed_problems"]
        metrics["avg_cost_per_problem"] = metrics["total_cost"] / metrics["processed_problems"]
    else:
        metrics["accuracy"] = 0
        metrics["avg_latency"] = 0
        metrics["avg_tokens_per_problem"] = 0
        metrics["avg_cost_per_problem"] = 0
    
    print(f"\n难度 {difficulty} 处理完成:")
    print(f"总问题数: {metrics['total_problems']} | 成功处理: {metrics['processed_problems']}")
    print(f"正确数: {metrics['correct_count']} | 准确度: {metrics['accuracy']:.2f}%")
    print(f"总Tokens: {metrics['total_tokens']} (Prompt: {metrics['prompt_tokens']}, Completion: {metrics['completion_tokens']})")
    print(f"总花费: ${metrics['total_cost']:.6f} | 平均每问题花费: ${metrics['avg_cost_per_problem']:.6f}")
    print(f"总时延: {metrics['total_latency']:.2f}秒 | 平均时延: {metrics['avg_latency']:.2f}秒/问题")
    print(f"FLOPs: {metrics['flops']}")
    
    return metrics

def main():
    """主函数：处理所有难度级别并保存结果"""
    # 初始化结果收集
    all_results = {
        "metadata": {
            "model": "deepseek-chat",
            "system_prompt": system_prompt,
            "evaluation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pricing": "Input: $2/1M tokens, Output: $8/1M tokens",
        },
        "difficulty_results": {},
        "summary": {}
    }
    
    # 处理5个难度级别
    for difficulty in range(1, 6):
        metrics = process_difficulty_level(difficulty)
        if metrics:
            all_results["difficulty_results"][f"difficulty_{difficulty}"] = metrics
    
    # 计算整体汇总指标
    total_problems = 0
    total_processed = 0
    total_correct = 0
    total_tokens = 0
    total_cost = 0.0
    total_latency = 0.0
    total_flops = 0
    
    for diff in all_results["difficulty_results"].values():
        total_problems += diff["total_problems"]
        total_processed += diff["processed_problems"]
        total_correct += diff["correct_count"]
        total_tokens += diff["total_tokens"]
        total_cost += diff["total_cost"]
        total_latency += diff["total_latency"]
        total_flops += diff["flops"]
    
    # 保存汇总信息
    all_results["summary"] = {
        "total_problems": total_problems,
        "processed_problems": total_processed,
        "correct_answers": total_correct,
        "overall_accuracy": (total_correct / total_processed * 100) if total_processed > 0 else 0,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "total_latency": total_latency,
        "avg_latency_per_problem": total_latency / total_processed if total_processed > 0 else 0,
        "avg_cost_per_problem": total_cost / total_processed if total_processed > 0 else 0,
        "total_flops": total_flops
    }
    
    # 创建汇总字符串
    summary_str = "\n===== 最终汇总结果 =====\n"
    summary_str += f"总问题数: {total_problems}\n"
    summary_str += f"成功处理: {total_processed}\n"
    summary_str += f"正确回答: {total_correct}\n"
    summary_str += f"整体准确度: {all_results['summary']['overall_accuracy']:.2f}%\n"
    summary_str += f"总Tokens消耗: {total_tokens}\n"
    summary_str += f"总花费: ${total_cost:.6f}\n"
    summary_str += f"总时延: {total_latency:.2f}秒\n"
    summary_str += f"平均每问题花费: ${all_results['summary']['avg_cost_per_problem']:.6f}\n"
    summary_str += f"平均每问题时延: {all_results['summary']['avg_latency_per_problem']:.2f}秒\n\n"
    summary_str += f"总FLOPs: {total_flops}\n\n"
    
    # 添加各难度级别的汇总
    summary_str += "各难度级别结果:\n"
    summary_str += "| 难度 | 问题数 | 处理数 | 正确数 | 准确度 | 总Tokens | 总花费 | 总时延 | Flops |\n"
    summary_str += "|------|--------|--------|--------|--------|----------|--------|--------|-------|\n"

    for diff in range(1, 6):
        key = f"difficulty_{diff}"
        if key in all_results["difficulty_results"]:
            d = all_results["difficulty_results"][key]
            summary_str += f"| {diff} | {d['total_problems']} | {d['processed_problems']} | {d['correct_count']} | {d['accuracy']:.2f}% | {d['total_tokens']} | ${d['total_cost']:.6f} | {d['total_latency']:.2f}s | {d['flops']} |\n"
    
    # 将汇总字符串添加到结果中
    all_results["summary_string"] = summary_str
    
    # 保存结果到文件
    result_dir = "./result"
    os.makedirs(result_dir, exist_ok=True)
    existing_files = [f for f in os.listdir(result_dir) if f.startswith("single_metrics_") and f.endswith(".json")]
    idx = len(existing_files) + 1
    results_file = os.path.join(result_dir, f"single_metrics_{idx}.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n所有难度处理完成! 结果已保存至 {results_file}")
    
    # 打印汇总信息
    print(summary_str)

if __name__ == "__main__":
    main()