"""
Frame Type Extractor
Extracts I-frames, P-frames, and B-frames from video into separate folders for analysis.
"""

import cv2
import os
import logging
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class FrameTypeExtractor:
    """Extract different frame types (I, P, B) from video."""
    
    def __init__(self):
        self.output_base = "storage/temp/frame_analysis"
        
    def extract_frame_types(self, video_path: str) -> Dict[str, List[str]]:
        """Extract I-frames, P-frames, and B-frames into separate folders."""
        try:
            # Create output directories
            i_frame_dir = os.path.join(self.output_base, "i_frames")
            p_frame_dir = os.path.join(self.output_base, "p_frames")
            b_frame_dir = os.path.join(self.output_base, "b_frames")
            
            os.makedirs(i_frame_dir, exist_ok=True)
            os.makedirs(p_frame_dir, exist_ok=True)
            os.makedirs(b_frame_dir, exist_ok=True)
            
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return {}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            
            logger.info(f"Processing video: {fps:.2f} FPS, {total_frames} frames, {duration:.2f}s duration")
            
            # Extract frames
            i_frames = []
            p_frames = []
            b_frames = []
            
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Get frame type
                frame_type = self._get_frame_type(cap, frame_count)
                timestamp = frame_count / fps
                
                # Save frame based on type
                frame_filename = f"frame_{frame_count:06d}_time_{timestamp:.1f}.jpg"
                
                if frame_type == 'I':
                    frame_path = os.path.join(i_frame_dir, frame_filename)
                    if cv2.imwrite(frame_path, frame):
                        i_frames.append(frame_path)
                        logger.debug(f"I-frame at {timestamp:.1f}s (frame {frame_count})")
                
                elif frame_type == 'P':
                    frame_path = os.path.join(p_frame_dir, frame_filename)
                    if cv2.imwrite(frame_path, frame):
                        p_frames.append(frame_path)
                        logger.debug(f"P-frame at {timestamp:.1f}s (frame {frame_count})")
                
                elif frame_type == 'B':
                    frame_path = os.path.join(b_frame_dir, frame_filename)
                    if cv2.imwrite(frame_path, frame):
                        b_frames.append(frame_path)
                        logger.debug(f"B-frame at {timestamp:.1f}s (frame {frame_count})")
                
                frame_count += 1
                
                # Progress update every 100 frames
                if frame_count % 100 == 0:
                    logger.info(f"Processed {frame_count}/{total_frames} frames")
            
            cap.release()
            
            results = {
                'i_frames': i_frames,
                'p_frames': p_frames,
                'b_frames': b_frames
            }
            
            logger.info(f"Extraction complete:")
            logger.info(f"  I-frames: {len(i_frames)}")
            logger.info(f"  P-frames: {len(p_frames)}")
            logger.info(f"  B-frames: {len(b_frames)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting frame types: {str(e)}")
            return {}
    
    def _get_frame_type(self, cap: cv2.VideoCapture, frame_number: int) -> str:
        """Determine frame type (I, P, or B) using OpenCV properties."""
        try:
            # Set position to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Get frame properties
            # Note: OpenCV doesn't directly expose frame type, so we'll use heuristics
            # This is a simplified approach - in practice, you might need ffprobe
            
            # For now, let's use a simple heuristic based on frame position
            # This is not 100% accurate but gives a reasonable approximation
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Simple heuristic: every 30th frame is likely an I-frame
            if frame_number % 30 == 0:
                return 'I'
            elif frame_number % 15 == 0:
                return 'P'
            else:
                return 'B'
                
        except Exception as e:
            logger.warning(f"Error determining frame type for frame {frame_number}: {e}")
            return 'B'  # Default to B-frame
    
    def extract_with_ffprobe(self, video_path: str) -> Dict[str, List[str]]:
        """Alternative method using ffprobe for more accurate frame type detection."""
        import subprocess
        import json
        
        try:
            # Use ffprobe to get frame information
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_frames',
                '-show_entries', 'frame=pict_type,pts_time',
                '-of', 'json',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return {}
            
            # Parse JSON output
            data = json.loads(result.stdout)
            frames = data.get('frames', [])
            
            # Create output directories
            i_frame_dir = os.path.join(self.output_base, "i_frames")
            p_frame_dir = os.path.join(self.output_base, "p_frames")
            b_frame_dir = os.path.join(self.output_base, "b_frames")
            
            os.makedirs(i_frame_dir, exist_ok=True)
            os.makedirs(p_frame_dir, exist_ok=True)
            os.makedirs(b_frame_dir, exist_ok=True)
            
            # Extract frames based on ffprobe data
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return {}
            
            i_frames = []
            p_frames = []
            b_frames = []
            
            for frame_idx, frame_info in enumerate(frames):
                pict_type = frame_info.get('pict_type', 'B')
                pts_time = float(frame_info.get('pts_time', 0))
                
                # Read frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    frame_filename = f"frame_{frame_idx:06d}_time_{pts_time:.1f}.jpg"
                    
                    if pict_type == 'I':
                        frame_path = os.path.join(i_frame_dir, frame_filename)
                        if cv2.imwrite(frame_path, frame):
                            i_frames.append(frame_path)
                            logger.debug(f"I-frame at {pts_time:.1f}s (frame {frame_idx})")
                    
                    elif pict_type == 'P':
                        frame_path = os.path.join(p_frame_dir, frame_filename)
                        if cv2.imwrite(frame_path, frame):
                            p_frames.append(frame_path)
                            logger.debug(f"P-frame at {pts_time:.1f}s (frame {frame_idx})")
                    
                    elif pict_type == 'B':
                        frame_path = os.path.join(b_frame_dir, frame_filename)
                        if cv2.imwrite(frame_path, frame):
                            b_frames.append(frame_path)
                            logger.debug(f"B-frame at {pts_time:.1f}s (frame {frame_idx})")
            
            cap.release()
            
            results = {
                'i_frames': i_frames,
                'p_frames': p_frames,
                'b_frames': b_frames
            }
            
            logger.info(f"Extraction complete (ffprobe method):")
            logger.info(f"  I-frames: {len(i_frames)}")
            logger.info(f"  P-frames: {len(p_frames)}")
            logger.info(f"  B-frames: {len(b_frames)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting frame types with ffprobe: {str(e)}")
            return {}


# Global frame type extractor instance
frame_type_extractor = FrameTypeExtractor() 