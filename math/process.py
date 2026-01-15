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
        "max_tokens": 200,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    response = requests.post(base_url, json=payload, headers=headers, timeout=30)
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
初始思考
触发条件：没有之前的思考或总结（全新的开始）
操作：在<think>标签内阐述初始推理过程
token最大长度限制：{300}
总结生成
触发条件：存在之前的思考并且还需要进一步推理
操作：在<summary>标签内提供总结
要求：
捕捉所有关键的推理要点和当前状态
确保总结是自包含的，以便下一个智能体使用
token最大长度限制：{100}
继续推理
触发条件：前一个智能体提供了总结，但没有附带思考过程
操作：在<think>标签内继续推理过程
要求：
仅基于提供的总结进行推理
有意义地推进推理过程
除非为了清晰起见，否则不要重复之前的工作
token最大长度限制：{100}
最终答案
触发条件：推理过程已完成
操作：在<answer>标签内提供答案
要求：
仅包含最简洁的最终的数值或文本结果
只有在确信问题已完全解决时才使用
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

def solve_problem_with_agents(question: str, max_iterations: int = 50, 
                             thought_token_limit: int = 200, 
                             summary_token_limit: int = 50, 
                             answer_token_limit: int = 50) -> tuple:
    """使用多智能体方法解决问题"""
    sys_prompt = _generate_prompt(thought_token_limit, summary_token_limit, answer_token_limit)
    last_response = ""
    total_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
    total_latency = 0.0
    total_cost = 0.0
    
    for iteration in range(max_iterations):
        user_prompt = _get_user_prompt(question, last_response)
        try:
            response, usage, latency = _get_response(sys_prompt, user_prompt)
            
            # 累计使用量和成本
            total_usage["total_tokens"] += usage["total_tokens"]
            total_usage["prompt_tokens"] += usage["prompt_tokens"]
            total_usage["completion_tokens"] += usage["completion_tokens"]
            total_latency += latency
            
            # 计算花费（DeepSeek定价：输入$2/1M tokens，输出$8/1M tokens）
            cost = (usage["prompt_tokens"] * 2 / 1e6) + (usage["completion_tokens"] * 8 / 1e6)
            total_cost += cost
            
            print(f"第 {iteration + 1}步: {response}\ncompletion_tokens:{usage['completion_tokens']}\n")
            
            if "<answer>" in response:
                final_answer = response.split("<answer>")[1].split("</answer>")[0].strip()
                print(f"Final Answer: {final_answer}")
                return final_answer, total_usage, total_latency, total_cost
            else:
                last_response = response
                
        except (RequestException, Timeout, ConnectionError) as e:
            logging.error(f"Error during request: {e}")
            time.sleep(2)  # Retry after a short delay
    
    # 如果达到最大迭代次数仍未找到答案
    return None, total_usage, total_latency, total_cost

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
    return final_answer in correct_answer

def process_difficulty_level(difficulty):
    """处理单个难度级别的问题集"""
    filename = f"./data/difficulty_{difficulty}.json"
    
    if not os.path.exists(filename):
        print(f"文件不存在: {filename}")
        return None
    
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
        problems = data["questions"]  
        problems = problems[:10]  
    
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
        "problem_details": []
    }
    
    print(f"\n{'='*50}")
    print(f"开始处理难度 {difficulty} 的问题集 ({len(problems)}个问题)")
    
    for i, problem in enumerate(problems, 1):
        user_prompt = problem["problem"]
        correct_answer = str(problem["answer"])
        
        try:
            # 使用多智能体方法解决问题
            final_answer, usage, latency, cost = solve_problem_with_agents(user_prompt)
            
            # 更新统计指标
            metrics["total_tokens"] += usage["total_tokens"]
            metrics["prompt_tokens"] += usage["prompt_tokens"]
            metrics["completion_tokens"] += usage["completion_tokens"]
            metrics["total_latency"] += latency
            metrics["total_cost"] += cost
            metrics["processed_problems"] += 1
            
            # 验证答案
            is_correct = compare_answers(final_answer, correct_answer)

            if is_correct:
                metrics["correct_count"] += 1
            
            # 保存问题详情
            problem_detail = {
                "problem": user_prompt,
                "model_answer": final_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "tokens": usage["total_tokens"],
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "latency": latency,
                "cost": cost
            }
            metrics["problem_details"].append(problem_detail)
            
            # 打印进度
            print(f"问题 {i}/{len(problems)}: ", end="")
            print(f"答案: {final_answer or '未找到'} | 正确答案: {correct_answer} | ", end="")
            print(f"用时: {latency:.2f}s | totalTokens: {usage['total_tokens']} | promptTokens: {usage['prompt_tokens']} | completionTokens: {usage['completion_tokens']}", end="")
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
    for difficulty in range(1, 2):
        metrics = process_difficulty_level(difficulty)
        if metrics:
            all_results["difficulty_results"][f"difficulty_{difficulty}"] = metrics
    
    # 计算整体汇总指标
    total_problems = 0
    total_processed = 0
    total_correct = 0
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0
    total_latency = 0.0
    
    for diff in all_results["difficulty_results"].values():
        total_problems += diff["total_problems"]
        total_processed += diff["processed_problems"]
        total_correct += diff["correct_count"]
        total_tokens += diff["total_tokens"]
        total_prompt_tokens += diff["prompt_tokens"]
        total_completion_tokens += diff["completion_tokens"]
        total_cost += diff["total_cost"]
        total_latency += diff["total_latency"]
    
    # 保存汇总信息
    all_results["summary"] = {
        "total_problems": total_problems,
        "processed_problems": total_processed,
        "correct_answers": total_correct,
        "overall_accuracy": (total_correct / total_processed * 100) if total_processed > 0 else 0,
        "total_tokens": total_tokens,
        "total_prompt_tokens":total_prompt_tokens,
        "total_completion_tokens":total_completion_tokens,
        "total_cost": total_cost,
        "total_latency": total_latency,
        "avg_latency_per_problem": total_latency / total_processed if total_processed > 0 else 0,
        "avg_cost_per_problem": total_cost / total_processed if total_processed > 0 else 0
    }
    
    # 创建汇总字符串
    summary_str = "\n===== 最终汇总结果 (多智能体方法) =====\n"
    summary_str += f"总问题数: {total_problems}\n"
    summary_str += f"成功处理: {total_processed}\n"
    summary_str += f"正确回答: {total_correct}\n"
    summary_str += f"整体准确度: {all_results['summary']['overall_accuracy']:.2f}%\n"
    summary_str += f"总Tokens消耗: {total_tokens}\n"
    summary_str += f"总Prompt Tokens消耗: {total_prompt_tokens},\n"
    summary_str += f"总Completion Tokens消耗: {total_completion_tokens},\n"
    summary_str += f"总花费: ${total_cost:.6f}\n"
    summary_str += f"总时延: {total_latency:.2f}秒\n"
    summary_str += f"平均每问题花费: ${all_results['summary']['avg_cost_per_problem']:.6f}\n"
    summary_str += f"平均每问题时延: {all_results['summary']['avg_latency_per_problem']:.2f}秒\n\n"
    
    # 添加各难度级别的汇总
    summary_str += "各难度级别结果:\n"
    summary_str += "| 难度 | 问题数 | 处理数 | 正确数 | 准确度 | 总Tokens | 总花费 | 总时延 |\n"
    summary_str += "|------|--------|--------|--------|--------|----------|--------|--------|\n"
    
    for diff in range(1, 2):
        key = f"difficulty_{diff}"
        if key in all_results["difficulty_results"]:
            d = all_results["difficulty_results"][key]
            summary_str += f"| {diff} | {d['total_problems']} | {d['processed_problems']} | {d['correct_count']} | {d['accuracy']:.2f}% | {d['total_tokens']} | ${d['total_cost']:.6f} | {d['total_latency']:.2f}s |\n"
    
    # 将汇总字符串添加到结果中
    all_results["summary_string"] = summary_str
    
    # 保存结果到文件
    results_file = "multi_agent_difficulty_metrics.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n所有难度处理完成! 结果已保存至 {results_file}")
    
    # 打印汇总信息
    print(summary_str)

if __name__ == "__main__":
    main()