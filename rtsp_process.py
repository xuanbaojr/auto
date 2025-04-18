from service.booth_check import BoothCheck
import logging, queue, threading, os
import subprocess, av, time, cv2
from concurrent.futures import ThreadPoolExecutor


class RTSPProcessor:
    def __init__(self, rtsp_url, output_dir, buffer_size=30, 
                analysis_workers=2, segment_length=300, reconnect_attempts=5, analyze_frame=None):
        
        self.rtsp_url = rtsp_url
        self.output_dir = output_dir
        self.buffer_size = buffer_size
        self.analysis_workers = analysis_workers
        self.segment_length = segment_length
        self.reconnect_attempts = reconnect_attempts

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RTSPProcessor')

        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.packet_queue = queue.Queue(maxsize=buffer_size)
        self.should_record = False
        self.is_recording = False
        self.stop_signal = threading.Event()
        self.last_segment_time = 0
        self.recording_proc = None

        self.ffmpeg_cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',           # More reliable than UDP
            '-rtsp_flags', 'prefer_tcp',        # Force TCP when possible
            '-stimeout', '5000000',             # 5 second timeout
            '-i', self.rtsp_url,
            '-c', 'copy',                       # Passthrough without re-encoding
            '-f', 'matroska',                   # Matroska container format
            'pipe:1'                            # Output to stdout
        ]

        self.proc = None
        self.container = None
        self.analyze_frame = analyze_frame

        os.makedirs(output_dir, exist_ok=True)
    
    def start(self):
        self.logger.info("Starting RTSP processor...")
        self.stop_signal.clear()
        self._start_ffmpeg()
        self.workers = []

        packet_reader = threading.Thread(target=self._packet_reader_thread)
        packet_reader.daemon = True
        packet_reader.start()
        self.workers.append(packet_reader)

        frame_decoder = threading.Thread(target=self._frame_decoder_thread)
        frame_decoder.daemon = True
        frame_decoder.start()
        self.workers.append(frame_decoder)

        self.analyzer_pool = ThreadPoolExecutor(max_workers=self.analysis_workers)

        packet_writer = threading.Thread(target=self._packet_writer_thread)
        packet_writer.daemon = True
        packet_writer.start()
        self.workers.append(packet_writer)

        self.logger.info("RTSP processor started")
        return self

    
    def _start_ffmpeg(self):
        self.logger.info("Starting FFmpeg subprocess...")
        self.proc = subprocess.Popen(
            self.ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )

        try:
            self.container = av.open(self.proc.stdout, format='matroska')
            self.logger.info("FFmpeg subprocess started successfully")
        except Exception as e:
            self.logger.error(f"Failed to open container: {e}")
            self._cleanup()
            raise
    
    def _cleanup(self, keep_running=False):
        if self.container:
            try:
                self.container.close()
            except:
                pass
            self.container = None
        
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except:
                try:
                    self.proc.kill()
                except:
                    pass
            self.proc = None

        if self.is_recording:
            self._stop_recording()

        if not keep_running:
            self.stop_signal.set()
    
    def _stop_recording(self):
        """Stop the current recording and finalize MP4 file with graceful termination"""
        if hasattr(self, 'recording_proc') and self.recording_proc:
            try:
                # Check if the process is still running
                if self.recording_proc.poll() is None:
                    # Graceful termination via SIGINT instead of SIGTERM
                    # This allows FFmpeg to properly finalize the container
                    import signal
                    self.recording_proc.send_signal(signal.SIGINT)
                    
                    # Give FFmpeg more time to finalize short recordings
                    try:
                        # Wait for process to finish with increased timeout for short recordings
                        self.recording_proc.wait(timeout=15)
                        self.logger.info("Recording gracefully stopped")
                    except subprocess.TimeoutExpired:
                        self.logger.warning("FFmpeg taking too long to finalize, sending SIGTERM")
                        self.recording_proc.terminate()
                        try:
                            self.recording_proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.logger.error("FFmpeg still not responding, forcing SIGKILL")
                            self.recording_proc.kill()
                else:
                    self.logger.info("Recording process already completed")
            except Exception as e:
                self.logger.error(f"Error stopping recording: {e}")
                try:
                    self.recording_proc.kill()
                except:
                    pass
            finally:
                self.recording_proc = None
                self.is_recording = False

    def _packet_reader_thread(self):
        self.logger.info("Packet reader thread started")

        try:
            for packet in self.container.demux(video=0):
                if self.stop_signal.is_set():
                    break

                if packet.dts is None:
                    continue

                if not self.packet_queue.full():
                    self.packet_queue.put(packet, block=False)
        except Exception as e:
            self.logger.error(f"Error in packet reader: {e}")
            self._attempt_reconnect()
        
        self.logger.info("Packet reader thread stopped")

    def _frame_decoder_thread(self):
        self.logger.info("Frame decoder thread started")
        try:
            while not self.stop_signal.is_set():
                if self.packet_queue.qsize() > 0:
                    packet = self.packet_queue.get()
                    for frame in packet.decode():
                        img = frame.to_ndarray(format="bgr24")
                        if not self.frame_queue.full():
                            future = self.analyzer_pool.submit(self.analyze_frame, img)
                            future.add_done_callback(self._handle_analysis_result)

        except Exception as e:
            self.logger.error(f"Error in frame decoder: {e}")
        
        self.logger.info("Frame decoder thread stopped")

    def _handle_analysis_result(self, future):
        try:
            result = future.result()
            if result and not self.should_record:
                self.should_record = True
                self.logger.info("Analysis indicates recording should start")
            elif not result and self.should_record:
                self.should_record = False
                self.logger.info("Analysis indicates recording should stop")
        except Exception as e:
            self.logger.error(f"Error handling analysis result: {e}")
    
    def _start_recording(self):
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            output_path = os.path.join(self.output_dir, f"capture_{timestamp}.mp4")
            
            # Create a second FFmpeg instance with improved parameters for short recordings
            self.recording_cmd = [
                'ffmpeg',
                '-y',
                '-rtsp_transport', 'tcp',             # More reliable than UDP
                '-rtsp_flags', 'prefer_tcp',          # Force TCP when possible
                '-stimeout', '5000000',               # 5 second timeout
                '-i', self.rtsp_url,                  # Use the original RTSP URL directly
                '-c:v', 'libx265',                    # H.265 video codec
                '-preset', 'fast',                    # Faster encoding for short segments
                '-crf', '23',                         # Constant Rate Factor
                '-pix_fmt', 'yuv420p',                # Standard pixel format
                '-tag:v', 'hvc1',                     # Tag for better compatibility
                '-f', 'mp4',                          # Explicitly set format
                '-movflags', '+faststart+frag_keyframe+empty_moov+default_base_moof',  # Enhanced MP4 fragmentation
                '-flush_packets', '1',                # Flush packets more frequently
                '-max_delay', '500000',               # Reduce max delay
                output_path
            ]
            
            # Start recording process
            self.recording_proc = subprocess.Popen(
                self.recording_cmd,
                stderr=subprocess.PIPE,
                bufsize=10**8                         # Increased buffer size
            )
            
            self.is_recording = True
            self.last_segment_time = time.time()
            self.logger.info(f"Started recording to {output_path} with H.265 encoding")
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            self.recording_proc = None

    def _packet_writer_thread(self):
        self.logger.info("Packet writer thread started")

        while not self.stop_signal.is_set():
            try:
                if self.should_record and not self.is_recording:
                    self._start_recording()
                elif not self.should_record and self.is_recording:
                    self._stop_recording()
                    self.logger.info("Recording stopped")

                if self.is_recording:
                    current_time = time.time()
                    
                    # Check if we need to start a new segment
                    if (current_time - self.last_segment_time) > self.segment_length:
                        self._stop_recording()
                        self._start_recording()
                        self.logger.info("New recording segment started")
                    
                    # Check if the recording process is still running
                    if hasattr(self, 'recording_proc') and self.recording_proc:
                        if self.recording_proc.poll() is not None:
                            # Process has exited
                            exit_code = self.recording_proc.poll()
                            self.logger.error(f"FFmpeg recording process exited with code {exit_code}")
                            stderr_output = self.recording_proc.stderr.read().decode('utf-8', errors='ignore')
                            self.logger.error(f"FFmpeg stderr output: {stderr_output}")
                            self._stop_recording()
                            if self.should_record:
                                self._start_recording()
                
                # No need to process packets individually - FFmpeg reads directly from RTSP
                time.sleep(0.5)  # Reduced polling frequency
                
            except Exception as e:
                self.logger.error(f"Error in packet writer: {e}")
                if self.is_recording:
                    self._stop_recording()  # Try to clean up recording if error occurs
                time.sleep(1)  # Wait a bit before retrying after an error

        self.logger.info("Packet writer thread stopped")

    def _attempt_reconnect(self):
        self.logger.info("Attempting to reconnect to RTSP stream...")
        self._cleanup(keep_running=True)
        for attempt in range(1, self.reconnect_attempts + 1):
            self.logger.info(f"Reconnection attempt {attempt}/{self.reconnect_attempts}")
            delay = 2 ** attempt
            time.sleep(delay)
            try:
                self._start_ffmpeg()
                self.logger.info("Reconnection successful")
                return True
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt} failed: {e}")
        self.logger.error("All reconnection attempts failed")
        return False
    
    def stop(self):
        """Stop the RTSP processor and clean up resources"""
        self.logger.info("Stopping RTSP processor...")
        
        # Signal all threads to stop
        self.stop_signal.set()
        
        # Clean up resources
        self._cleanup()
        
        # Wait for threads to complete
        for thread in self.workers:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        # Shutdown thread pool
        if hasattr(self, 'analyzer_pool'):
            self.analyzer_pool.shutdown(wait=False)
        
        self.logger.info("RTSP processor stopped")
        
def main():
    booth_check = BoothCheck()

    rtsp_url1 = "rtsp://admin:FFWNQY@192.168.1.2/camera/h264/ch1/main/av_stream"
    output_dir = "./videos"
    try:
        processor = RTSPProcessor(
            rtsp_url=rtsp_url1,
            output_dir=output_dir,
            buffer_size=60,
            analysis_workers=2,
            segment_length=20,  # 5-minute segments
            reconnect_attempts=5,
            analyze_frame=booth_check.check
        )
      
        processor.start()
        print("Processing RTSP stream... Press Ctrl+C to stop")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if 'processor' in locals():
            processor.stop()
            print("Processor stopped")


if __name__ == "__main__":
    main()