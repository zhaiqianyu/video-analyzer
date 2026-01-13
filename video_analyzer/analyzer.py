from typing import List, Dict, Any, Optional, Tuple
import logging
import re
from .clients.llm_client import LLMClient
from .prompt import PromptLoader
from .frame import Frame
from .audio_processor import AudioTranscript

logger = logging.getLogger(__name__)

class VideoAnalyzer:
    def __init__(self, client: LLMClient, model: str, prompt_loader: PromptLoader, temperature: float, 
                 user_prompt: str = "", two_stage_config: Optional[Dict[str, Any]] = None,
                 small_client: Optional[LLMClient] = None, small_model: Optional[str] = None):
        """Initialize the VideoAnalyzer.
        
        Args:
            client: LLM client for making API calls (large model)
            model: Name of the model to use (large model)
            prompt_loader: Loader for prompt templates
            temperature: Temperature for LLM generation
            user_prompt: Optional user question about the video that will be injected into frame analysis
                        and video description prompts using the {prompt} token
            two_stage_config: Configuration for two-stage analysis (optional)
            small_client: Small model client for screening (optional)
            small_model: Small model name for screening (optional)
        """
        self.client = client
        self.model = model
        self.prompt_loader = prompt_loader
        self.temperature = temperature
        self.user_prompt = user_prompt  # Store user's question about the video
        self.two_stage_config = two_stage_config
        self.small_client = small_client
        self.small_model = small_model
        self._load_prompts()
        self.previous_analyses = []
        self.screening_results = []  # Store screening results for two-stage analysis
        
    def _format_user_prompt(self) -> str:
        """Format the user's prompt by adding prefix if not empty."""
        if self.user_prompt:
            return f"I want to know {self.user_prompt}"
        return ""
        
    def _load_prompts(self):
        """Load prompts from files."""
        self.frame_prompt = self.prompt_loader.get_by_index(0)  # Frame Analysis prompt
        self.video_prompt = self.prompt_loader.get_by_index(1)  # Video Reconstruction prompt
        # Try to load screening prompt (may not exist if not using two-stage)
        try:
            self.screening_prompt = self.prompt_loader.get_by_index(2)  # Frame Screening prompt
        except (IndexError, FileNotFoundError):
            self.screening_prompt = None

    def _format_previous_analyses(self) -> str:
        """Format previous frame analyses for inclusion in prompt."""
        if not self.previous_analyses:
            return ""
            
        formatted_analyses = []
        for i, analysis in enumerate(self.previous_analyses):
            formatted_analysis = (
                f"Frame {i}\n"
                f"{analysis.get('response', 'No analysis available')}\n"
            )
            formatted_analyses.append(formatted_analysis)
            
        return "\n".join(formatted_analyses)

    def _parse_screening_result(self, response: str) -> Dict[str, Any]:
        """Parse screening result from model response.
        
        Returns:
            Dict with keys: description, importance_score, needs_deep_analysis
        """
        result = {
            "description": "",
            "importance_score": 0,
            "needs_deep_analysis": False
        }
        
        try:
            # Extract description
            desc_match = re.search(r'【简要描述】\s*(.*?)(?=【|$)', response, re.DOTALL)
            if desc_match:
                result["description"] = desc_match.group(1).strip()
            
            # Extract importance score
            score_match = re.search(r'【重要性评分】\s*(\d+)', response)
            if score_match:
                result["importance_score"] = int(score_match.group(1))
            
            # Extract needs deep analysis
            needs_match = re.search(r'【是否需要深度分析】\s*(是|否)', response)
            if needs_match:
                result["needs_deep_analysis"] = needs_match.group(1) == "是"
            
        except Exception as e:
            logger.warning(f"Error parsing screening result: {e}, using raw response")
            result["description"] = response[:200]  # Use first 200 chars as fallback
        
        return result

    def screen_frame(self, frame: Frame) -> Dict[str, Any]:
        """Screen a frame using small model to determine if it needs deep analysis.
        
        Returns:
            Dict with screening results including description, importance_score, needs_deep_analysis
        """
        if not self.small_client or not self.small_model or not self.screening_prompt:
            raise ValueError("Small model client, model, or screening prompt not configured")
        
        if not frame.path.exists():
            error_msg = f"Frame file does not exist: {frame.path} (frame {frame.number})"
            logger.error(error_msg)
            return {
                "description": error_msg,
                "importance_score": 0,
                "needs_deep_analysis": False,
                "error": error_msg
            }
        
        # Format prompt
        prompt = self.screening_prompt.replace("{prompt}", self._format_user_prompt())
        prompt = f"{prompt}\n这是第 {frame.number} 帧，时间位置：{frame.timestamp:.2f} 秒。"
        
        try:
            response = self.small_client.generate(
                prompt=prompt,
                image_path=str(frame.path),
                model=self.small_model,
                temperature=0.1,  # Lower temperature for more consistent screening
                num_predict=150  # Shorter output for screening
            )
            
            screening_result = self._parse_screening_result(response.get('response', ''))
            screening_result['frame_number'] = frame.number
            screening_result['timestamp'] = frame.timestamp
            screening_result['raw_response'] = response.get('response', '')
            
            logger.debug(f"Screened frame {frame.number}: importance={screening_result['importance_score']}, "
                        f"needs_deep={screening_result['needs_deep_analysis']}")
            
            return screening_result
            
        except Exception as e:
            logger.error(f"Error screening frame {frame.number}: {e}")
            return {
                "description": f"Error screening frame: {str(e)}",
                "importance_score": 0,
                "needs_deep_analysis": False,
                "error": str(e),
                "frame_number": frame.number
            }

    def analyze_frame(self, frame: Frame) -> Dict[str, Any]:
        """Analyze a single frame using the LLM."""
        # Check if frame file exists before analysis
        if not frame.path.exists():
            error_msg = f"Frame file does not exist: {frame.path} (frame {frame.number})"
            logger.error(error_msg)
            error_result = {"response": f"Error analyzing frame {frame.number}: {error_msg}"}
            self.previous_analyses.append(error_result)
            return error_result
        
        # Replace {PREVIOUS_FRAMES} token with formatted previous analyses
        # Replace tokens in the prompt template
        prompt = self.frame_prompt.replace("{PREVIOUS_FRAMES}", self._format_previous_analyses())
        prompt = prompt.replace("{prompt}", self._format_user_prompt())
        prompt = f"{prompt}\nThis is frame {frame.number} captured at {frame.timestamp:.2f} seconds."
        
        try:
            response = self.client.generate(
                prompt=prompt,
                image_path=str(frame.path),
                model=self.model,
                temperature=self.temperature,
                num_predict=300
            )
            logger.debug(f"Successfully analyzed frame {frame.number}")
            
            # Store the analysis for future frames
            analysis_result = {k: v for k, v in response.items() if k != "context"}
            self.previous_analyses.append(analysis_result)
            
            return analysis_result
        except Exception as e:
            logger.error(f"Error analyzing frame {frame.number}: {e}")
            error_result = {"response": f"Error analyzing frame {frame.number}: {str(e)}"}
            self.previous_analyses.append(error_result)
            return error_result

    def analyze_frames_two_stage(self, frames: List[Frame]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Analyze frames using two-stage approach: screen with small model, then deep analyze selected frames.
        
        Args:
            frames: List of frames to analyze
            
        Returns:
            Tuple of (frame_analyses, screening_results)
            - frame_analyses: List of analysis results (may be None for non-selected frames)
            - screening_results: List of screening results for all frames
        """
        if not self.two_stage_config or not self.two_stage_config.get("enabled"):
            raise ValueError("Two-stage analysis is not enabled")
        
        if not self.small_client or not self.small_model:
            raise ValueError("Small model client and model must be configured for two-stage analysis")
        
        importance_threshold = self.two_stage_config.get("small_model", {}).get("importance_threshold", 6)
        max_frames = self.two_stage_config.get("small_model", {}).get("max_frames_for_deep_analysis", 10)
        
        logger.info(f"Starting two-stage analysis: screening {len(frames)} frames, "
                   f"threshold={importance_threshold}, max_deep_analysis={max_frames}")
        
        # Stage 1: Screen all frames with small model
        screening_results = []
        for idx, frame in enumerate(frames, 1):
            logger.info(f"Screening frame {idx}/{len(frames)} (frame {frame.number})...")
            screening_result = self.screen_frame(frame)
            screening_results.append(screening_result)
        
        # Select frames for deep analysis
        # Priority: needs_deep_analysis=True > high importance_score > ensure time distribution
        candidates = []
        for i, (frame, screening) in enumerate(zip(frames, screening_results)):
            score = screening.get("importance_score", 0)
            needs_deep = screening.get("needs_deep_analysis", False)
            
            # Calculate priority: higher score = higher priority
            priority = score
            if needs_deep:
                priority += 10  # Boost priority if explicitly marked
            
            candidates.append({
                "index": i,
                "frame": frame,
                "screening": screening,
                "priority": priority
            })
        
        # Sort by priority and select top frames
        candidates.sort(key=lambda x: x["priority"], reverse=True)
        selected_indices = set()
        
        # Ensure we have frames from different time periods
        total_duration = frames[-1].timestamp if frames else 0
        time_buckets = {}
        for candidate in candidates:
            frame = candidate["frame"]
            bucket = int(frame.timestamp / max(total_duration / 3, 1))  # 3 time buckets
            if bucket not in time_buckets:
                time_buckets[bucket] = []
            time_buckets[bucket].append(candidate)
        
        # Select frames: prioritize high priority, but ensure time distribution
        selected = []
        for bucket in sorted(time_buckets.keys()):
            bucket_candidates = sorted(time_buckets[bucket], key=lambda x: x["priority"], reverse=True)
            for candidate in bucket_candidates[:max(1, max_frames // 3)]:  # At least 1 per bucket
                if len(selected) < max_frames and candidate["index"] not in selected_indices:
                    selected.append(candidate)
                    selected_indices.add(candidate["index"])
        
        # Fill remaining slots with highest priority frames
        for candidate in candidates:
            if len(selected) >= max_frames:
                break
            if candidate["index"] not in selected_indices:
                selected.append(candidate)
                selected_indices.add(candidate["index"])
        
        # Sort selected frames by original order
        selected.sort(key=lambda x: x["index"])
        
        logger.info(f"Selected {len(selected)} frames for deep analysis out of {len(frames)} total frames")
        
        # Stage 2: Deep analyze selected frames
        frame_analyses = [None] * len(frames)  # Initialize with None
        self.previous_analyses = []  # Reset for deep analysis
        
        for idx, candidate in enumerate(selected, 1):
            frame = candidate["frame"]
            frame_idx = candidate["index"]
            screening = candidate["screening"]
            
            logger.info(f"Deep analyzing frame {idx}/{len(selected)} (frame {frame.number}, "
                       f"importance={screening.get('importance_score', 0)})...")
            
            # Include screening description in context for deep analysis
            analysis = self.analyze_frame(frame)
            
            # Enhance analysis with screening info
            if "screening_description" not in analysis:
                analysis["screening_description"] = screening.get("description", "")
                analysis["importance_score"] = screening.get("importance_score", 0)
            
            frame_analyses[frame_idx] = analysis
        
        # For frames not selected, use screening description as analysis
        for i, (frame, screening) in enumerate(zip(frames, screening_results)):
            if frame_analyses[i] is None:
                frame_analyses[i] = {
                    "response": f"[快速筛选结果] {screening.get('description', '无描述')}",
                    "screening_description": screening.get("description", ""),
                    "importance_score": screening.get("importance_score", 0),
                    "analyzed_by": "small_model_only"
                }
        
        return frame_analyses, screening_results

    def reconstruct_video(self, frame_analyses: List[Dict[str, Any]], frames: List[Frame], 
                         transcript: Optional[AudioTranscript] = None) -> Dict[str, Any]:
        """Reconstruct video description from frame analyses and transcript."""
        frame_notes = []
        for i, (frame, analysis) in enumerate(zip(frames, frame_analyses)):
            frame_note = (
                f"Frame {i} ({frame.timestamp:.2f}s):\n"
                f"{analysis.get('response', 'No analysis available')}"
            )
            frame_notes.append(frame_note)
        
        analysis_text = "\n\n".join(frame_notes)
        
        # Get first frame analysis
        first_frame_text = ""
        if frame_analyses and len(frame_analyses) > 0:
            first_frame_text = frame_analyses[0].get('response', '')
        
        # Include transcript information if available
        transcript_text = ""
        if transcript and transcript.text.strip():
            transcript_text = transcript.text
        
        # Replace tokens in the prompt template
        prompt = self.video_prompt.replace("{prompt}", self._format_user_prompt())
        prompt = prompt.replace("{FRAME_NOTES}", analysis_text)
        prompt = prompt.replace("{FIRST_FRAME}", first_frame_text)
        prompt = prompt.replace("{TRANSCRIPT}", transcript_text)
        
        try:
            response = self.client.generate(
                prompt=prompt,
                model=self.model,
                temperature=self.temperature,
                num_predict=1000
            )
            logger.info("Successfully reconstructed video description")
            return {k: v for k, v in response.items() if k != "context"}
        except Exception as e:
            logger.error(f"Error reconstructing video: {e}")
            return {"response": f"Error reconstructing video: {str(e)}"}
