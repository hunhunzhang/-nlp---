import json

def find_max_problem(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    max_iterations_problem = None
    max_total_tokens_problem = None

    max_iterations = -1
    max_total_tokens = -1

    # 遍历所有问题
    for problem in data["difficulty_results"]["difficulty_5"]["problem_details"]:
        if problem.get("is_correct"):
            # 检查最大 iterations
            if problem.get("iterations", 0) > max_iterations:
                max_iterations = problem["iterations"]
                max_iterations_problem = problem

            # 检查最大 total_tokens
            if problem.get("total_tokens", 0) > max_total_tokens:
                max_total_tokens = problem["total_tokens"]
                max_total_tokens_problem = problem

    return max_iterations_problem, max_total_tokens_problem


if __name__ == "__main__":
    file_path = "e:\\NLPpractice\\math\\multi_metrics_1.json"
    max_iterations_problem, max_total_tokens_problem = find_max_problem(file_path)

    print("拥有最大 iterations 的问题:")
    print(json.dumps(max_iterations_problem, indent=2, ensure_ascii=False))

    print("\n拥有最大 total_tokens 的问题:")
    print(json.dumps(max_total_tokens_problem, indent=2, ensure_ascii=False))