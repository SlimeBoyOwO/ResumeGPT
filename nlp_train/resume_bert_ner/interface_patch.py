
import os
import json
import glob
from interface import InferenceEngine

def batch_process_pdfs(input_dir="./data/test_pdfs", output_dir="./results"):
    """
    批量处理PDF文件，进行NER识别，并将结果保存为JSON文件

    Args:
        input_dir: 输入PDF文件目录
        output_dir: 输出JSON文件目录
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 获取所有PDF文件
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))

    if not pdf_files:
        print(f"警告: 在 {input_dir} 目录下未找到PDF文件")
        return

    print(f"找到 {len(pdf_files)} 个PDF文件待处理")

    # 初始化推理引擎
    engine = InferenceEngine()

    # 处理每个PDF文件
    for pdf_path in pdf_files:
        print(f"\n正在处理: {pdf_path}")

        # 获取文件名（不含路径）
        filename = os.path.basename(pdf_path)
        # 去掉.pdf后缀，添加.json
        json_filename = os.path.splitext(filename)[0] + ".json"
        json_path = os.path.join(output_dir, json_filename)

        # 进行NER识别
        result = engine.predict(pdf_path)

        # 保存结果为JSON文件
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"结果已保存到: {json_path}")

    print(f"\n处理完成！所有结果已保存到 {output_dir} 目录")

if __name__ == "__main__":
    batch_process_pdfs()
