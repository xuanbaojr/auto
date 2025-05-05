"""
Voice Instruction Generator
Generates voiced instruction audio files in Vietnamese for a photo booth application.
Uses Microsoft Edge TTS instead of Google TTS for improved quality and reliability.
"""
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Union

import edge_tts
from pydub import AudioSegment
from pydub.effects import speedup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceGenerator:
    """Generates voice instructions using Microsoft Edge TTS with sound effects."""
    
    def __init__(self, 
                 output_dir: Optional[Union[str, Path]] = None,
                 voice: str = "vi-VN-HoaiMyNeural",
                 playback_rate: float = 1.3,
                 sound_effect_file: str = "ting.mp3",
                 silence_duration: int = 250):
        """
        Initialize the voice generator with configuration options.
        
        Args:
            output_dir: Directory to save output files (defaults to current directory)
            voice: Edge TTS voice to use (default is Vietnamese female voice)
            playback_rate: Speed multiplier for the final audio
            sound_effect_file: Path to sound effect file for success messages
            silence_duration: Duration of silence in milliseconds after sound effect
        """
        self.output_dir = Path(output_dir or os.path.dirname(os.path.abspath(__file__)))
        self.temp_dir = self.output_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        self.voice = voice
        self.playback_rate = playback_rate
        
        # Load sound effect for success messages
        self.sound_effect_path = self.output_dir / sound_effect_file
        if not self.sound_effect_path.exists():
            logger.warning(f"Sound effect file not found: {self.sound_effect_path}")
            self.ting = None
        else:
            self.ting = AudioSegment.from_file(self.sound_effect_path, format='mp3')
        
        self.silence = AudioSegment.silent(duration=silence_duration)
        
        # Define instructions (current version)
        self.instructions = {
            "1_true": "Xin chào. Bước 1: Vui lòng đặt úp bàn tay vào vị trí bên phải.",
            "2_true": "Bước 2: Đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi, hở răng.",
            "2_false": "Bước 1: Vui lòng đặt úp bàn tay vào vị trí bên phải.",
            "3_true": "Bước 3: Quay người sang phải 90 độ.",
            "3_false": "Bước 2: Đứng vào ô vuông dưới chân, nhìn thẳng camera và cười tươi, hở răng.",
            "4_true": "Bước 4: Tiếp tục quay sang phải 90 độ, lưng hướng về camera.",
            "4_false": "Bước 3: Quay người sang phải 90 độ, lưng hướng ra ngoài.",
            "5_true": "Bước 5: Tiếp tục quay phải, hướng người ra bên ngoài.",
            "5_false": "Bước 4: Tiếp tục quay sang phải 90 độ, lưng hướng về camera.",
            "6_true": "Đã hoàn thành. Xin cảm ơn! Vui lòng rời khỏi booth.",
            "6_false": "Bước 5: Tiếp tục quay phải, hướng người ra bên ngoài."
        }
    
    async def generate_speech(self, text: str, output_path: Path) -> Path:
        """
        Generate speech using Edge TTS and save to file.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the generated audio
            
        Returns:
            Path to the generated audio file
        """
        communicate = edge_tts.Communicate(text, self.voice)
        
        try:
            await communicate.save(str(output_path))
            logger.info(f"Generated speech at {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise
    
    def process_audio(self, input_path: Path, is_success: bool) -> AudioSegment:
        """
        Process audio by adding sound effects and adjusting speed.
        
        Args:
            input_path: Path to input audio file
            is_success: Whether to add success sound effect
            
        Returns:
            Processed AudioSegment
        """
        try:
            # Load the speech audio
            speech = AudioSegment.from_file(input_path, format='mp3')
            
            # Add sound effect for success messages
            if is_success and self.ting is not None:
                final_audio = self.ting + self.silence + speech
            else:
                final_audio = speech
            
            # Speed up the audio
            sped_audio = speedup(final_audio, playback_speed=self.playback_rate)
            
            return sped_audio
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise
    
    async def generate_instruction(self, key: str, text: str) -> Path:
        """
        Generate a complete instruction audio file.
        
        Args:
            key: Instruction key (e.g., '1_true')
            text: Instruction text
            
        Returns:
            Path to the final audio file
        """
        logger.info(f"Generating instruction for: {key}")
        
        # Generate speech with Edge TTS
        temp_path = self.temp_dir / f"temp_{key}.mp3"
        await self.generate_speech(text, temp_path)
        
        # Process audio with effects and speed adjustments
        is_success = key.endswith('_true')
        processed_audio = self.process_audio(temp_path, is_success)
        
        # Export final audio
        output_path = self.output_dir / f"{key}.mp3"
        processed_audio.export(str(output_path), format='mp3')
        logger.info(f"Created final audio: {output_path}")
        
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()
        
        return output_path
    
    async def generate_all_instructions(self):
        """Generate all instruction audio files in parallel."""
        logger.info(f"Starting generation of {len(self.instructions)} audio files")
        
        # Create tasks for each instruction
        tasks = []
        for key, text in self.instructions.items():
            task = self.generate_instruction(key, text)
            tasks.append(task)
        
        # Run all tasks concurrently for better performance
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            logger.error(f"Encountered {len(errors)} errors during generation")
            for error in errors:
                logger.error(f"Error: {error}")
        else:
            logger.info("All audio files generated successfully")
    
    def cleanup(self):
        """Clean up temporary files and directory."""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*"):
                    file.unlink()
                self.temp_dir.rmdir()
                logger.info("Temporary directory cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


async def main():
    """Main function to run the voice generator."""
    generator = VoiceGenerator()
    
    try:
        await generator.generate_all_instructions()
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
    finally:
        generator.cleanup()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())