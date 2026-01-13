import argparse
from pathlib import Path
import json
import logging
import shutil
import sys
from typing import Optional
import torch
import torch.backends.mps

from .config import Config, get_client, get_model
from .frame import VideoProcessor
from .prompt import PromptLoader
from .analyzer import VideoAnalyzer
from .audio_processor import AudioProcessor, AudioTranscript
from .clients.ollama import OllamaClient
from .clients.generic_openai_api import GenericOpenAIAPIClient

# Initialize logger at module level
logger = logging.getLogger(__name__)

def get_log_level(level_str: str) -> int:
    """Convert string log level to logging constant."""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return levels.get(level_str.upper(), logging.INFO)

def cleanup_files(output_dir: Path):
    """Clean up temporary files and directories."""
    try:
        frames_dir = output_dir / "frames"
        if frames_dir.exists():
            shutil.rmtree(frames_dir)
            logger.debug(f"Cleaned up frames directory: {frames_dir}")
            
        audio_file = output_dir / "audio.wav"
        if audio_file.exists():
            audio_file.unlink()
            logger.debug(f"Cleaned up audio file: {audio_file}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def create_client(config: Config):
    """Create the appropriate client based on configuration."""
    client_type = config.get("clients", {}).get("default", "ollama")
    client_config = get_client(config)
    
    if client_type == "ollama":
        return OllamaClient(client_config["url"])
    elif client_type == "openai_api":
        return GenericOpenAIAPIClient(client_config["api_key"], client_config["api_url"])
    else:
        raise ValueError(f"Unknown client type: {client_type}")

def main():
    parser = argparse.ArgumentParser(description="Analyze video using Vision models")
    parser.add_argument("video_path", type=str, help="Path to the video file")
    parser.add_argument("--config", type=str, default="config",
                        help="Path to configuration directory")
    parser.add_argument("--output", type=str, help="Output directory for analysis results")
    parser.add_argument("--client", type=str, help="Client to use (ollama or openrouter)")
    parser.add_argument("--ollama-url", type=str, help="URL for the Ollama service")
    parser.add_argument("--api-key", type=str, help="API key for OpenAI-compatible service")
    parser.add_argument("--api-url", type=str, help="API URL for OpenAI-compatible API")
    parser.add_argument("--model", type=str, help="Name of the vision model to use")
    parser.add_argument("--duration", type=float, help="Duration in seconds to process")
    parser.add_argument("--keep-frames", action="store_true", help="Keep extracted frames after analysis")
    parser.add_argument("--whisper-model", type=str, help="Whisper model size (tiny, base, small, medium, large), or path to local Whisper model snapshot")
    parser.add_argument("--start-stage", type=int, default=1, help="Stage to start processing from (1-3)")
    parser.add_argument("--max-frames", type=int, default=sys.maxsize, help="Maximum number of frames to process")
    parser.add_argument("--log-level", type=str, default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level (default: INFO)")
    parser.add_argument("--prompt", type=str, default="",
                        help="Question to ask about the video")
    parser.add_argument("--language", type=str, default=None)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--temperature", type=float, help="Temperature for LLM generation")
    args = parser.parse_args()

    # Set up logging with specified level
    log_level = get_log_level(args.log_level)
    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True  # Force reconfiguration of the root logger
    )
    # Ensure our module logger has the correct level
    logger.setLevel(log_level)

    # Load and update configuration
    config = Config(args.config)
    config.update_from_args(args)

    # Initialize components
    video_path = Path(args.video_path)
    output_dir = Path(config.get("output_dir"))
    client = create_client(config)
    model = get_model(config)
    prompt_loader = PromptLoader(config.get("prompt_dir"), config.get("prompts", []))
    
    try:
        transcript = None
        frames = []
        frame_analyses = []
        video_description = None
        screening_results = []  # Initialize for two-stage analysis
        analyzer = None  # Initialize analyzer variable
        
        # Stage 1: Frame and Audio Processing
        if args.start_stage <= 1:
            # Initialize audio processor and extract transcript, the AudioProcessor accept following parameters that can be set in config.json:
            # language (str): Language code for audio transcription (default: None)
            # whisper_model (str): Whisper model size or path (default: "medium")
            # device (str): Device to use for audio processing (default: "cpu")
            logger.debug("Initializing audio processing...")
            audio_processor = AudioProcessor(language=config.get("audio", {}).get("language", ""), 
                                             model_size_or_path=config.get("audio", {}).get("whisper_model", "medium"),
                                             device=config.get("audio", {}).get("device", "cpu"))
            
            logger.info("Extracting audio from video...")
            try:
                audio_path = audio_processor.extract_audio(video_path, output_dir)
            except Exception as e:
                logger.error(f"Error extracting audio: {e}")
                audio_path = None
            
            if audio_path is None:
                logger.debug("No audio found in video - skipping transcription")
                transcript = None
            else:
                logger.info("Transcribing audio...")
                transcript = audio_processor.transcribe(audio_path)
                if transcript is None:
                    logger.warning("Could not generate reliable transcript. Proceeding with video analysis only.")
            
            logger.info(f"Extracting frames from video using model {model}...")
            processor = VideoProcessor(
                video_path, 
                output_dir / "frames", 
                model
            )
            frames = processor.extract_keyframes(
                frames_per_minute=config.get("frames", {}).get("per_minute", 60),
                duration=config.get("duration"),
                max_frames=args.max_frames
            )
            
        # Stage 2: Frame Analysis
        if args.start_stage <= 2:
            two_stage_config = config.get("two_stage_analysis", {})
            two_stage_enabled = two_stage_config.get("enabled", False)
            screening_results = []
            
            if two_stage_enabled:
                logger.info("Two-stage analysis enabled: using small model for screening, large model for deep analysis")
                
                # Create small model client
                small_model_config = two_stage_config.get("small_model", {})
                small_client_type = small_model_config.get("client", "ollama")
                small_model = small_model_config.get("model", "llama3.2-vision")
                
                if small_client_type == "ollama":
                    small_client = OllamaClient(config.get("clients", {}).get("ollama", {}).get("url", "http://localhost:11434"))
                elif small_client_type == "openai_api":
                    small_api_config = config.get("clients", {}).get("openai_api", {})
                    # Allow override from small_model config
                    small_api_key = small_model_config.get("api_key") or small_api_config.get("api_key")
                    small_api_url = small_model_config.get("api_url") or small_api_config.get("api_url")
                    if not small_api_key or not small_api_url:
                        raise ValueError("API key and URL required for small model when using openai_api client")
                    small_client = GenericOpenAIAPIClient(small_api_key, small_api_url)
                else:
                    raise ValueError(f"Unknown small model client type: {small_client_type}")
                
                logger.info(f"Small model: {small_model} (client: {small_client_type})")
                logger.info(f"Large model: {model} (client: {config.get('clients', {}).get('default')})")
                
                # Create analyzer with two-stage support
                analyzer = VideoAnalyzer(
                    client, 
                    model, 
                    prompt_loader,
                    config.get("clients", {}).get("temperature", 0.2),
                    config.get("prompt", ""),
                    two_stage_config=two_stage_config,
                    small_client=small_client,
                    small_model=small_model
                )
                
                # Use two-stage analysis
                frame_analyses, screening_results = analyzer.analyze_frames_two_stage(frames)
                logger.info(f"Completed two-stage analysis: {len([a for a in frame_analyses if a and a.get('analyzed_by') != 'small_model_only'])} frames deep analyzed, "
                           f"{len([a for a in frame_analyses if a and a.get('analyzed_by') == 'small_model_only'])} frames screened only")
            else:
                logger.info(f"Analyzing {len(frames)} frames with single-stage approach...")
                analyzer = VideoAnalyzer(
                    client, 
                    model, 
                    prompt_loader,
                    config.get("clients", {}).get("temperature", 0.2),
                    config.get("prompt", "")
                )
                frame_analyses = []
                for idx, frame in enumerate(frames, 1):
                    logger.info(f"Analyzing frame {idx}/{len(frames)} (frame {frame.number})...")
                    analysis = analyzer.analyze_frame(frame)
                    frame_analyses.append(analysis)
                logger.info(f"Completed analyzing {len(frame_analyses)} frames")
                
        # Stage 3: Video Reconstruction
        if args.start_stage <= 3:
            logger.info("Reconstructing video description...")
            video_description = analyzer.reconstruct_video(
                frame_analyses, frames, transcript
            )
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare metadata
        two_stage_config = config.get("two_stage_analysis", {})
        two_stage_enabled = two_stage_config.get("enabled", False)
        
        metadata = {
            "client": config.get("clients", {}).get("default"),
            "model": model,
            "whisper_model": config.get("audio", {}).get("whisper_model"),
            "frames_per_minute": config.get("frames", {}).get("per_minute"),
            "duration_processed": config.get("duration"),
            "frames_extracted": len(frames),
            "frames_processed": min(len(frames), args.max_frames),
            "start_stage": args.start_stage,
            "audio_language": transcript.language if transcript else None,
            "transcription_successful": transcript is not None,
            "two_stage_analysis_enabled": two_stage_enabled
        }
        
        if two_stage_enabled:
            small_model_config = two_stage_config.get("small_model", {})
            metadata["small_model"] = {
                "client": small_model_config.get("client"),
                "model": small_model_config.get("model"),
                "importance_threshold": small_model_config.get("importance_threshold"),
                "max_frames_for_deep_analysis": small_model_config.get("max_frames_for_deep_analysis")
            }
            metadata["large_model"] = {
                "client": config.get("clients", {}).get("default"),
                "model": model
            }
            deep_analyzed_count = len([a for a in frame_analyses if a and a.get('analyzed_by') != 'small_model_only'])
            metadata["frames_deep_analyzed"] = deep_analyzed_count
            metadata["frames_screened_only"] = len(frames) - deep_analyzed_count
        
        results = {
            "metadata": metadata,
            "transcript": {
                "text": transcript.text if transcript else None,
                "segments": transcript.segments if transcript else None
            } if transcript else None,
            "frame_analyses": frame_analyses,
            "video_description": video_description
        }
        
        # Add screening results if two-stage analysis was used
        if two_stage_enabled and screening_results:
            results["screening_results"] = screening_results
        
        with open(output_dir / "analysis.json", "w") as f:
            json.dump(results, f, indent=2)
            
        logger.info("\nTranscript:")
        if transcript:
            logger.info(transcript.text)
        else:
            logger.info("No reliable transcript available")
            
        if video_description:
            logger.info("\nVideo Description:")
            logger.info(video_description.get("response", "No description generated"))
        
        if not config.get("keep_frames"):
            cleanup_files(output_dir)
        
        logger.info(f"Analysis complete. Results saved to {output_dir / 'analysis.json'}")
            
    except Exception as e:
        logger.error(f"Error during video analysis: {e}")
        if not config.get("keep_frames"):
            cleanup_files(output_dir)
        raise

if __name__ == "__main__":
    main()
