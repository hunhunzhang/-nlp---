import json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

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
    if not data or 'problem_details' not in data:
        print("错误：数据格式不正确，缺少problem_details")
        return []
    
    # 提取所有问题的迭代步数
    iteration_steps = []
    for problem in data['problem_details']:
        if 'iterations' in problem:
            try:
                # 确保迭代步数是整数
                steps = int(problem['iterations'])
                iteration_steps.append(steps)
            except (ValueError, TypeError):
                print(f"警告：无效的迭代步数值 {problem.get('iterations')}，已跳过")
    
    return iteration_steps

def create_bins(iteration_steps, bin_width=5):
    """创建区间跨度为5的 bins"""
    if not iteration_steps:
        return [], []
    
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
            # 处理落在最后一个区间的数据
            if step >= bins[-1]:
                frequency[(bins[-2], bins[-1])] += 1
    
    return frequency

def plot_histogram(frequency, bin_width=5):
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
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 绘制直方图
    bars = ax.bar(bin_labels, counts, color='skyblue', edgecolor='black')
    
    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height}', ha='center', va='bottom')
    
    # 设置标题和轴标签
    ax.set_title(f'迭代步数频率直方图 (区间跨度 = {bin_width})', fontsize=16, pad=20)
    ax.set_xlabel('迭代步数区间', fontsize=14, labelpad=10)
    ax.set_ylabel('问题数量', fontsize=14, labelpad=10)
    
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
    
    # 处理迭代步数
    iteration_steps = process_iteration_steps(data)
    if not iteration_steps:
        print("没有找到有效的迭代步数数据")
        return
    
    # 创建区间
    bin_width = 5
    bins = create_bins(iteration_steps, bin_width)
    
    # 统计频率
    frequency = count_frequency(iteration_steps, bins)
    
    # 绘制直方图
    plot_histogram(frequency, bin_width)

if __name__ == "__main__":
    main()
