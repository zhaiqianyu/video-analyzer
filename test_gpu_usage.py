#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Ollama GPU 使用情况（非交互式）"""
import requests
import time
import subprocess

def check_gpu_before():
    """检查运行前的 GPU 使用情况"""
    print("[INFO] 检查运行前的 GPU 使用情况...")
    try:
        cmd = 'Get-Counter "\\GPU Engine(*)\\Utilization Percentage" | Select-Object -ExpandProperty CounterSamples | Where-Object {$_.InstanceName -like "*Compute*"} | Measure-Object -Property CookedValue -Sum | Select-Object -ExpandProperty Sum'
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            try:
                usage = float(result.stdout.strip())
                print(f"[INFO] 当前 GPU Compute 总使用率: {usage}%")
                return usage
            except:
                print("[INFO] 无法解析 GPU 使用率")
        return 0
    except Exception as e:
        print(f"[WARN] 检查 GPU 时出错: {e}")
        return 0

def test_ollama_request():
    """发送测试请求到 Ollama"""
    print("\n" + "="*60)
    print("发送测试请求到 Ollama...")
    print("="*60)
    
    payload = {
        "model": "llama3.2-vision",
        "prompt": "Describe what you see in one sentence.",
        "stream": False
    }
    
    print("[INFO] 请求内容: 简单的文本生成测试")
    print("[TIP] 请在任务管理器中观察 GPU 使用情况")
    print("   - 任务管理器 -> 性能 -> GPU")
    print("   - 查看 'Compute' 的使用率")
    print()
    
    try:
        print("[INFO] 发送请求中...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=60
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 请求成功完成 (耗时: {elapsed_time:.2f} 秒)")
            print(f"[INFO] 响应长度: {len(result.get('response', ''))} 字符")
            return True
        else:
            print(f"[ERROR] 请求失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return False

def check_gpu_during():
    """在运行期间检查 GPU（需要手动观察）"""
    print("\n" + "="*60)
    print("GPU 使用情况检查")
    print("="*60)
    print()
    print("[TIP] 请手动检查任务管理器中的 GPU 使用情况：")
    print("   1. 打开任务管理器 (Ctrl + Shift + Esc)")
    print("   2. 切换到 '性能' 选项卡")
    print("   3. 选择 GPU")
    print("   4. 查看 'Compute' 或 'DirectML' 的使用率")
    print()
    print("[判断标准]")
    print("   - 如果 GPU Compute 使用率 > 0%: GPU 正在工作")
    print("   - 如果 GPU Compute 使用率 = 0%: 可能在使用 CPU")
    print()

def main():
    print("="*60)
    print("Ollama GPU 使用情况测试")
    print("="*60)
    print()
    
    # 检查运行前状态
    gpu_before = check_gpu_before()
    
    # 发送测试请求
    success = test_ollama_request()
    
    # 提示检查 GPU
    check_gpu_during()
    
    # 总结
    print("="*60)
    print("测试总结")
    print("="*60)
    print()
    print(f"[INFO] Ollama 版本: 0.13.5")
    print(f"[INFO] 测试请求: {'成功' if success else '失败'}")
    print()
    print("[结论]")
    if gpu_before == 0:
        print("   - 当前 GPU Compute 使用率为 0%")
        print("   - 如果运行测试时 GPU 使用率仍为 0%，说明可能在使用 CPU")
        print("   - Intel Arc GPU 在 Ollama 中的支持可能有限")
    else:
        print(f"   - 检测到 GPU 使用率: {gpu_before}%")
    print()
    print("[建议]")
    print("   1. 查看任务管理器确认 GPU 是否被使用")
    print("   2. 如果 GPU 未使用，考虑优化配置以减少处理时间")
    print("   3. 查看 '配置Ollama使用GPU.md' 了解更多配置选项")

if __name__ == "__main__":
    main()



