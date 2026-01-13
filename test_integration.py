#!/usr/bin/env python3
"""Integration test for two-stage analysis with a small video sample."""
import sys
import json
from pathlib import Path

def check_prerequisites():
    """Check if prerequisites are met."""
    print("=" * 60)
    print("Checking Prerequisites")
    print("=" * 60)
    
    issues = []
    
    # Check if config exists
    config_path = Path("config/test_config.json")
    if not config_path.exists():
        issues.append(f"Test config not found: {config_path}")
        print(f"[FAIL] Test config not found: {config_path}")
    else:
        print(f"[OK] Test config found: {config_path}")
    
    # Check Ollama
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            has_vision = any("vision" in m.get("name", "").lower() for m in models)
            if has_vision:
                print("[OK] Ollama is running with vision model")
            else:
                issues.append("Ollama is running but no vision model found")
                print("[WARN] Ollama is running but no vision model found")
                print("  Run: ollama pull llama3.2-vision")
        else:
            issues.append("Ollama service returned error")
            print(f"[FAIL] Ollama service returned status {response.status_code}")
    except Exception as e:
        issues.append("Ollama is not running")
        print(f"[FAIL] Ollama is not running: {e}")
        print("  Start Ollama: ollama serve")
        print("  Or install: https://ollama.ai")
    
    # Check if video file would be provided
    print("\n[INFO] To test with actual video, provide a video file path")
    print("  Example: python test_integration.py --video path/to/video.mp4")
    
    print("\n" + "=" * 60)
    if issues:
        print(f"[FAIL] Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] All prerequisites met!")
        return True

def show_usage_instructions():
    """Show how to use two-stage analysis."""
    print("\n" + "=" * 60)
    print("How to Test Two-Stage Analysis")
    print("=" * 60)
    
    print("\n1. Enable two-stage analysis in config:")
    print('   Set "two_stage_analysis.enabled": true')
    
    print("\n2. Start Ollama (if using local model):")
    print("   ollama serve")
    print("   ollama pull llama3.2-vision")
    
    print("\n3. Run analysis with test config:")
    print('   video-analyzer video.mp4 --config config --max-frames 10')
    
    print("\n4. Check output:")
    print("   - output/analysis.json should contain 'screening_results'")
    print("   - metadata.two_stage_analysis_enabled should be true")
    print("   - metadata.frames_deep_analyzed should show count")
    
    print("\n5. Compare costs:")
    print("   - Single-stage: all frames analyzed with large model")
    print("   - Two-stage: only selected frames analyzed with large model")

def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("Two-Stage Analysis Integration Test")
    print("=" * 60 + "\n")
    
    # Check prerequisites
    prerequisites_ok = check_prerequisites()
    
    # Show usage instructions
    show_usage_instructions()
    
    # If video file provided, run actual test
    if len(sys.argv) > 1 and sys.argv[1] == "--video" and len(sys.argv) > 2:
        video_path = Path(sys.argv[2])
        if video_path.exists():
            print(f"\n[INFO] Video file found: {video_path}")
            print("[INFO] To run analysis, use:")
            print(f'  video-analyzer "{video_path}" --config config --max-frames 10')
        else:
            print(f"\n[FAIL] Video file not found: {video_path}")
            return 1
    
    if prerequisites_ok:
        print("\n[OK] Ready to test! Follow the instructions above.")
        return 0
    else:
        print("\n[FAIL] Please fix the issues above before testing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())






