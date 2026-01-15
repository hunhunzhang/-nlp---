import json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

# 设置中文字体显示
import matplotlib
matplotlib.rcParams['font.family'] = ['sans-serif']
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

def load_data(file_path):
    """加载JSON数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"错误：文件 {file_path} 不是有效的JSON格式")
        return None

def process_completion_tokens(data, response_type_filter=None):
    """提取并处理completion_tokens数据
    
    Args:
        data: JSON数据
        response_type_filter: 过滤特定的response_type，如'thinking', 'summary', 'answer'
                             如果为None则排除'answer'类型（保持原有行为）
    """
    if not data:
        print("错误：数据为空")
        return []
    
    # 提取所有正确回答问题中的completion_tokens
    completion_tokens_list = []
    
    # 检查是否有difficulty_results结构
    if 'difficulty_results' in data:
        # 遍历所有难度级别
        for difficulty_key, difficulty_data in data['difficulty_results'].items():
            if 'problem_details' in difficulty_data:
                for problem in difficulty_data['problem_details']:
                    # 只统计回答正确的问题
                    if problem.get('is_correct', False) and 'iteration_details' in problem:
                        for iteration in problem['iteration_details']:
                            if 'completion_tokens' in iteration:
                                # 根据response_type_filter进行过滤
                                if response_type_filter is None:
                                    # 原有行为：排除answer类型
                                    if iteration.get('response_type') != 'answer':
                                        try:
                                            tokens = int(iteration['completion_tokens'])
                                            completion_tokens_list.append(tokens)
                                        except (ValueError, TypeError):
                                            print(f"警告：无效的completion_tokens值 {iteration.get('completion_tokens')}，已跳过")
                                else:
                                    # 只统计指定的response_type
                                    if iteration.get('response_type') == response_type_filter:
                                        try:
                                            tokens = int(iteration['completion_tokens'])
                                            completion_tokens_list.append(tokens)
                                        except (ValueError, TypeError):
                                            print(f"警告：无效的completion_tokens值 {iteration.get('completion_tokens')}，已跳过")
    # 兼容旧格式：直接在根级别有problem_details
    elif 'problem_details' in data:
        for problem in data['problem_details']:
            # 只统计回答正确的问题
            if problem.get('is_correct', False) and 'iteration_details' in problem:
                for iteration in problem['iteration_details']:
                    if 'completion_tokens' in iteration:
                        # 根据response_type_filter进行过滤
                        if response_type_filter is None:
                            # 原有行为：排除answer类型
                            if iteration.get('response_type') != 'answer':
                                try:
                                    tokens = int(iteration['completion_tokens'])
                                    completion_tokens_list.append(tokens)
                                except (ValueError, TypeError):
                                    print(f"警告：无效的completion_tokens值 {iteration.get('completion_tokens')}，已跳过")
                        else:
                            # 只统计指定的response_type
                            if iteration.get('response_type') == response_type_filter:
                                try:
                                    tokens = int(iteration['completion_tokens'])
                                    completion_tokens_list.append(tokens)
                                except (ValueError, TypeError):
                                    print(f"警告：无效的completion_tokens值 {iteration.get('completion_tokens')}，已跳过")
    else:
        print("错误：数据格式不正确，找不到problem_details")
        return []
    
    return completion_tokens_list

def create_bins(completion_tokens_list, bin_width=50):
    """创建区间跨度为50的 bins"""
    if not completion_tokens_list:
        return []
    
    # 确定数据范围，确保覆盖所有数据点
    min_tokens = min(completion_tokens_list)
    max_tokens = max(completion_tokens_list)
    
    # 计算合适的区间边界
    start_bin = (min_tokens // bin_width) * bin_width
    end_bin = ((max_tokens // bin_width) + 1) * bin_width
    
    # 创建区间
    bins = list(range(start_bin, end_bin + bin_width, bin_width))
    
    return bins

def count_frequency(completion_tokens_list, bins):
    """统计每个区间的iteration数量"""
    frequency = defaultdict(int)
    
    for tokens in completion_tokens_list:
        # 找到对应的区间
        for i in range(len(bins) - 1):
            if bins[i] <= tokens < bins[i + 1]:
                frequency[(bins[i], bins[i + 1])] += 1
                break
        else:
            # 处理落在最后一个区间的数据点（包含最大值）
            if len(bins) >= 2 and tokens == bins[-1]:
                frequency[(bins[-2], bins[-1])] += 1
    
    return frequency

def plot_histogram(frequency, bin_width=50, completion_tokens_list=None, response_type="All (Excluding Answer)"):
    """绘制completion_tokens频率直方图"""
    if not frequency:
        print("没有数据可绘制直方图")
        return
    
    # 排序区间
    sorted_bins = sorted(frequency.keys())
    counts = [frequency[bin_range] for bin_range in sorted_bins]
    
    # 创建区间标签
    bin_labels = [f"{start}-{end}" for start, end in sorted_bins]
    
    # 根据response_type选择颜色
    color_map = {
        "All (Excluding Answer)": 'lightcoral',
        "thinking": 'lightblue',
        "summary": 'lightgreen'
    }
    color = color_map.get(response_type, 'lightcoral')
    
    # 设置图形样式
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 绘制直方图
    bars = ax.bar(bin_labels, counts, color=color, edgecolor='black', alpha=0.7)
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        if height > 0:  # 只在有数据的柱子上显示标签
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height}', ha='center', va='bottom')
    
    # 添加统计线（如果提供了原始数据）
    if completion_tokens_list is not None:
        mean_val = np.mean(completion_tokens_list)
        median_val = np.median(completion_tokens_list)
        max_val = max(completion_tokens_list)
        
        # 计算统计值在x轴上的位置
        def find_x_position(value, sorted_bins):
            """找到数值在x轴上的位置"""
            for i, (start, end) in enumerate(sorted_bins):
                if start <= value < end:
                    # 在区间内的相对位置
                    relative_pos = (value - start) / (end - start)
                    return i + relative_pos
            # 如果值等于最大值，放在最后一个区间
            if value == sorted_bins[-1][1]:
                return len(sorted_bins) - 1 + 1.0
            return len(sorted_bins) - 1
        
        mean_x = find_x_position(mean_val, sorted_bins)
        median_x = find_x_position(median_val, sorted_bins)
        max_x = find_x_position(max_val, sorted_bins)
        
        # 添加垂直线
        ax.axvline(x=mean_x, color='red', linestyle='--', linewidth=2, alpha=0.8, label=f'Mean: {mean_val:.1f}')
        ax.axvline(x=median_x, color='green', linestyle='--', linewidth=2, alpha=0.8, label=f'Median: {median_val:.1f}')
        ax.axvline(x=max_x, color='orange', linestyle='--', linewidth=2, alpha=0.8, label=f'Max: {max_val}')
        
        # 添加图例
        ax.legend(loc='upper right', fontsize=12)
        
        # 在图表顶部添加统计信息文本框
        stats_text = f'Statistics: Total={len(completion_tokens_list)}, Mean={mean_val:.1f}, Median={median_val:.1f}, Max={max_val}'
        ax.text(0.5, 0.98, stats_text, transform=ax.transAxes, fontsize=11, 
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
                verticalalignment='top', horizontalalignment='left')
    
    # 设置标题和轴标签
    title = f'Completion Tokens Histogram - {response_type} (Correct Answers, Bin Width = {bin_width})'
    ax.set_title(title, fontsize=16, pad=20)
    ax.set_xlabel('Completion Tokens Range', fontsize=14, labelpad=10)
    ax.set_ylabel('Number of Iterations', fontsize=14, labelpad=10)
    
    # 旋转x轴标签以防重叠
    plt.xticks(rotation=45, ha='right')
    
    # 添加网格线使读数更方便
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # 调整布局
    plt.tight_layout()
    
    # 显示图形
    plt.show()
    
    # 保存图形
    filename = f'completion_tokens_histogram_{response_type.lower().replace(" ", "_").replace("(", "").replace(")", "")}.png'
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"直方图已保存为 '{filename}'")

def analyze_and_plot(data, response_type_filter=None, response_type_name="All (Excluding Answer)"):
    """分析并绘制特定类型的completion_tokens直方图"""
    # 处理completion_tokens数据
    completion_tokens_list = process_completion_tokens(data, response_type_filter)
    if not completion_tokens_list:
        print(f"没有找到 {response_type_name} 类型的有效completion_tokens数据")
        return
    
    print(f"\n=== {response_type_name} 类型分析 ===")
    print(f"iterations数量: {len(completion_tokens_list)}")
    print(f"最小completion_tokens: {min(completion_tokens_list)}")
    print(f"最大completion_tokens: {max(completion_tokens_list)}")
    print(f"平均completion_tokens: {np.mean(completion_tokens_list):.2f}")
    print(f"中位数completion_tokens: {np.median(completion_tokens_list):.2f}")
    
    # 创建区间
    bin_width = 50
    bins = create_bins(completion_tokens_list, bin_width)
    
    # 统计频率
    frequency = count_frequency(completion_tokens_list, bins)
    
    # 打印频率统计（只显示前10个最频繁的区间）
    print(f"\n前10个最频繁的区间:")
    sorted_bins = sorted(frequency.keys())
    sorted_frequency = [(bin_range, frequency[bin_range]) for bin_range in sorted_bins]
    sorted_frequency.sort(key=lambda x: x[1], reverse=True)
    
    for i, (bin_range, count) in enumerate(sorted_frequency[:10]):
        percentage = (count / len(completion_tokens_list)) * 100
        print(f"区间 [{bin_range[0]}-{bin_range[1]}): {count} 个iterations ({percentage:.1f}%)")
    
    # 绘制直方图
    plot_histogram(frequency, bin_width, completion_tokens_list, response_type_name)

def main():
    # 数据文件路径（请根据实际情况修改）
    file_path = 'multi_metrics_5.json'
    
    # 加载数据
    data = load_data(file_path)
    if not data:
        return
    
    # 统计总问题数、正确答案数和总iteration数
    total_problems = 0
    correct_problems = 0
    total_iterations = 0
    correct_iterations = 0
    correct_non_answer_iterations = 0  # 正确答案中排除answer类型的iteration数
    thinking_iterations = 0
    summary_iterations = 0
    
    if 'difficulty_results' in data:
        for difficulty_key, difficulty_data in data['difficulty_results'].items():
            if 'problem_details' in difficulty_data:
                for problem in difficulty_data['problem_details']:
                    total_problems += 1
                    if 'iteration_details' in problem:
                        total_iterations += len(problem['iteration_details'])
                        if problem.get('is_correct', False):
                            correct_problems += 1
                            correct_iterations += len(problem['iteration_details'])
                            # 统计不同类型的iteration数
                            for iteration in problem['iteration_details']:
                                response_type = iteration.get('response_type', '')
                                if response_type != 'answer':
                                    correct_non_answer_iterations += 1
                                if response_type == 'thinking':
                                    thinking_iterations += 1
                                elif response_type == 'summary':
                                    summary_iterations += 1
    elif 'problem_details' in data:
        for problem in data['problem_details']:
            total_problems += 1
            if 'iteration_details' in problem:
                total_iterations += len(problem['iteration_details'])
                if problem.get('is_correct', False):
                    correct_problems += 1
                    correct_iterations += len(problem['iteration_details'])
                    # 统计不同类型的iteration数
                    for iteration in problem['iteration_details']:
                        response_type = iteration.get('response_type', '')
                        if response_type != 'answer':
                            correct_non_answer_iterations += 1
                        if response_type == 'thinking':
                            thinking_iterations += 1
                        elif response_type == 'summary':
                            summary_iterations += 1
    
    # 打印基本统计信息
    print("=== 总体统计信息 ===")
    print(f"总问题数: {total_problems}")
    print(f"正确答案数: {correct_problems}")
    print(f"错误答案数: {total_problems - correct_problems}")
    print(f"准确率: {(correct_problems/total_problems)*100:.1f}%")
    print()
    print(f"总iteration数: {total_iterations}")
    print(f"正确答案的iteration数: {correct_iterations}")
    print(f"正确答案中排除answer类型的iteration数: {correct_non_answer_iterations}")
    print(f"其中thinking类型: {thinking_iterations}")
    print(f"其中summary类型: {summary_iterations}")
    
    # 分析并绘制三种不同的图表
    print("\n" + "="*50)
    print("开始生成三种类型的直方图...")
    print("="*50)
    
    # 1. 总体图表（排除answer类型）
    analyze_and_plot(data, None, "All (Excluding Answer)")
    
    # 2. 只统计thinking类型
    analyze_and_plot(data, "thinking", "Thinking")
    
    # 3. 只统计summary类型
    analyze_and_plot(data, "summary", "Summary")
    
    print("\n" + "="*50)
    print("所有图表生成完成！")
    print("="*50)

if __name__ == "__main__":
    main()
