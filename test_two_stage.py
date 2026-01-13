#!/usr/bin/env python3
"""Test script for two-stage analysis functionality."""
import json
import sys
from pathlib import Path
from video_analyzer.config import Config
from video_analyzer.prompt import PromptLoader
from video_analyzer.clients.ollama import OllamaClient
from video_analyzer.clients.generic_openai_api import GenericOpenAIAPIClient
from video_analyzer.analyzer import VideoAnalyzer
from video_analyzer.frame import Frame

def test_config_loading():
    """Test that two-stage config is loaded correctly."""
    print("=" * 60)
    print("Test 1: Configuration Loading")
    print("=" * 60)
    
    config = Config("video_analyzer/config")
    two_stage = config.get("two_stage_analysis", {})
    
    print(f"Two-stage enabled: {two_stage.get('enabled', False)}")
    print(f"Small model client: {two_stage.get('small_model', {}).get('client')}")
    print(f"Small model: {two_stage.get('small_model', {}).get('model')}")
    print(f"Importance threshold: {two_stage.get('small_model', {}).get('importance_threshold')}")
    print(f"Max frames: {two_stage.get('small_model', {}).get('max_frames_for_deep_analysis')}")
    
    assert "two_stage_analysis" in config.config, "Two-stage config not found"
    print("[OK] Configuration loaded successfully\n")
    return config

def test_prompt_loading():
    """Test that screening prompt is loaded."""
    print("=" * 60)
    print("Test 2: Prompt Loading")
    print("=" * 60)
    
    config = Config("video_analyzer/config")
    prompt_loader = PromptLoader(config.get("prompt_dir"), config.get("prompts", []))
    
    # Test all prompts
    try:
        frame_prompt = prompt_loader.get_by_index(0)
        print(f"[OK] Frame analysis prompt loaded ({len(frame_prompt)} chars)")
    except Exception as e:
        print(f"[FAIL] Failed to load frame analysis prompt: {e}")
        return False
    
    try:
        video_prompt = prompt_loader.get_by_index(1)
        print(f"[OK] Video reconstruction prompt loaded ({len(video_prompt)} chars)")
    except Exception as e:
        print(f"[FAIL] Failed to load video reconstruction prompt: {e}")
        return False
    
    try:
        screening_prompt = prompt_loader.get_by_index(2)
        print(f"[OK] Screening prompt loaded ({len(screening_prompt)} chars)")
        print(f"  Preview: {screening_prompt[:100]}...")
    except Exception as e:
        print(f"[FAIL] Failed to load screening prompt: {e}")
        return False
    
    print("[OK] All prompts loaded successfully\n")
    return True

def test_ollama_connection():
    """Test Ollama service connection."""
    print("=" * 60)
    print("Test 3: Ollama Service Connection")
    print("=" * 60)
    
    try:
        client = OllamaClient("http://localhost:11434")
        # Try to list models (simple test)
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            print(f"[OK] Ollama service is running")
            print(f"  Available models: {', '.join(model_names[:5])}")
            
            # Check if llama3.2-vision is available
            has_vision = any("vision" in name.lower() for name in model_names)
            if has_vision:
                print(f"[OK] Vision model found")
            else:
                print(f"[WARN] No vision model found. You may need to run: ollama pull llama3.2-vision")
            
            print("[OK] Ollama connection successful\n")
            return True
        else:
            print(f"[FAIL] Ollama service returned status {response.status_code}\n")
            return False
    except Exception as e:
        print(f"[FAIL] Failed to connect to Ollama: {e}")
        print("  Make sure Ollama is running: ollama serve\n")
        return False

def test_screening_parsing():
    """Test screening result parsing."""
    print("=" * 60)
    print("Test 4: Screening Result Parsing")
    print("=" * 60)
    
    from video_analyzer.analyzer import VideoAnalyzer
    from video_analyzer.clients.llm_client import LLMClient
    
    # Create a mock analyzer to test parsing
    class MockClient(LLMClient):
        def generate(self, prompt, image_path=None, **kwargs):
            return {"response": """【简要描述】
画面显示一个医美机构的宣传画面，包含前后对比图和文字说明。

【重要性评分】
8

【是否需要深度分析】
是"""}
    
    config = Config("video_analyzer/config")
    prompt_loader = PromptLoader(config.get("prompt_dir"), config.get("prompts", []))
    
    analyzer = VideoAnalyzer(
        MockClient(),
        "test-model",
        prompt_loader,
        0.2,
        two_stage_config={"enabled": True},
        small_client=MockClient(),
        small_model="test"
    )
    
    # Test parsing
    test_response = """【简要描述】
画面显示一个医美机构的宣传画面，包含前后对比图和文字说明。

【重要性评分】
8

【是否需要深度分析】
是"""
    
    result = analyzer._parse_screening_result(test_response)
    
    print(f"Parsed description: {result['description'][:50]}...")
    print(f"Parsed importance_score: {result['importance_score']}")
    print(f"Parsed needs_deep_analysis: {result['needs_deep_analysis']}")
    
    assert result['importance_score'] == 8, "Failed to parse importance score"
    assert result['needs_deep_analysis'] == True, "Failed to parse needs_deep_analysis"
    assert len(result['description']) > 0, "Failed to parse description"
    
    print("[OK] Screening result parsing successful\n")
    return True

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Two-Stage Analysis Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Prompt Loading", test_prompt_loading),
        ("Ollama Connection", test_ollama_connection),
        ("Screening Parsing", test_screening_parsing),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result if result is not None else True))
        except Exception as e:
            print(f"[FAIL] Test '{name}' failed with exception: {e}\n")
            results.append((name, False))
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All tests passed! Two-stage analysis is ready to use.")
        print("\nTo enable two-stage analysis, set in config:")
        print('  "two_stage_analysis": { "enabled": true }')
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed. Please fix issues before using.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

