import pytest
from core.assistant.live_conversation_stream import LiveConversationStream

def test_stream_chunks_pacing():
    stream = LiveConversationStream(words_per_tick=3)
    text = "Sistem grid sedang berjalan lancar tanpa sebarang gangguan."
    
    stream.start_stream(text)
    assert stream.is_streaming is True
    assert stream.status == "STREAMING"
    assert stream.output_buffer == ""
    
    # Tick 1: outputs 3 words
    res1 = stream.tick()
    assert res1["output_buffer"] == "Sistem grid sedang"
    assert res1["progress_pct"] > 0.0
    
    # Tick 2: outputs 3 more words
    res2 = stream.tick()
    assert res2["output_buffer"] == "Sistem grid sedang berjalan lancar tanpa"
    
    # Tick 3: outputs last words and completes
    res3 = stream.tick()
    assert res3["output_buffer"] == "Sistem grid sedang berjalan lancar tanpa sebarang gangguan."
    assert res3["status"] == "COMPLETED"
    assert stream.is_streaming is False

def test_stream_interruption():
    stream = LiveConversationStream(words_per_tick=2)
    text = "Saya mengesan sedikit kelainan pada sistem Bus 5 tadi."
    
    stream.start_stream(text)
    stream.tick() # yields "Saya mengesan"
    
    # Interrupt
    res = stream.interrupt()
    assert res["status"] == "INTERRUPTED"
    assert res["is_streaming"] is False
    assert res["interrupted_at_text"] == "Saya mengesan"
    assert "Maaf mencelah" in res["interruption_apology"]
