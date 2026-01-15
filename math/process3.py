import json
import time
import logging
from typing import Dict, List, Any, Optional
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import regex as re
from datetime import datetime
import os

# API配置
api_key = "sk-EEQLw6Rp2J64TGqc056fF8F3D3A748A8B28dC6C6DdDc33A2"
base_url = "https://api.bltcy.ai/v1/chat/completions"

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


def _get_response(sys_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role":"system",
                "content":sys_prompt
            },
            {
                "role": "user", 
                "content":user_prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1500,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    response = requests.post(base_url, json=payload, headers=headers, timeout=300)
    latency = time.time() - start_time
    response.raise_for_status()  

    result = response.json()
    
    content = result["choices"][0]["message"]["content"].strip()
    usage = result["usage"]
    
    return content, usage, latency

def _generate_prompt(thought_token_limit: int, summary_token_limit: int, answer_token_limit: int) -> str:
    """生成多智能体推理提示"""
        
    # 基础系统提示
    system_prompt = f"""你是一个用于解决数学问题的多智能体系统中的推理智能体。整个推理过程被分解为多个迭代步骤，由多个专业智能体共同完成。每次被调用时，你必须根据提供的上下文执行恰好一个操作。
操作（每次响应选择一个）：
1.初始思考
触发条件：没有之前的思考或总结（全新的开始）
操作：在<think>标签内阐述初始推理过程
最大长度：{623} tokens
2.总结生成
触发条件：存在之前的思考并且还需要进一步推理
操作：在<summary>标签内提供总结
要求：
捕捉所有关键的推理要点和当前状态
确保总结是自包含的，以便下一个智能体使用
最大长度：{142} tokens
3.继续推理
触发条件：前一个智能体提供了总结，但没有附带思考过程
操作：在<think>标签内继续推理过程
要求：
仅基于提供的总结进行推理
有意义地推进推理过程
除非为了清晰起见，否则不要重复之前的工作
最大长度：{623} tokens
4.最终答案
触发条件：推理过程已完成
操作：在<answer>标签内提供答案
要求：
仅包含最简洁的最终的数值或文本结果
只有在确信问题已完全解决时才使用
最大长度：{50} tokens
关键指导原则：
中文友好系统：以中文思维理解问题，并使用中文进行回答
单一操作规则：每个响应恰好包含一个操作，不得合并多个操作
总结的重要性：下一个智能体仅接收总结和原始问题，而不是完整的思考历史
完成阈值：只有在解决方案完整且经过验证时，才提供最终答案
推理的连贯性：每个步骤必须逻辑上基于之前的工作，并朝着解决方案推进
流程：
初始思考 → 总结 → 继续推理 → 总结 → ... → 最终答案
在提供最终答案后，流程终止。"""
        
    return system_prompt 

def _get_user_prompt(question: str, last_response) -> str:
    if last_response=="":
        user_prompt=question
    else:
        user_prompt=f"{question}\n{last_response}"
    return user_prompt

def solve_problem_with_agents(question: str, max_iterations: int = 22, 
                             thought_token_limit: int = 200, 
                             summary_token_limit: int = 50, 
                             answer_token_limit: int = 50) -> tuple:
    """使用多智能体方法解决问题"""
    sys_prompt = _generate_prompt(thought_token_limit, summary_token_limit, answer_token_limit)
    last_response = ""
    total_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
    total_latency = 0.0
    total_cost = 0.0
    flops = 0
    iterations_count = 0
    
    # 详细记录每次迭代的信息
    iteration_details = []  # 新增：记录每次迭代的详细信息
    iteration_completion_tokens = []
    
    for iteration in range(max_iterations):
        iterations_count += 1
        user_prompt = _get_user_prompt(question, last_response)
        try:
            response, usage, latency = _get_response(sys_prompt, user_prompt)
            
            # 记录当前迭代的详细信息
            iteration_info = {
                "iteration": iteration + 1,
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
                "latency": latency,
                "response_type": "thinking" if "<think>" in response else ("summary" if "<summary>" in response else ("answer" if "<answer>" in response else "other"))
            }
            iteration_details.append(iteration_info)
            iteration_completion_tokens.append(usage["completion_tokens"])
            
            # 累计使用量和成本
            total_usage["total_tokens"] += usage["total_tokens"]
            total_usage["prompt_tokens"] += usage["prompt_tokens"]
            total_usage["completion_tokens"] += usage["completion_tokens"]
            total_latency += latency
            
            # 计算花费
            cost = (usage["prompt_tokens"] * 2 / 1e6) + (usage["completion_tokens"] * 8 / 1e6)
            total_cost += cost
            if(iteration == 0):
                flops += usage["total_tokens"]**2
            else:
                flops += (usage["total_tokens"]-370) **2
                
            print(f"Iteration {iteration + 1} (C:{usage['completion_tokens']}): {response}")
            
            if "<answer>" in response:
                final_answer = response.split("<answer>")[1].split("</answer>")[0].strip()
                print(f"Final Answer: {final_answer}")
                
                # 计算统计信息
                avg_completion_tokens_per_iteration = sum(iteration_completion_tokens) / len(iteration_completion_tokens) if iteration_completion_tokens else 0
                max_completion_tokens_per_iteration = max(iteration_completion_tokens) if iteration_completion_tokens else 0
                min_completion_tokens_per_iteration = min(iteration_completion_tokens) if iteration_completion_tokens else 0
                
                return (final_answer, total_usage, total_latency, total_cost, flops, iterations_count, 
                       avg_completion_tokens_per_iteration, max_completion_tokens_per_iteration, 
                       min_completion_tokens_per_iteration, iteration_details)
            else:
                last_response = response
                
        except (RequestException, Timeout, ConnectionError) as e:
            logging.error(f"Error during request: {e}")
            time.sleep(2)
    
    # 如果达到最大迭代次数仍未找到答案
    avg_completion_tokens_per_iteration = sum(iteration_completion_tokens) / len(iteration_completion_tokens) if iteration_completion_tokens else 0
    max_completion_tokens_per_iteration = max(iteration_completion_tokens) if iteration_completion_tokens else 0
    min_completion_tokens_per_iteration = min(iteration_completion_tokens) if iteration_completion_tokens else 0
    
    return (None, total_usage, total_latency, total_cost, flops, iterations_count, 
           avg_completion_tokens_per_iteration, max_completion_tokens_per_iteration,
           min_completion_tokens_per_iteration, iteration_details)

def extract_final_answer(response_content):
    """从LLM响应中提取最终答案"""
    if response_content is None:
        return None
    # 使用正则表达式提取<answer>标签中的内容
    match = re.search(r"<answer>(.*?)</answer>", response_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return response_content  # 如果没有标签，返回原内容

def compare_answers(final_answer, correct_answer):
    """比较LLM的答案和正确答案"""
    if final_answer is None or correct_answer is None:
        return False
    
    # 处理答案，去除空格和换行符
    final_answer = str(final_answer).replace(" ", "").replace("\n", "")
    correct_answer = str(correct_answer).replace(" ", "").replace("\n", "")
    
    # 直接比较字符串
    return final_answer == correct_answer

def evaluate_answers_ai(problem: str, answer1: str, answer2: str) -> bool:
    user_prompt = f"Problem: {problem}\nAnswer 1: {answer1}\nAnswer 2: {answer2}"
    response, _, _ = _get_response(eval_prompt, user_prompt)
    # 检查响应中是否包含[[YES]]或[[NO]]
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
        # problems = problems[:100]  # 只处理前10个问题

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
        "total_flops": 0,  # 修改：记录总FLOPs
        "total_iterations": 0,  # 新增：记录总迭代次数
        # 新增：迭代级别的统计
        "total_avg_completion_tokens_per_iteration": 0.0,
        "total_max_completion_tokens_per_iteration": 0,
        "overall_max_completion_tokens_per_iteration": 0,  # 所有问题中最大的单次迭代completion tokens
    }
    
    print(f"\n{'='*50}")
    print(f"开始处理难度 {difficulty} 的问题集 ({len(problems)}个问题)")
    
    for i, problem in enumerate(problems, 1):
        user_prompt = problem["problem"]
        correct_answer = str(problem["answer"])
        
        try:
            # 使用多智能体方法解决问题
            result = solve_problem_with_agents(user_prompt)
            final_answer, usage, latency, cost, flop, iterations, avg_completion_per_iter, max_completion_per_iter, min_completion_per_iter, iteration_details = result
            
            # 更新统计指标
            metrics["total_tokens"] += usage["total_tokens"]
            metrics["prompt_tokens"] += usage["prompt_tokens"]
            metrics["completion_tokens"] += usage["completion_tokens"]
            metrics["total_latency"] += latency
            metrics["total_cost"] += cost
            metrics["processed_problems"] += 1
            metrics["total_flops"] += flop
            metrics["total_iterations"] += iterations  # 新增：累计迭代次数
            
            # 新增：累计迭代级别统计
            metrics["total_avg_completion_tokens_per_iteration"] += avg_completion_per_iter
            metrics["total_max_completion_tokens_per_iteration"] += max_completion_per_iter
            metrics["overall_max_completion_tokens_per_iteration"] = max(
                metrics["overall_max_completion_tokens_per_iteration"], 
                max_completion_per_iter
            )
            
            # 验证答案
            is_correct = evaluate_answers_ai(user_prompt, final_answer, correct_answer)

            if is_correct:
                metrics["correct_count"] += 1
            
            # 保存问题详情（增强版）
            problem_detail = {
                "problem": user_prompt,
                "model_answer": final_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "total_tokens": usage["total_tokens"],
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "iterations": iterations,
                "avg_completion_tokens_per_iteration": avg_completion_per_iter,
                "max_completion_tokens_per_iteration": max_completion_per_iter,
                "min_completion_tokens_per_iteration": min_completion_per_iter,  # 新增
                "iteration_details": iteration_details,  # 新增：每次迭代的详细信息
                "flops": flop,
                "latency": latency,
                "cost": cost
            }
            metrics["problem_details"].append(problem_detail)
            
            # 打印进度（增强版）
            print(f"问题 {i}/{len(problems)}: ", end="")
            print(f"答案: {final_answer or '未找到'} | 正确答案: {correct_answer} | ", end="")
            print(f"用时: {latency:.2f}s | 迭代: {iterations} | ", end="")
            print(f"Tokens: {usage['total_tokens']} (P:{usage['prompt_tokens']}, C:{usage['completion_tokens']}) | ", end="")
            print(f"C/迭代: 平均{avg_completion_per_iter:.1f} 最大{max_completion_per_iter} 最小{min_completion_per_iter} | ", end="")  # 增强
            print(f"FLOPs: {flop} | 花费: ${cost:.6f} | {'✓' if is_correct else '✗'}")
            
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
        metrics["avg_total_tokens"] = metrics["total_tokens"] / metrics["processed_problems"]
        metrics["avg_prompt_tokens"] = metrics["prompt_tokens"] / metrics["processed_problems"]  # 新增
        metrics["avg_completion_tokens"] = metrics["completion_tokens"] / metrics["processed_problems"]  # 新增
        metrics["avg_iterations"] = metrics["total_iterations"] / metrics["processed_problems"]  # 新增
        metrics["avg_flops"] = metrics["total_flops"] / metrics["processed_problems"]  # 新增
        metrics["avg_cost_per_problem"] = metrics["total_cost"] / metrics["processed_problems"]
        
        # 新增：迭代级别的平均值
        metrics["avg_avg_completion_tokens_per_iteration"] = metrics["total_avg_completion_tokens_per_iteration"] / metrics["processed_problems"]
        metrics["avg_max_completion_tokens_per_iteration"] = metrics["total_max_completion_tokens_per_iteration"] / metrics["processed_problems"]
    else:
        metrics["accuracy"] = 0
        metrics["avg_latency"] = 0
        metrics["avg_total_tokens"] = 0
        metrics["avg_prompt_tokens"] = 0
        metrics["avg_completion_tokens"] = 0
        metrics["avg_iterations"] = 0
        metrics["avg_flops"] = 0
        metrics["avg_cost_per_problem"] = 0
        metrics["avg_avg_completion_tokens_per_iteration"] = 0
        metrics["avg_max_completion_tokens_per_iteration"] = 0
    
    print(f"\n难度 {difficulty} 处理完成:")
    print(f"总问题数: {metrics['total_problems']} | 成功处理: {metrics['processed_problems']}")
    print(f"正确数: {metrics['correct_count']} | 准确度: {metrics['accuracy']:.2f}%")
    print(f"总Tokens: {metrics['total_tokens']} (Prompt: {metrics['prompt_tokens']}, Completion: {metrics['completion_tokens']})")
    print(f"平均迭代次数: {metrics['avg_iterations']:.2f} | 总迭代次数: {metrics['total_iterations']}")
    print(f"平均每迭代Completion: {metrics['avg_avg_completion_tokens_per_iteration']:.1f} | 平均最大每迭代Completion: {metrics['avg_max_completion_tokens_per_iteration']:.1f}")  # 新增
    print(f"整体最大单次迭代Completion: {metrics['overall_max_completion_tokens_per_iteration']}")  # 新增
    print(f"总FLOPs: {metrics['total_flops']} | 平均FLOPs: {metrics['avg_flops']:.2f}")
    print(f"总花费: ${metrics['total_cost']:.6f} | 平均每问题花费: ${metrics['avg_cost_per_problem']:.6f}")
    print(f"总时延: {metrics['total_latency']:.2f}秒 | 平均时延: {metrics['avg_latency']:.2f}秒/问题")
    
    return metrics


def main():
    """主函数：处理所有难度级别并保存结果"""
    # 初始化结果收集
    all_results = {
        "metadata": {
            "model": "deepseek-chat",
            "method": "multi-agent reasoning",
            "evaluation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pricing": "Input: $2/1M tokens, Output: $8/1M tokens"
        },
        "difficulty_results": {},
        "summary": {}
    }
    
    # 处理5个难度级别
    for difficulty in range(5,6):
        metrics = process_difficulty_level(difficulty)
        if metrics:
            all_results["difficulty_results"][f"difficulty_{difficulty}"] = metrics
    
    # 计算整体汇总指标
    total_problems = 0
    total_processed = 0
    total_correct = 0
    total_tokens = 0
    total_prompt_tokens = 0  # 新增
    total_completion_tokens = 0  # 新增
    total_iterations = 0  # 新增
    total_flops = 0
    total_cost = 0.0
    total_latency = 0.0
    
    # 新增：迭代级别的汇总
    total_avg_completion_per_iteration = 0.0
    total_max_completion_per_iteration = 0.0
    global_max_completion_per_iteration = 0
    
    for diff in all_results["difficulty_results"].values():
        total_problems += diff["total_problems"]
        total_processed += diff["processed_problems"]
        total_correct += diff["correct_count"]
        total_tokens += diff["total_tokens"]
        total_prompt_tokens += diff["prompt_tokens"]  # 新增
        total_completion_tokens += diff["completion_tokens"]  # 新增
        total_iterations += diff["total_iterations"]  # 新增
        total_flops += diff["total_flops"]
        total_cost += diff["total_cost"]
        total_latency += diff["total_latency"]
        
        # 新增：迭代级别的累计
        total_avg_completion_per_iteration += diff["total_avg_completion_tokens_per_iteration"]
        total_max_completion_per_iteration += diff["total_max_completion_tokens_per_iteration"]
        global_max_completion_per_iteration = max(
            global_max_completion_per_iteration,
            diff["overall_max_completion_tokens_per_iteration"]
        )

    # 保存汇总信息
    all_results["summary"] = {
        "total_problems": total_problems,
        "processed_problems": total_processed,
        "correct_answers": total_correct,
        "overall_accuracy": (total_correct / total_processed * 100) if total_processed > 0 else 0,
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt_tokens,  # 新增
        "total_completion_tokens": total_completion_tokens,  # 新增
        "total_iterations": total_iterations,  # 新增
        "total_flops": total_flops,
        "total_cost": total_cost,
        "total_latency": total_latency,
        "avg_latency_per_problem": total_latency / total_processed if total_processed > 0 else 0,
        "avg_cost_per_problem": total_cost / total_processed if total_processed > 0 else 0,
        "avg_total_tokens_per_problem": total_tokens / total_processed if total_processed > 0 else 0,  # 新增
        "avg_prompt_tokens_per_problem": total_prompt_tokens / total_processed if total_processed > 0 else 0,  # 新增
        "avg_completion_tokens_per_problem": total_completion_tokens / total_processed if total_processed > 0 else 0,  # 新增
        "avg_iterations_per_problem": total_iterations / total_processed if total_processed > 0 else 0,  # 新增
        "avg_flops_per_problem": total_flops / total_processed if total_processed > 0 else 0,  # 新增
        
        # 新增：迭代级别的汇总统计
        "overall_avg_completion_tokens_per_iteration": total_avg_completion_per_iteration / total_processed if total_processed > 0 else 0,
        "overall_avg_max_completion_tokens_per_iteration": total_max_completion_per_iteration / total_processed if total_processed > 0 else 0,
        "global_max_completion_tokens_per_iteration": global_max_completion_per_iteration
    }
    
    # 创建汇总字符串
    summary_str = "\n===== 最终汇总结果 (多智能体方法) =====\n"
    summary_str += f"总问题数: {total_problems}\n"
    summary_str += f"成功处理: {total_processed}\n"
    summary_str += f"正确回答: {total_correct}\n"
    summary_str += f"整体准确度: {all_results['summary']['overall_accuracy']:.2f}%\n"
    summary_str += f"总Tokens消耗: {total_tokens} (Prompt: {total_prompt_tokens}, Completion: {total_completion_tokens})\n"
    summary_str += f"总迭代次数: {total_iterations}\n"
    summary_str += f"总FLOPs: {total_flops}\n"
    summary_str += f"总花费: ${total_cost:.6f}\n"
    summary_str += f"总时延: {total_latency:.2f}秒\n"
    summary_str += f"平均每问题花费: ${all_results['summary']['avg_cost_per_problem']:.6f}\n"
    summary_str += f"平均每问题时延: {all_results['summary']['avg_latency_per_problem']:.2f}秒\n"
    summary_str += f"平均每问题迭代次数: {all_results['summary']['avg_iterations_per_problem']:.2f}\n"
    summary_str += f"平均每问题Completion Tokens: {all_results['summary']['avg_completion_tokens_per_problem']:.2f}\n"
    summary_str += f"整体平均每迭代Completion Tokens: {all_results['summary']['overall_avg_completion_tokens_per_iteration']:.2f}\n"  # 新增
    summary_str += f"整体平均最大每迭代Completion Tokens: {all_results['summary']['overall_avg_max_completion_tokens_per_iteration']:.2f}\n"  # 新增
    summary_str += f"全局最大单次迭代Completion Tokens: {all_results['summary']['global_max_completion_tokens_per_iteration']}\n"  # 新增
    summary_str += f"平均每问题FLOPs: {all_results['summary']['avg_flops_per_problem']:.2f}\n\n"
    
    # 添加各难度级别的汇总
    summary_str += "各难度级别结果:\n"
    summary_str += "| 难度 | 问题数 | 正确数 | 准确度 | 总Tokens | P-Tokens | C-Tokens | 迭代次数 | 平均C/迭代 | 最大C/迭代 | FLOPs | 时延(s) |\n"
    summary_str += "|------|--------|--------|--------|----------|----------|----------|----------|-----------|-----------|-------|--------|\n"

    for diff in range(5, 6):
        key = f"difficulty_{diff}"
        if key in all_results["difficulty_results"]:
            d = all_results["difficulty_results"][key]
            summary_str += f"| {diff} | {d['total_problems']} | {d['correct_count']} | {d['accuracy']:.1f}% | {d['total_tokens']} | {d['prompt_tokens']} | {d['completion_tokens']} | {d['total_iterations']} | {d['avg_avg_completion_tokens_per_iteration']:.1f} | {d['overall_max_completion_tokens_per_iteration']} | {d['total_flops']} | {d['total_latency']:.1f} |\n"
    
    # 将汇总字符串添加到结果中
    all_results["summary_string"] = summary_str
    
    # 保存结果到文件
    result_dir = "./result"
    os.makedirs(result_dir, exist_ok=True)
    existing_files = [f for f in os.listdir(result_dir) if f.startswith("multi_metrics_") and f.endswith(".json")]
    idx = len(existing_files) + 1
    results_file = os.path.join(result_dir, f"multi_metrics_{idx}.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n所有难度处理完成! 结果已保存至 {results_file}")
    
    # 打印汇总信息
    print(summary_str)

if __name__ == "__main__":
    main()