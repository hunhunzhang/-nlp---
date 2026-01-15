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

def process_iteration_steps(data):
    """提取并处理迭代步数数据"""
    if not data:
        print("错误：数据为空")
        return []
    
    # 提取所有问题的迭代步数
    iteration_steps = []
    
    # 检查是否有difficulty_results结构
    if 'difficulty_results' in data:
        # 遍历所有难度级别
        for difficulty_key, difficulty_data in data['difficulty_results'].items():
            if 'problem_details' in difficulty_data:
                for problem in difficulty_data['problem_details']:
                    # 只统计回答正确的问题
                    if 'iterations' in problem and problem.get('is_correct', False):
                    # if 'iterations' in problem:
                        try:
                            # 确保迭代步数是整数
                            steps = int(problem['iterations'])
                            iteration_steps.append(steps)
                        except (ValueError, TypeError):
                            print(f"警告：无效的迭代步数值 {problem.get('iterations')}，已跳过")
    # 兼容旧格式：直接在根级别有problem_details
    elif 'problem_details' in data:
        for problem in data['problem_details']:
            # 只统计回答正确的问题
            if 'iterations' in problem and problem.get('is_correct', False):
                try:
                    # 确保迭代步数是整数
                    steps = int(problem['iterations'])
                    iteration_steps.append(steps)
                except (ValueError, TypeError):
                    print(f"警告：无效的迭代步数值 {problem.get('iterations')}，已跳过")
    else:
        print("错误：数据格式不正确，找不到problem_details")
        return []
    
    return iteration_steps

def create_bins(iteration_steps, bin_width=5):
    """创建区间跨度为5的 bins"""
    if not iteration_steps:
        return []
    
    # 确定数据范围，确保覆盖所有数据点
    min_step = min(iteration_steps)
    max_step = max(iteration_steps)
    
    # 计算合适的区间边界
    start_bin = (min_step // bin_width) * bin_width
    end_bin = ((max_step // bin_width) + 1) * bin_width
    
    # 创建区间
    bins = list(range(start_bin, end_bin + bin_width, bin_width))
    
    return bins

def count_frequency(iteration_steps, bins):
    """统计每个区间的问题数量"""
    frequency = defaultdict(int)
    
    for step in iteration_steps:
        # 找到对应的区间
        for i in range(len(bins) - 1):
            if bins[i] <= step < bins[i + 1]:
                frequency[(bins[i], bins[i + 1])] += 1
                break
        else:
            # 处理落在最后一个区间的数据点（包含最大值）
            if len(bins) >= 2 and step == bins[-1]:
                frequency[(bins[-2], bins[-1])] += 1
    
    return frequency

def plot_histogram(frequency, bin_width=5, iteration_steps=None):
    """绘制频率直方图"""
    if not frequency:
        print("没有数据可绘制直方图")
        return
    
    # 排序区间
    sorted_bins = sorted(frequency.keys())
    counts = [frequency[bin_range] for bin_range in sorted_bins]
    
    # 创建区间标签
    bin_labels = [f"{start}-{end}" for start, end in sorted_bins]
    
    # 设置图形样式
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 绘制直方图
    bars = ax.bar(bin_labels, counts, color='skyblue', edgecolor='black', alpha=0.7)
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height}', ha='center', va='bottom')
    
    # 添加统计线（如果提供了原始数据）
    if iteration_steps is not None:
        mean_val = np.mean(iteration_steps)
        median_val = np.median(iteration_steps)
        max_val = max(iteration_steps)
        
        # 获取y轴的最大值
        y_max = max(counts) * 1.1
        
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
        stats_text = f'Statistics: Total={len(iteration_steps)}, Mean={mean_val:.1f}, Median={median_val:.1f}, Max={max_val}'
        ax.text(0.5, 0.98, stats_text, transform=ax.transAxes, fontsize=11, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                verticalalignment='top', horizontalalignment='left')
    
    # 设置标题和轴标签 - 使用英文以避免字体问题
    ax.set_title(f'Iteration Steps Frequency Histogram (Correct Answers Only, Bin Width = {bin_width})', fontsize=16, pad=20)
    ax.set_xlabel('Iteration Steps Range', fontsize=14, labelpad=10)
    ax.set_ylabel('Number of Problems', fontsize=14, labelpad=10)
    
    # 旋转x轴标签以防重叠
    plt.xticks(rotation=45, ha='right')
    
    # 添加网格线使读数更方便
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # 调整布局
    plt.tight_layout()
    
    # 显示图形
    plt.show()
    
    # 保存图形
    fig.savefig('iteration_steps_histogram.png', dpi=300, bbox_inches='tight')
    print("直方图已保存为 'iteration_steps_histogram.png'")

def main():
    # 数据文件路径（请根据实际情况修改）
    file_path = 'multi_metrics_1.json'
    
    # 加载数据
    data = load_data(file_path)
    if not data:
        return
    
    # 统计总问题数和正确答案数
    total_problems = 0
    correct_problems = 0
    
    if 'difficulty_results' in data:
        for difficulty_key, difficulty_data in data['difficulty_results'].items():
            if 'problem_details' in difficulty_data:
                for problem in difficulty_data['problem_details']:
                    total_problems += 1
                    if problem.get('is_correct', False):
                        correct_problems += 1
    elif 'problem_details' in data:
        for problem in data['problem_details']:
            total_problems += 1
            if problem.get('is_correct', False):
                correct_problems += 1
    
    # 处理迭代步数（只包含正确答案）
    iteration_steps = process_iteration_steps(data)
    if not iteration_steps:
        print("没有找到有效的迭代步数数据")
        return
    
    # 打印基本统计信息
    print(f"总问题数: {total_problems}")
    print(f"正确答案数: {correct_problems}")
    print(f"错误答案数: {total_problems - correct_problems}")
    print(f"准确率: {(correct_problems/total_problems)*100:.1f}%")
    print()
    print(f"以下统计仅基于正确答案的 {len(iteration_steps)} 个问题:")
    print(f"最小迭代步数: {min(iteration_steps)}")
    print(f"最大迭代步数: {max(iteration_steps)}")
    print(f"平均迭代步数: {np.mean(iteration_steps):.2f}")
    print(f"中位数迭代步数: {np.median(iteration_steps):.2f}")
    
    # 计算迭代步数在30及以下的问题比例
    steps_30_or_less = [step for step in iteration_steps if step <= 30]
    percentage_30_or_less = (len(steps_30_or_less) / len(iteration_steps)) * 100
    print(f"迭代步数在30及以下的问题: {len(steps_30_or_less)} 个 ({percentage_30_or_less:.1f}%)")
    print()
    
    # 创建区间
    bin_width = 5
    bins = create_bins(iteration_steps, bin_width)
    print(f"创建了 {len(bins)-1} 个区间，区间跨度为 {bin_width}")
    
    # 统计频率
    frequency = count_frequency(iteration_steps, bins)
    
    # 打印频率统计
    print("\n各区间频率统计:")
    sorted_bins = sorted(frequency.keys())
    for bin_range in sorted_bins:
        count = frequency[bin_range]
        percentage = (count / len(iteration_steps)) * 100
        print(f"区间 [{bin_range[0]}-{bin_range[1]}): {count} 个问题 ({percentage:.1f}%)")
    
    # 绘制直方图
    plot_histogram(frequency, bin_width, iteration_steps)

if __name__ == "__main__":
    main()
