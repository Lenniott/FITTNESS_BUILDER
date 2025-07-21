"""
Enhanced transcription service with quality validation and improved segment handling.
Addresses transcription quality issues for better AI analysis.
"""

import asyncio
import logging
import os
import tempfile
import subprocess
from typing import Dict, List, Optional, Any, Tuple
import json

import whisper
from openai import OpenAI

logger = logging.getLogger(__name__)

class EnhancedTranscriptionService:
    """Enhanced transcription service with quality validation and improved segment handling."""
    
    def __init__(self):
        self.min_segment_duration = 1.0  # Minimum segment duration in seconds
        self.max_segment_duration = 30.0  # Maximum segment duration in seconds
        self.min_audio_quality = 0.3  # Minimum audio quality score
        self.min_text_length = 3  # Minimum characters in transcript text
        self.max_text_length = 500  # Maximum characters in transcript text
    
    async def transcribe_audio(self, video_file: str) -> List[Dict[str, Any]]:
        """
        Enhanced audio transcription with quality validation.
        
        Args:
            video_file: Path to video file
            
        Returns:
            List of validated transcript segments with timestamps
        """
        try:
            # Step 1: Validate audio quality before transcription
            audio_quality = await self._validate_audio_quality(video_file)
            if not audio_quality['is_valid']:
                logger.warning(f"⚠️  Poor audio quality detected: {audio_quality['warnings']}")
                # Continue with transcription but log the issues
            
            # Step 2: Check for existing subtitle files
            subtitle_file = await self._find_subtitle_file(video_file)
            
            if subtitle_file:
                logger.info(f"Found existing subtitle file: {subtitle_file}")
                segments = await self._parse_subtitle_file(subtitle_file)
            else:
                logger.info("No subtitle file found, using Whisper for transcription")
                segments = await self._transcribe_with_whisper(video_file)
            
            # Step 3: Validate and clean transcript segments
            validated_segments = await self._validate_and_clean_segments(segments, video_file)
            
            # Step 4: Merge short segments and improve timing
            improved_segments = await self._merge_and_improve_segments(validated_segments)
            
            # Step 5: Final quality check
            final_segments = await self._final_quality_check(improved_segments)
            
            logger.info(f"✅ Enhanced transcription complete: {len(final_segments)} segments")
            return final_segments
            
        except Exception as e:
            logger.error(f"Error in enhanced transcription: {str(e)}")
            return []
    
    async def _validate_audio_quality(self, video_file: str) -> Dict[str, Any]:
        """Validate audio quality before transcription."""
        result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'metadata': {}
        }
        
        try:
            # Use FFmpeg to analyze audio
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'a',
                '-show_entries', 'stream=codec_name,sample_rate,channels,bit_rate',
                '-of', 'json',
                video_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                result['errors'].append("No audio stream found")
                result['is_valid'] = False
                return result
            
            # Parse audio information
            audio_data = json.loads(stdout.decode())
            audio_streams = audio_data.get('streams', [])
            
            if not audio_streams:
                result['errors'].append("No audio streams found")
                result['is_valid'] = False
                return result
            
            audio_stream = audio_streams[0]
            result['metadata'] = {
                'codec': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': audio_stream.get('sample_rate', 'unknown'),
                'channels': audio_stream.get('channels', 'unknown'),
                'bit_rate': audio_stream.get('bit_rate', 'unknown')
            }
            
            # Check audio quality indicators
            sample_rate = audio_stream.get('sample_rate')
            if sample_rate and int(sample_rate) < 22050:
                result['warnings'].append(f"Low audio sample rate: {sample_rate} Hz")
            
            bit_rate = audio_stream.get('bit_rate')
            if bit_rate and int(bit_rate) < 64000:
                result['warnings'].append(f"Low audio bit rate: {bit_rate} bps")
            
            # Check for audio duration
            duration_cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                video_file
            ]
            
            duration_process = await asyncio.create_subprocess_exec(
                *duration_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            duration_stdout, _ = await duration_process.communicate()
            
            if duration_process.returncode == 0:
                try:
                    duration = float(duration_stdout.decode().strip())
                    result['metadata']['duration'] = duration
                    
                    if duration < 5.0:
                        result['warnings'].append(f"Very short audio duration: {duration:.1f}s")
                    elif duration > 600.0:
                        result['warnings'].append(f"Very long audio duration: {duration:.1f}s")
                except ValueError:
                    result['warnings'].append("Could not determine audio duration")
            
            return result
            
        except Exception as e:
            result['errors'].append(f"Error validating audio quality: {str(e)}")
            result['is_valid'] = False
            return result
    
    async def _find_subtitle_file(self, video_file: str) -> Optional[str]:
        """Find subtitle file in the same directory as the video file."""
        video_dir = os.path.dirname(video_file)
        video_name = os.path.splitext(os.path.basename(video_file))[0]
        
        # Look for subtitle files with common extensions
        subtitle_extensions = ['.vtt', '.srt', '.ass', '.ssa', '.sub']
        
        for ext in subtitle_extensions:
            subtitle_file = os.path.join(video_dir, f"{video_name}{ext}")
            if os.path.exists(subtitle_file):
                return subtitle_file
        
        # Also check for files with language codes (e.g., .en.vtt)
        for ext in subtitle_extensions:
            for lang in ['en', 'en-US', 'en-GB']:
                subtitle_file = os.path.join(video_dir, f"{video_name}.{lang}{ext}")
                if os.path.exists(subtitle_file):
                    return subtitle_file
        
        # Only check .txt files if they look like actual subtitles
        txt_file = os.path.join(video_dir, f"{video_name}.txt")
        if os.path.exists(txt_file):
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # If it contains timestamp patterns, it's a subtitle
                    if '-->' in content or any(line.strip().count(':') >= 2 for line in content.split('\n')):
                        return txt_file
                    # If it's just a short caption, skip it
                    elif len(content.strip()) < 200:
                        logger.info(f"Skipping short caption file: {txt_file}")
                        return None
            except Exception as e:
                logger.warning(f"Error checking txt file: {str(e)}")
        
        return None
    
    async def _parse_subtitle_file(self, subtitle_file: str) -> List[Dict[str, Any]]:
        """Parse subtitle file with enhanced validation."""
        try:
            ext = os.path.splitext(subtitle_file)[1].lower()
            
            if ext == '.vtt':
                return await self._parse_vtt_file(subtitle_file)
            elif ext == '.srt':
                return await self._parse_srt_file(subtitle_file)
            elif ext == '.txt':
                return await self._parse_txt_file(subtitle_file)
            else:
                logger.warning(f"Unsupported subtitle format: {ext}")
                return []
                
        except Exception as e:
            logger.error(f"Error parsing subtitle file: {str(e)}")
            return []
    
    async def _parse_vtt_file(self, vtt_file: str) -> List[Dict[str, Any]]:
        """Parse VTT subtitle file with validation."""
        segments = []
        
        try:
            with open(vtt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if not line or line == 'WEBVTT':
                    i += 1
                    continue
                
                if '-->' in line:
                    try:
                        start_time, end_time = line.split(' --> ')
                        start_seconds = self._parse_timestamp(start_time)
                        end_seconds = self._parse_timestamp(end_time)
                        
                        # Validate timing
                        if end_seconds <= start_seconds:
                            logger.warning(f"Invalid timing in VTT: {start_seconds} -> {end_seconds}")
                            i += 1
                            continue
                        
                        # Get text
                        text_lines = []
                        i += 1
                        while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                            text_lines.append(lines[i].strip())
                            i += 1
                        
                        text = ' '.join(text_lines).strip()
                        if text and len(text) >= self.min_text_length:
                            segments.append({
                                'start': start_seconds,
                                'end': end_seconds,
                                'text': text,
                                'duration': end_seconds - start_seconds
                            })
                    except Exception as e:
                        logger.warning(f"Error parsing VTT timestamp: {str(e)}")
                        i += 1
                else:
                    i += 1
            
            logger.info(f"Parsed {len(segments)} segments from VTT file")
            return segments
            
        except Exception as e:
            logger.error(f"Error parsing VTT file: {str(e)}")
            return []
    
    async def _parse_srt_file(self, srt_file: str) -> List[Dict[str, Any]]:
        """Parse SRT subtitle file with validation."""
        segments = []
        
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            blocks = content.split('\n\n')
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    try:
                        timestamp_line = lines[1]
                        start_time, end_time = timestamp_line.split(' --> ')
                        start_seconds = self._parse_timestamp(start_time)
                        end_seconds = self._parse_timestamp(end_time)
                        
                        # Validate timing
                        if end_seconds <= start_seconds:
                            logger.warning(f"Invalid timing in SRT: {start_seconds} -> {end_seconds}")
                            continue
                        
                        text = ' '.join(lines[2:]).strip()
                        if text and len(text) >= self.min_text_length:
                            segments.append({
                                'start': start_seconds,
                                'end': end_seconds,
                                'text': text,
                                'duration': end_seconds - start_seconds
                            })
                    except Exception as e:
                        logger.warning(f"Error parsing SRT block: {str(e)}")
                        continue
            
            logger.info(f"Parsed {len(segments)} segments from SRT file")
            return segments
            
        except Exception as e:
            logger.error(f"Error parsing SRT file: {str(e)}")
            return []
    
    async def _parse_txt_file(self, txt_file: str) -> List[Dict[str, Any]]:
        """Parse text file with validation."""
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            if text and len(text) >= self.min_text_length:
                # Create a single segment for the entire text
                segments = [{
                    'start': 0.0,
                    'end': 0.0,  # Duration unknown
                    'text': text,
                    'duration': 0.0
                }]
                logger.info("Parsed text file as transcript")
                return segments
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error parsing text file: {str(e)}")
            return []
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse timestamp string to seconds."""
        try:
            if ',' in timestamp:
                time_part, ms_part = timestamp.split(',')
                hours, minutes, seconds = map(int, time_part.split(':'))
                milliseconds = int(ms_part)
                return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
            elif '.' in timestamp:
                time_part, ms_part = timestamp.split('.')
                hours, minutes, seconds = map(int, time_part.split(':'))
                milliseconds = int(ms_part)
                return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
            else:
                hours, minutes, seconds = map(int, timestamp.split(':'))
                return hours * 3600 + minutes * 60 + seconds
        except Exception as e:
            logger.warning(f"Error parsing timestamp {timestamp}: {str(e)}")
            return 0.0
    
    async def _transcribe_with_whisper(self, video_file: str) -> List[Dict[str, Any]]:
        """Transcribe using Whisper with enhanced validation."""
        try:
            # Load Whisper model
            model = whisper.load_model("base")
            
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, model.transcribe, video_file)
            
            # Format and validate transcript segments
            segments = []
            if result and isinstance(result, dict) and 'segments' in result:
                for segment in result['segments']:
                    if isinstance(segment, dict):
                        start = float(segment.get('start', 0.0))
                        end = float(segment.get('end', 0.0))
                        text = str(segment.get('text', '')).strip()
                        
                        # Basic validation
                        if end > start and text and len(text) >= self.min_text_length:
                            segments.append({
                                'start': start,
                                'end': end,
                                'text': text,
                                'duration': end - start
                            })
            
            logger.info(f"Transcribed {len(segments)} segments with Whisper")
            return segments
            
        except Exception as e:
            logger.error(f"Error transcribing with Whisper: {str(e)}")
            return []
    
    async def _validate_and_clean_segments(self, segments: List[Dict[str, Any]], video_file: str) -> List[Dict[str, Any]]:
        """Validate and clean transcript segments."""
        validated_segments = []
        
        for segment in segments:
            # Validate segment structure
            if not all(key in segment for key in ['start', 'end', 'text']):
                logger.warning(f"Skipping segment with missing fields: {segment}")
                continue
            
            start = segment['start']
            end = segment['end']
            text = segment['text'].strip()
            duration = end - start
            
            # Validate timing
            if end <= start:
                logger.warning(f"Skipping segment with invalid timing: {start} -> {end}")
                continue
            
            # Validate duration
            if duration < self.min_segment_duration:
                logger.warning(f"Skipping segment too short: {duration:.1f}s")
                continue
            
            if duration > self.max_segment_duration:
                logger.warning(f"Skipping segment too long: {duration:.1f}s")
                continue
            
            # Validate text
            if len(text) < self.min_text_length:
                logger.warning(f"Skipping segment with too short text: '{text}'")
                continue
            
            if len(text) > self.max_text_length:
                logger.warning(f"Truncating segment with too long text: {len(text)} chars")
                text = text[:self.max_text_length] + "..."
            
            # Clean text
            text = self._clean_text(text)
            
            if text:
                validated_segments.append({
                    'start': start,
                    'end': end,
                    'text': text,
                    'duration': duration
                })
        
        logger.info(f"Validated {len(validated_segments)} segments from {len(segments)} original")
        return validated_segments
    
    async def _merge_and_improve_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge short segments and improve timing."""
        if not segments:
            return segments
        
        merged_segments = []
        current_segment = None
        
        for segment in segments:
            if current_segment is None:
                current_segment = segment.copy()
                continue
            
            # Check if segments should be merged
            time_gap = segment['start'] - current_segment['end']
            combined_duration = current_segment['duration'] + segment['duration']
            
            # Merge if gap is small and combined duration is reasonable
            if time_gap < 2.0 and combined_duration <= self.max_segment_duration:
                current_segment['end'] = segment['end']
                current_segment['text'] += ' ' + segment['text']
                current_segment['duration'] = combined_duration
                logger.debug(f"Merged segments: {current_segment['start']:.1f}s - {current_segment['end']:.1f}s")
            else:
                # Add current segment to results and start new one
                merged_segments.append(current_segment)
                current_segment = segment.copy()
        
        # Add the last segment
        if current_segment:
            merged_segments.append(current_segment)
        
        logger.info(f"Merged {len(segments)} segments into {len(merged_segments)} segments")
        return merged_segments
    
    async def _final_quality_check(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Final quality check on transcript segments."""
        final_segments = []
        
        for segment in segments:
            # Final validation
            if (segment['duration'] >= self.min_segment_duration and
                segment['duration'] <= self.max_segment_duration and
                len(segment['text']) >= self.min_text_length):
                
                final_segments.append(segment)
            else:
                logger.warning(f"Final validation failed for segment: {segment}")
        
        logger.info(f"Final quality check: {len(final_segments)} segments passed")
        return final_segments
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize transcript text."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common transcription artifacts
        text = text.replace('[Music]', '').replace('[music]', '')
        text = text.replace('[Applause]', '').replace('[applause]', '')
        text = text.replace('[Laughter]', '').replace('[laughter]', '')
        text = text.replace('[Silence]', '').replace('[silence]', '')
        
        # Remove excessive punctuation
        text = text.replace('...', ' ').replace('..', ' ')
        
        # Clean up
        text = ' '.join(text.split())
        
        return text.strip()

# Global enhanced transcription service instance
enhanced_transcription = EnhancedTranscriptionService() 