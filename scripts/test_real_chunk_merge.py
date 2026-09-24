from src.asr.chunking import (
    ASRChunk,
    merge_asr_chunks,
)


def main():
    chunks = [
        ASRChunk(
            chunk_id="chunk_00",
            start_sec=0,
            end_sec=17,
            text=(
                "नमस्कार हम एक मार्केट रिसर्च सर्वे कर रहे है "
                "मैं आपसे कुछ छोटे सवाल पूछूंगा ठीक है "
                "क्या आप उत्तर प्रदेश के निवासी है ठीक है "
                "क्या आप राज्य सरकार"
            ),
        ),
        ASRChunk(
            chunk_id="chunk_01",
            start_sec=15,
            end_sec=32,
            text=(
                "बदलाव देखना चाहते हैं या नहीं मुझे पता नहीं "
                "हाँ बोल दीजिए हाँ ठीक है क्या आप राज्य सरकार "
                "में बदलाव देखना चाहते हैं या नहीं "
                "समझ नहीं आ रहा हाँ या नहीं नहीं"
            ),
        ),
        ASRChunk(
            chunk_id="chunk_02",
            start_sec=30,
            end_sec=47,
            text=(
                "ठीक है आपका विधानसभा क्षेत्र बदलापुर है "
                "नहीं बिजनौर बिजनौर बिजनौर ठीक है "
                "आपकी उम्र क्या है छत्तीस साल "
                "ठीक है आपके हिसाब से"
            ),
        ),
        ASRChunk(
            chunk_id="chunk_03",
            start_sec=45,
            end_sec=62,
            text=(
                "इस समय सबसे बड़ी समस्या क्या है "
                "महंगाई महंगाई कितने बच्चे ठीक है "
                "अगर अगर आज चुनाव हो तो "
                "आप किस पार्टी को वोट देना पसंद करेंगे "
                "मुझे पक्का नहीं पता"
            ),
        ),
        ASRChunk(
            chunk_id="chunk_04",
            start_sec=60,
            end_sec=74,
            text=(
                "बीएसपी बोल दे हाँ बीएसपी ठीक है "
                "आप मुख्यमंत्री के रूप में किसे देखना चाहेंगे "
                "अभी डिसाइड नहीं किया कोई बात नहीं "
                "सर्वे के लिए धन्यवाद धन्यवाद"
            ),
        ),
    ]

    result = merge_asr_chunks(
        chunks
    )

    print()
    print("=== MERGED REAL Vaani TRANSCRIPT ===")
    print()

    print(
        f"Window: "
        f"{result.start_sec:.1f}s "
        f"→ {result.end_sec:.1f}s"
    )

    print()

    print(
        result.text
    )


if __name__ == "__main__":
    main()