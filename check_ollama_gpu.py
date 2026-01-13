#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Ollama GPU 使用情况的脚本"""
import requests
import json
import subprocess
import sys
import io

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_ollama_api():
    """检查 Ollama API 是否可用"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[ERROR] 无法连接到 Ollama API: {e}")
        return None

def check_gpu_usage():
    """检查 GPU 使用情况（通过任务管理器信息）"""
    try:
        # 使用 PowerShell 获取 GPU 信息
        cmd = 'Get-Counter "\\GPU Engine(*)\\Utilization Percentage" | Select-Object -ExpandProperty CounterSamples | Where-Object {$_.InstanceName -like "*Compute*" -or $_.InstanceName -like "*DirectML*"} | Select-Object InstanceName, CookedValue | Format-Table -AutoSize'
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            print("[INFO] GPU 使用情况:")
            print(result.stdout)
            return True
        else:
            print("[WARN] 无法获取 GPU 使用情况（可能需要管理员权限）")
            return False
    except Exception as e:
        print(f"[WARN] 检查 GPU 时出错: {e}")
        return False

def check_ollama_version():
    """检查 Ollama 版本"""
    try:
        # 尝试通过 API 获取版本信息
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print(f"[OK] Ollama 版本: {version_info.get('version', '未知')}")
            return version_info
    except:
        pass
    
    # 尝试通过进程信息获取
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process ollama | Select-Object Path"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("[OK] Ollama 进程正在运行")
            print(result.stdout)
    except:
        pass
    
    return None

def test_model_run():
    """测试运行一个简单的模型请求，观察 GPU 使用"""
    print("\n" + "="*60)
    print("测试模型运行（这将触发 GPU 使用检查）")
    print("="*60)
    
    try:
        # 发送一个简单的请求
        payload = {
            "model": "llama3.2-vision",
            "prompt": "Hello",
            "stream": False
        }
        
        print("[INFO] 发送测试请求到 Ollama...")
        print("[TIP] 提示：请在任务管理器中观察 GPU 使用情况")
        print("   - 打开任务管理器 -> 性能 -> GPU")
        print("   - 查看 'Compute' 或 'DirectML' 的使用率")
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("[OK] 测试请求成功")
            return True
        else:
            print(f"[WARN] 请求返回状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] 测试请求失败: {e}")
        return False

def main():
    print("="*60)
    print("Ollama GPU 使用情况检查工具")
    print("="*60)
    print()
    
    # 1. 检查 Ollama API
    print("\n[1] 检查 Ollama API 连接...")
    models = check_ollama_api()
    if models:
        print("[OK] Ollama API 连接正常")
        model_list = models.get("models", [])
        if model_list:
            print(f"[INFO] 已安装的模型 ({len(model_list)} 个):")
            for model in model_list[:5]:  # 只显示前5个
                print(f"   - {model.get('name', '未知')}")
            if len(model_list) > 5:
                print(f"   ... 还有 {len(model_list) - 5} 个模型")
        else:
            print("[WARN] 未找到已安装的模型")
    else:
        print("[ERROR] 无法连接到 Ollama API")
        print("   请确保 Ollama 服务正在运行: ollama serve")
        return
    
    print()
    
    # 2. 检查 Ollama 版本
    print("\n[2] 检查 Ollama 版本...")
    check_ollama_version()
    
    print()
    
    # 3. 检查 GPU 使用情况
    print("\n[3] 检查 GPU 使用情况...")
    print("[TIP] 提示：请手动打开任务管理器查看 GPU 使用情况")
    print("   - 任务管理器 -> 性能 -> GPU")
    print("   - 查看 'Compute' 或 'DirectML' 的使用率")
    check_gpu_usage()
    
    print()
    
    # 4. 提供配置建议
    print("\n" + "="*60)
    print("配置建议")
    print("="*60)
    print()
    print("对于 Intel Arc GPU，Ollama 的支持可能有限。")
    print("但您可以尝试以下方法：")
    print()
    print("1. 确保使用最新版本的 Ollama:")
    print("   - 访问 https://ollama.ai/download 下载最新版本")
    print()
    print("2. 设置环境变量（如果支持）:")
    print("   $env:OLLAMA_NUM_GPU=1")
    print("   $env:OLLAMA_GPU_LAYERS=32")
    print()
    print("3. 检查 Ollama 日志:")
    print("   - 查看 Ollama 启动时的日志，看是否有 GPU 相关信息")
    print()
    print("4. 使用任务管理器监控:")
    print("   - 运行模型时，观察 GPU 使用率是否上升")
    print("   - 如果 GPU 使用率为 0，说明可能在使用 CPU")
    print()
    
    # 5. 询问是否运行测试
    print("\n" + "="*60)
    response = input("是否运行测试请求来检查 GPU 使用？(y/n): ")
    if response.lower() == 'y':
        test_model_run()
        print()
        print("[OK] 测试完成！请检查任务管理器中的 GPU 使用情况")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

