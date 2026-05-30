import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("assistant.live_stream")

class LiveConversationStream:
    def __init__(self, words_per_tick: int = 2):
        self.words_per_tick = words_per_tick
        self.is_streaming = False
        self.full_response_text = ""
        self.output_buffer = ""
        self.chunks: List[str] = []
        self.current_chunk_idx = 0
        self.status = "IDLE"  # IDLE, STREAMING, COMPLETED, INTERRUPTED
        self.stream_progress_pct = 0.0
        self.interrupted_at_text = ""
        self.interruption_apology = ""
        self.start_time = 0.0

    def start_stream(self, text: str) -> None:
        """
        Starts the conversational streaming buffer.
        """
        self.is_streaming = True
        self.full_response_text = text
        self.output_buffer = ""
        self.chunks = text.split(" ")
        self.current_chunk_idx = 0
        self.status = "STREAMING"
        self.stream_progress_pct = 0.0
        self.interrupted_at_text = ""
        self.interruption_apology = ""
        self.start_time = time.time()
        logger.info(f"Started live streaming response: '{text}'")

    def tick(self) -> Dict[str, Any]:
        """
        Advances the stream chunk-by-chunk based on pacing.
        """
        if not self.is_streaming:
            return self.get_status_summary()

        if self.current_chunk_idx >= len(self.chunks):
            self.is_streaming = False
            self.status = "COMPLETED"
            self.stream_progress_pct = 100.0
            return self.get_status_summary()

        # Add next batch of chunks
        end_idx = min(self.current_chunk_idx + self.words_per_tick, len(self.chunks))
        new_words = self.chunks[self.current_chunk_idx:end_idx]
        self.current_chunk_idx = end_idx
        
        if self.output_buffer:
            self.output_buffer += " " + " ".join(new_words)
        else:
            self.output_buffer = " ".join(new_words)

        # Calculate progress
        self.stream_progress_pct = round((self.current_chunk_idx / len(self.chunks)) * 100.0, 1)

        if self.current_chunk_idx >= len(self.chunks):
            self.is_streaming = False
            self.status = "COMPLETED"
            self.stream_progress_pct = 100.0

        return self.get_status_summary()

    def interrupt(self) -> Dict[str, Any]:
        """
        Stops outputting, preserves buffer, and formats a conversational apology.
        """
        if not self.is_streaming:
            return self.get_status_summary()

        self.is_streaming = False
        self.status = "INTERRUPTED"
        self.interrupted_at_text = self.output_buffer
        
        # Friendly Malay syntax interruption apologies
        self.interruption_apology = "Maaf mencelah, saya terpaksa hentikan jawapan tadi kerana menerima input baharu."
        
        logger.info(f"Stream interrupted at {self.stream_progress_pct}%. Truncated output: '{self.output_buffer}'")
        return self.get_status_summary()

    def get_status_summary(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time if self.start_time > 0 else 0.0
        return {
            "is_streaming": self.is_streaming,
            "status": self.status,
            "full_response_text": self.full_response_text,
            "output_buffer": self.output_buffer,
            "progress_pct": self.stream_progress_pct,
            "elapsed_sec": round(elapsed, 2),
            "interrupted_at_text": self.interrupted_at_text,
            "interruption_apology": self.interruption_apology
        }
